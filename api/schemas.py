from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    debug: bool = False

class AuthResponse(BaseModel):
    token: str
    role: str
    display_name: str
    student_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    think_chain: list = []
    worker_results: list = []
    iteration_count: int = 0
