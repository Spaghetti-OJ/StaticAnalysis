#!/usr/bin/env python3
"""
Clang-Tidy Static Analysis API Server (FastAPI)
提供靜態分析功能的 FastAPI 版本
"""

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import subprocess
import json
import yaml
import tempfile
import shutil
from pathlib import Path
import sqlite3
from datetime import datetime

app = FastAPI(title="Clang-Tidy API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
BASE_DIR = Path(__file__).parent.parent
BUILD_DIR = BASE_DIR / "build"
MODULE_PATH = BUILD_DIR / "libMiscTidyModule.so"
SCRIPT_PATH = BASE_DIR / "scripts" / "generate_tidy_config.py"
CONFIG_DIR = BASE_DIR / "configs"
DB_PATH = BASE_DIR / "api" / "database.db"

# 確保目錄存在
CONFIG_DIR.mkdir(exist_ok=True)
(BASE_DIR / "api").mkdir(exist_ok=True)


def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # submissions 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY,
            problem_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            created_at TEXT NOT NULL,
            user_id INTEGER
        )
    ''')
    
    # requirements 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL UNIQUE,
            rules TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # lint_runs 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS lint_runs (
            id TEXT PRIMARY KEY,
            submission_id INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            violations_count INTEGER,
            fixes_available BOOLEAN,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT
        )
    ''')
    
    # lint_reports 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS lint_reports (
            id TEXT PRIMARY KEY,
            submission_id INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            run_id TEXT NOT NULL,
            passed BOOLEAN NOT NULL,
            violations TEXT NOT NULL,
            total_violations INTEGER NOT NULL,
            execution_time_ms INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES lint_runs(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def auth_dependency(authorization: str | None = Header(default=None)):
    """簡易認證依賴（示範用）。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized.")
    # TODO: 驗證 token
    return True


def permission_dependency(_: bool = Depends(auth_dependency)):
    """簡易權限依賴（示範用）。"""
    # TODO: 實作權限檢查
    return True


# ======== Pydantic models ========

class RequirementsBody(BaseModel):
    problem_id: int
    rules: list[str]


class GenerateBody(BaseModel):
    problem_id: int
    rules: list[str]
    language_type: int | None = 1


class RunBody(BaseModel):
    submission_id: int
    problem_id: int
    language_type: int | None = 1
    timeout_sec: int | None = 30
    export_fixes: bool | None = True


class ReportResult(BaseModel):
    passed: bool
    violations: list[dict] = []
    total_violations: int = 0
    execution_time_ms: int | None = None


class ReportBody(BaseModel):
    submission_id: int
    problem_id: int
    run_id: str
    result: ReportResult


class CreateSubmissionBody(BaseModel):
    problem_id: int
    code: str
    language: str = "cpp"


# ==================== API 端點 ====================

@app.get('/submission/{submission_id}')
def get_submission(submission_id: int, _auth: bool = Depends(auth_dependency)):
    """1. GET /submission/<submission> – 取得使用者提交程式碼"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            '''
            SELECT id, problem_id, code, language, created_at
            FROM submissions WHERE id = ?
            ''',
            (submission_id,)
        )
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="submission not found.")

        return {
            "submission_id": row[0],
            "problem_id": row[1],
            "code": row[2],
            "language": row[3],
            "created_at": row[4],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/lint/requirements')
def save_requirements(body: RequirementsBody, _perm: bool = Depends(permission_dependency)):
    """2. POST /lint/requirements – 提交出題者需求"""
    try:
        problem_id = body.problem_id
        rules = body.rules or []
        if not problem_id or not rules:
            raise HTTPException(status_code=400, detail="invalid rules format.")
        
        # 驗證規則格式
        valid_rules = ['--forbid-loops', '--forbid-arrays', '--forbid-stl']
        for rule in rules:
            if not any(rule.startswith(vr) or rule == vr for vr in valid_rules + ['--forbid-functions=']):
                raise HTTPException(status_code=400, detail=f"invalid rule: {rule}")
        
        # 儲存到資料庫
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''
            INSERT OR REPLACE INTO requirements (problem_id, rules, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (problem_id, json.dumps(rules), now, now))
        
        config_id = f"cfg_{problem_id}"
        conn.commit()
        conn.close()
        
        return {
            "message": "requirements saved.",
            "config_id": config_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/lint/generate')
def generate_config(body: GenerateBody, _perm: bool = Depends(permission_dependency)):
    """3. POST /lint/generate – 生成 .clang-tidy 檔案"""
    try:
        problem_id = body.problem_id
        rules = body.rules or []
        if not problem_id or not rules:
            raise HTTPException(status_code=400, detail="missing problem_id or rules.")
        
        # 建立題目配置目錄
        problem_config_dir = CONFIG_DIR / f"problem_{problem_id}"
        problem_config_dir.mkdir(exist_ok=True)
        
        # 轉換規則為腳本參數
        script_args = ['python3', str(SCRIPT_PATH)]
        for rule in rules:
            if rule.startswith('--forbid-functions='):
                script_args.append('--forbid-functions')
                funcs = rule.split('=')[1]
                script_args.extend(['--function-names', funcs])
            else:
                script_args.append(rule)
        
        script_args.extend(['--output-dir', str(problem_config_dir)])
        
        # 執行生成腳本
        result = subprocess.run(
            script_args,
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"generation failed: {result.stderr}")
        
        # 讀取生成的配置
        config_path = problem_config_dir / ".clang-tidy"
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        return {
            "message": f"Generated .clang-tidy for problem {problem_id}",
            "config_path": str(config_path),
            "config_content": config_content,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/lint/run')
def run_lint(body: RunBody):
    """4. POST /lint/run – 執行 Clang-Tidy 檢查"""
    try:
        submission_id = body.submission_id
        problem_id = body.problem_id
        language_type = body.language_type or 1  # 0=C, 1=C++
        timeout_sec = body.timeout_sec or 30
        export_fixes = True if body.export_fixes is None else body.export_fixes

        if not submission_id or not problem_id:
            raise HTTPException(status_code=400, detail="invalid submission_id or missing code.")
        
        # 取得提交程式碼
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT code, language FROM submissions WHERE id = ?', (submission_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="submission not found.")
        
        code, language = row
        
        # 建立 run 記錄
        run_id = f"run_{submission_id}_{int(datetime.now().timestamp())}"
        now = datetime.now().isoformat()
        c.execute('''
            INSERT INTO lint_runs (id, submission_id, problem_id, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (run_id, submission_id, problem_id, 'running', now))
        conn.commit()
        
        # 建立臨時工作目錄
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 決定檔案副檔名
            ext = '.c' if language_type == 0 else '.cpp'
            code_file = tmpdir_path / f"code{ext}"
            code_file.write_text(code)
            
            # 複製 .clang-tidy 配置
            config_src = CONFIG_DIR / f"problem_{problem_id}" / ".clang-tidy"
            if config_src.exists():
                shutil.copy(config_src, tmpdir_path / ".clang-tidy")
            
            # 準備 clang-tidy 命令
            std_flag = '-std=c17' if language_type == 0 else '-std=c++17'
            fixes_file = tmpdir_path / "fixes.yaml"
            
            cmd = [
                'clang-tidy',
                str(code_file),
                '-load', str(MODULE_PATH),
            ]
            
            if export_fixes:
                cmd.extend(['-export-fixes', str(fixes_file)])
            
            cmd.extend(['--', std_flag])
            
            # 執行 clang-tidy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=tmpdir_path,
            )
            
            # 解析結果
            violations_count = 0
            fixes_available = False
            
            if export_fixes and fixes_file.exists():
                with open(fixes_file, 'r') as f:
                    fixes_data = yaml.safe_load(f)
                    if fixes_data and 'Diagnostics' in fixes_data:
                        violations_count = len(fixes_data['Diagnostics'])
                        fixes_available = True
            
            # 更新 run 記錄
            status = 'finished' if result.returncode in [0, 1] else 'failed'
            c.execute('''
                UPDATE lint_runs
                SET status = ?, violations_count = ?, fixes_available = ?,
                    completed_at = ?, error_message = ?
                WHERE id = ?
            ''', (status, violations_count, fixes_available, datetime.now().isoformat(),
                  result.stderr if status == 'failed' else None, run_id))
            conn.commit()
        
        conn.close()
        
        return {
            "message": "clang-tidy completed.",
            "run_id": run_id,
            "status": status,
            "violations_count": violations_count,
            "fixes_available": fixes_available,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="clang-tidy timeout.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"clang-tidy runtime error: {str(e)}")


@app.post('/lint/report')
def save_report(body: ReportBody, _perm: bool = Depends(permission_dependency)):
    """5. POST /lint/report – 儲存靜態分析結果"""
    try:
        submission_id = body.submission_id
        problem_id = body.problem_id
        run_id = body.run_id
        result = body.result
        
        if not all([submission_id, problem_id, run_id, result]):
            raise HTTPException(status_code=400, detail="invalid report format.")
        
        # 儲存報告
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        report_id = f"rpt_{submission_id}_{int(datetime.now().timestamp())}"
        now = datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO lint_reports 
            (id, submission_id, problem_id, run_id, passed, violations, 
             total_violations, execution_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, submission_id, problem_id, run_id,
            bool(result.passed),
            json.dumps(result.violations or []),
            int(result.total_violations or 0),
            result.execution_time_ms,
            now
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "report saved.",
            "report_id": report_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 輔助端點 ====================

@app.post('/submission', status_code=201)
def create_submission(body: CreateSubmissionBody):
    """建立新的提交（測試用）"""
    try:
        code = body.code
        problem_id = body.problem_id
        language = body.language or 'cpp'

        if not code or not problem_id:
            raise HTTPException(status_code=400, detail="missing code or problem_id.")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO submissions (problem_id, code, language, created_at)
            VALUES (?, ?, ?, ?)
        ''', (problem_id, code, language, now))
        
        submission_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "message": "submission created.",
            "submission_id": submission_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/health')
def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "module_exists": MODULE_PATH.exists(),
        "script_exists": SCRIPT_PATH.exists(),
    }


@app.on_event("startup")
def on_startup():
    init_db()
    print(f"✅ Database initialized at {DB_PATH}")
    print(f"✅ Module path: {MODULE_PATH}")
    print(f"✅ Script path: {SCRIPT_PATH}")
    print(f"✅ Config directory: {CONFIG_DIR}")

