from fastapi import FastAPI, HTTPException, File, Form, UploadFile, Depends, Header, status
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from typing import Optional
from contextlib import asynccontextmanager
import logging
import json
import asyncio
import os
import hashlib
import shutil
import aiofiles
import time
import glob
from logging.handlers import TimedRotatingFileHandler

from models import SubmissionRequest, LimitObject, Job
from queue_manager import job_queue
from worker import worker_manager

# 設定日誌
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "sandbox.log")

handler = TimedRotatingFileHandler(
    log_file, 
    when="midnight", 
    interval=1, 
    backupCount=30, 
    encoding='utf-8'
)
handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await worker_manager.start()
    yield
    # Shutdown
    await worker_manager.stop()

app = FastAPI(
    title="Sandbox Isolate API",
    version="2.0.0",
    description="非同步 Isolate 沙盒評測服務",
    lifespan=lifespan
)

# ===== Security =====
API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("SANDBOX_API_KEY", "default-insecure-key") # 建議在環境變數中設定
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """驗證 API Key"""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )
    return api_key

# ===== API Endpoints =====

@app.post("/api/v1/submissions", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)])
async def submit_job(
    submission_id: str = Form(..., description="唯一的提交 ID"),
    problem_id: str = Form(..., description="題目 ID"),
    mode: str = Form(..., description="模式: zip | normal", regex="^(zip|normal)$"),
    language: str = Form(..., description="程式語言: c, cpp, python, java, go"),
    
    file: UploadFile = File(..., description="程式碼檔案或 ZIP"),
    file_hash: str = Form(..., description="檔案 SHA256 Hash"),
    
    time_limit: float = Form(2.0, description="CPU 時間限制 (秒)"),
    memory_limit: int = Form(256000, description="記憶體限制 (KB)"),
    
    use_checker: bool = Form(False, description="是否使用 Checker"),
    checker_file: Optional[UploadFile] = File(None, description="Checker 執行檔"),
    
    use_static_analysis: bool = Form(False, description="是否使用靜態分析"),
    static_analysis_file: Optional[UploadFile] = File(None, description="靜態分析設定檔或執行檔"),
    
    callback_url: Optional[str] = Form(None, description="Webhook URL"),
    priority: int = Form(10, description="優先級"),
    stdin: Optional[str] = Form(None, description="標準輸入 (Stdin)"),
):
    """
    提交評測任務 (Async V2) - Aligned with User Spec
    """
    # 0. Log 接收到的請求
    logger.info(f"Received submission {submission_id}: problem={problem_id}, lang={language}, mode={mode}, priority={priority}")

    # 1. 建立暫存目錄
    upload_dir = f"/tmp/sandbox/submissions/{submission_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 2. 儲存主檔案
    file_path = os.path.join(upload_dir, file.filename)
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

    # 3. 驗證 Hash
    sha256_hash = hashlib.sha256(content).hexdigest()
    if sha256_hash != file_hash:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"File hash mismatch. Expected {file_hash}, got {sha256_hash}")

    # 4. 儲存 Optional Files
    checker_path = None
    if use_checker and checker_file:
        checker_path = os.path.join(upload_dir, checker_file.filename)
        async with aiofiles.open(checker_path, 'wb') as out_file:
            await out_file.write(await checker_file.read())
            
    static_analysis_path = None
    if use_static_analysis and static_analysis_file:
        static_analysis_path = os.path.join(upload_dir, static_analysis_file.filename)
        async with aiofiles.open(static_analysis_path, 'wb') as out_file:
            await out_file.write(await static_analysis_file.read())

    # 5. 建構 Request Data (For backward compatibility / internal use)
    limits = LimitObject(
        time_limit_sec=time_limit,
        memory_limit_kb=memory_limit,
        wall_time_limit_sec=time_limit * 2.5 # Default heuristic
    )
    
    request_data = SubmissionRequest(
        submission_id=submission_id,
        code="<FILE_UPLOADED>", 
        language=language,
        priority=priority,
        limits=limits,
        callback_url=callback_url
    )

    # 6. 建立 Job
    job = Job(
        submission_id=submission_id,
        language=language,
        priority=priority,
        timestamp=time.time(),
        request_data=request_data,
        
        problem_id=problem_id,
        mode=mode,
        file_path=file_path,
        file_hash=file_hash,
        
        use_checker=use_checker,
        checker_file_path=checker_path,
        
        use_static_analysis=use_static_analysis,
        static_analysis_file_path=static_analysis_path,
        
        stdin=stdin
    )

    # 7. 推入隊列
    try:
        await job_queue.push(job)
        logger.info(f"Job {submission_id} added to queue (Position: {job_queue.size()})")
    except asyncio.QueueFull:
        logger.warning(f"Job queue full, rejected {submission_id}")
        # Cleanup on failure
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="系統忙碌中，請稍後再試 (Queue Full)"
        )

    return {
        "success": True,
        "submission_id": submission_id,
        "status": "queued",
        "queue_position": job_queue.size()
    }

@app.post("/api/v1/test_local/{problem_id}", dependencies=[Depends(verify_api_key)])
async def test_local_problem(problem_id: str):
    """
    測試本地題目 (Dev Only)
    讀取 test_data/problems/{problem_id} 下的 solution.py 與 test cases
    """
    problem_dir = os.path.join("test_data", "problems", problem_id)
    if not os.path.exists(problem_dir):
        raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found")

    solution_path = os.path.join(problem_dir, "solution.py")
    if not os.path.exists(solution_path):
        raise HTTPException(status_code=404, detail="solution.py not found")

    # Read solution code
    async with aiofiles.open(solution_path, "r", encoding="utf-8") as f:
        code_content = await f.read()
    
    # Find test cases
    input_files = sorted(glob.glob(os.path.join(problem_dir, "*.in")))
    
    results = []
    
    for input_file in input_files:
        test_case_name = os.path.basename(input_file).replace(".in", "")
        output_file = input_file.replace(".in", ".out")
        
        expected_output = None
        if os.path.exists(output_file):
            async with aiofiles.open(output_file, "r", encoding="utf-8") as f:
                expected_output = await f.read()
        
        stdin_content = None
        async with aiofiles.open(input_file, "r", encoding="utf-8") as f:
            stdin_content = await f.read()

        submission_id = f"test-{problem_id}-{test_case_name}-{int(time.time())}"
        
        # Create Job directly
        # Note: We skip the file upload part for local testing and just use the code content
        # But Worker expects a file path. So we mock it or create a temp file.
        # Let's create a temp file to be consistent with Worker logic.
        
        upload_dir = f"/tmp/sandbox/submissions/{submission_id}"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, "solution.py")
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(code_content)
            
        file_hash = hashlib.sha256(code_content.encode()).hexdigest()
        
        limits = LimitObject(
            time_limit_sec=2.0,
            memory_limit_kb=256000,
            wall_time_limit_sec=5.0
        )
        
        request_data = SubmissionRequest(
            submission_id=submission_id,
            code=code_content,
            language="python",
            priority=10,
            limits=limits
        )
        
        job = Job(
            submission_id=submission_id,
            language="python",
            priority=10,
            timestamp=time.time(),
            request_data=request_data,
            problem_id=problem_id,
            mode="normal",
            file_path=file_path,
            file_hash=file_hash,
            stdin=stdin_content,
            expected_output=expected_output
        )
        
        await job_queue.push(job)
        results.append(submission_id)
        
    return {
        "message": f"Triggered {len(results)} tests for {problem_id}",
        "submission_ids": results
    }

@app.get("/api/v1/submissions/{submission_id}")
async def get_submission_result(submission_id: str):
    """
    查詢特定提交的結果
    """
    # 1. 搜尋歷史紀錄 (已完成的任務)
    for job in worker_manager.history:
        if job["submission_id"] == submission_id:
            return job
    
    # 2. 搜尋正在執行的任務
    for worker in worker_manager.workers:
        if worker.current_job and worker.current_job.submission_id == submission_id:
            return {
                "submission_id": submission_id,
                "status": "processing",
                "message": "Job is currently running"
            }
            
    # 3. 搜尋佇列中的任務 (尚未開始)
    # 這邊需要遍歷 queue，但 asyncio.Queue 不容易遍歷，暫時略過或假設在 queue 中
    # 簡單回傳 404 代表 "Not Found in History or Active" -> 可能還在 Queue 或 ID 錯誤
    
    raise HTTPException(status_code=404, detail="Submission not found (might be queued or invalid ID)")

@app.get("/health")
async def health():
    status_data = worker_manager.get_status()
    return {
        "status": "ok", 
        "queue_size": job_queue.size(),
        "service": "sandbox-isolate-api-v2",
        "workers": status_data
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """即時監控儀表板"""
    if os.path.exists("dashboard.html"):
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Dashboard not found"

@app.get("/logs/view", response_class=HTMLResponse)
async def view_logs():
    """即時 Log 檢視頁面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sandbox Live Logs</title>
        <meta charset="utf-8">
        <style>
            body { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; margin: 0; padding: 20px; font-size: 14px; }
            h1 { font-size: 18px; margin-bottom: 10px; color: #569cd6; }
            #controls { margin-bottom: 10px; position: sticky; top: 0; background: #1e1e1e; padding: 10px 0; border-bottom: 1px solid #333; }
            button { background: #0e639c; color: white; border: none; padding: 5px 10px; cursor: pointer; }
            button:hover { background: #1177bb; }
            #log-container { white-space: pre-wrap; word-wrap: break-word; }
            .error { color: #f48771; }
            .info { color: #d4d4d4; }
            .warning { color: #cca700; }
        </style>
    </head>
    <body>
        <div id="controls">
            <h1>Sandbox Live Logs</h1>
            <button onclick="fetchLogs()">Refresh Now</button>
            <span id="status" style="margin-left: 10px; font-size: 12px; color: #888;">Auto-refreshing every 2s...</span>
            <div id="debug-info" style="font-size: 10px; color: #666; margin-top: 5px;"></div>
        </div>
        <div id="log-container">Loading...</div>
        <script>
            const logContainer = document.getElementById('log-container');
            const debugInfo = document.getElementById('debug-info');
            let isScrolledToBottom = true;

            window.onscroll = function() {
                isScrolledToBottom = (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 50;
            };

            async function fetchLogs() {
                try {
                    const response = await fetch('/logs/raw?t=' + new Date().getTime());
                    if (!response.ok) throw new Error("Failed to fetch: " + response.status);
                    const text = await response.text();
                    logContainer.textContent = text;
                    
                    if (isScrolledToBottom) {
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                    document.getElementById('status').textContent = "Last updated: " + new Date().toLocaleTimeString();
                    debugInfo.textContent = "Length: " + text.length + " chars";
                } catch (e) {
                    document.getElementById('status').textContent = "Error: " + e.message;
                }
            }
            
            // Initial load
            fetchLogs();
            // Auto refresh
            setInterval(fetchLogs, 2000);
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/logs/raw")
async def get_raw_logs():
    """獲取原始 Log 內容"""
    abs_log_file = os.path.abspath(log_file)
    if not os.path.exists(abs_log_file):
        # Debug info if file not found
        return f"Log file not found at {abs_log_file}.\nCWD: {os.getcwd()}\nLS logs/: {os.listdir('logs') if os.path.exists('logs') else 'logs dir missing'}"
    
    try:
        # Use standard open to ensure we get content and avoid async locking issues if any
        with open(abs_log_file, mode='r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if not content:
                return f"Log file exists at {abs_log_file} but is empty."
            return content
    except Exception as e:
        return f"Error reading log file: {str(e)}"

@app.get("/")
async def root():
    return {
        "service": app.title, 
        "version": app.version,
        "endpoints": ["/health", "/api/v1/submissions", "/dashboard"]
    }
