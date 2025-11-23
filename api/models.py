from pydantic import BaseModel
from typing import Optional, Any

class LimitObject(BaseModel):
    time_limit_sec: float
    memory_limit_kb: int
    wall_time_limit_sec: float

class SubmissionRequest(BaseModel):
    submission_id: str
    code: str
    language: str
    priority: int
    limits: LimitObject
    callback_url: Optional[str] = None

class Job(BaseModel):
    submission_id: str
    language: str
    priority: int
    timestamp: float
    request_data: SubmissionRequest
    
    problem_id: str
    mode: str
    file_path: str
    file_hash: str
    
    use_checker: bool = False
    checker_file_path: Optional[str] = None
    
    use_static_analysis: bool = False
    static_analysis_file_path: Optional[str] = None
    
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
