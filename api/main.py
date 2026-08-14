import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from api.schemas import LoginRequest, ChatRequest, AuthResponse, ChatResponse
from auth.auth import authenticate, guest_login, validate_session, logout
from agents.supervisor import run_supervisor, run_supervisor_stream
import json
import asyncio

app = FastAPI(title="Smart Campus AI", version="2.0.0")

# CORS：仅允许前端开发服务器与 Gradio 的固定来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:7860",
        "http://127.0.0.1:7860",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, dict] = {}


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "token": "",
            "session_id": session_id,
            "role": "guest",
            "display_name": "Guest",
            "user_id": None,
            "student_id": None,
        }
    return _sessions[session_id]


def _require_authenticated_session(session: dict) -> None:
    """会话必须已绑定有效的服务端登录 token，否则拒绝访问"""
    if not session.get("token"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if validate_session(session["token"]) is None:
        session["token"] = ""
        session["role"] = "guest"
        raise HTTPException(status_code=401, detail="Session expired, please login again")


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    session = authenticate(req.username, req.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return AuthResponse(
        token=session.token,
        role=session.role,
        display_name=session.display_name,
        student_id=session.student_id,
    )


@app.post("/api/auth/guest", response_model=AuthResponse)
async def guest():
    session = guest_login()
    return AuthResponse(
        token=session.token,
        role=session.role,
        display_name=session.display_name,
        student_id=None,
    )


@app.post("/api/auth/logout")
async def api_logout(token: str):
    logout(token)
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session = _get_or_create_session(req.session_id)
    _require_authenticated_session(session)
    result = run_supervisor(
        req.message,
        session["session_id"],
        session["role"],
        session["user_id"],
        session["display_name"],
        req.debug,
        session.get("student_id"),
    )
    return ChatResponse(
        response=result.get("response", "Error"),
        think_chain=result.get("think_chain", []),
        worker_results=result.get("worker_results", []),
        iteration_count=result.get("iteration_count", 0),
    )


@app.get("/api/chat/stream")
async def chat_stream(message: str, session_id: str, debug: bool = False):
    session = _get_or_create_session(session_id)
    _require_authenticated_session(session)

    async def event_generator():
        async for event in run_supervisor_stream(
            message,
            session["session_id"],
            session["role"],
            session["user_id"],
            session["display_name"],
            session.get("student_id"),
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/session/update")
async def update_session(session_id: str, token: str):
    """把前端会话与服务端登录会话绑定。

    安全说明：角色/姓名/学号一律以服务端登录会话为准，不接受客户端传入，
    防止通过伪造 role 参数提权为 admin。
    """
    server_session = validate_session(token)
    if not server_session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    session = _get_or_create_session(session_id)
    session["token"] = token
    session["role"] = server_session.role
    session["display_name"] = server_session.display_name
    # 游客视为未登录用户，不绑定 user_id（不写入长期记忆/画像）
    session["user_id"] = None if server_session.role == "guest" else server_session.username
    session["student_id"] = server_session.student_id
    return {"status": "ok"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
