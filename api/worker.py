import asyncio
import logging
import os
import subprocess
import shutil
import tempfile
import yaml
from pathlib import Path
from queue_manager import job_queue
from models import Job

logger = logging.getLogger(__name__)

# Configuration for Static Analysis
BASE_DIR = Path(__file__).parent.parent
BUILD_DIR = BASE_DIR / "build"
MODULE_PATH = BUILD_DIR / "libMiscTidyModule.so"

class Worker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.current_job = None
        self._stop_event = asyncio.Event()

    async def run(self):
        logger.info(f"Worker {self.worker_id} started")
        while not self._stop_event.is_set():
            try:
                if job_queue.empty():
                    await asyncio.sleep(1)
                    continue
                
                job = await job_queue.pop()
                self.current_job = job
                logger.info(f"Worker {self.worker_id} processing job {job.submission_id}")
                
                await self.process_job(job)
                
                # Add to history (in a real app, save to DB)
                worker_manager.history.append({
                    "submission_id": job.submission_id,
                    "status": "completed",
                    "result": "Processed" # Simplify for now
                })
                
                self.current_job = None
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                if self.current_job:
                     worker_manager.history.append({
                        "submission_id": self.current_job.submission_id,
                        "status": "failed",
                        "error": str(e)
                    })
                self.current_job = None

    async def process_job(self, job: Job):
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Copy source file
            source_ext = ".cpp" if "cpp" in job.language else ".c" if "c" == job.language else ".py"
            code_file = tmpdir_path / f"solution{source_ext}"
            shutil.copy(job.file_path, code_file)
            
            result_data = {}

            # 1. Static Analysis (if requested)
            if job.use_static_analysis:
                logger.info(f"Running static analysis for {job.submission_id}")
                sa_result = self.run_static_analysis(code_file, job.static_analysis_file_path, tmpdir_path)
                result_data["static_analysis"] = sa_result

            # 2. Execution (Basic placeholder)
            # In a real Isolate sandbox, we would use 'isolate' command here.
            # For now, we just compile and run if it's C/C++.
            if job.mode == "normal":
                exec_result = self.run_execution(code_file, job, tmpdir_path)
                result_data["execution"] = exec_result

            # Update job history with detailed results
            # (In a real app, we would update the DB here)
            worker_manager.history.append({
                "submission_id": job.submission_id,
                "status": "completed",
                "data": result_data
            })

    def run_static_analysis(self, code_file: Path, config_path: str, tmpdir: Path):
        if not MODULE_PATH.exists():
            return {"error": "Static analysis module not found"}

        # Prepare clang-tidy command
        cmd = ['clang-tidy', str(code_file), '-load', str(MODULE_PATH)]
        
        # Use provided config or default
        if config_path and os.path.exists(config_path):
            shutil.copy(config_path, tmpdir / ".clang-tidy")
        
        # Export fixes to yaml
        fixes_file = tmpdir / "fixes.yaml"
        cmd.extend(['-export-fixes', str(fixes_file)])
        
        # Add standard flags
        cmd.extend(['--', '-std=c++17'])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=30
            )
            
            violations = []
            if fixes_file.exists():
                with open(fixes_file, 'r') as f:
                    fixes_data = yaml.safe_load(f)
                    if fixes_data and 'Diagnostics' in fixes_data:
                        violations = fixes_data['Diagnostics']

            return {
                "passed": proc.returncode == 0,
                "violations": violations,
                "raw_output": proc.stdout
            }
        except Exception as e:
            return {"error": str(e)}

    def run_execution(self, code_file: Path, job: Job, tmpdir: Path):
        # Placeholder for execution logic
        return {"message": "Execution simulated"}

    def stop(self):
        self._stop_event.set()

class WorkerManager:
    def __init__(self):
        self.workers = []
        self.history = [] # Simple in-memory history

    async def start(self, num_workers=2):
        for i in range(num_workers):
            w = Worker(i)
            self.workers.append(w)
            asyncio.create_task(w.run())

    async def stop(self):
        for w in self.workers:
            w.stop()

    def get_status(self):
        return [
            {
                "id": w.worker_id, 
                "busy": w.current_job is not None,
                "job_id": w.current_job.submission_id if w.current_job else None
            }
            for w in self.workers
        ]

worker_manager = WorkerManager()
