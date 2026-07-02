"""RBAC access control module - Python 3.7+ compatible"""
from __future__ import annotations
import hashlib, secrets, json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    username: str
    password_hash: str
    role: str
    display_name: str
    student_id: Optional[str] = None
    email: Optional[str] = None

@dataclass
class Session:
    token: str
    username: str
    role: str
    display_name: str
    created_at: str
    student_id: Optional[str] = None

PERMISSIONS = {
    "admin":    {"db_query": True, "score_query": True, "student_info": True, "send_email": True, "rag_query": True, "search": True, "manage_users": True, "view_all_students": True, "view_analytics": True},
    "teacher":  {"db_query": True, "score_query": True, "student_info": True, "send_email": True, "rag_query": True, "search": True, "manage_users": False, "view_all_students": True, "view_analytics": False},
    "student":  {"db_query": True, "score_query": True, "student_info": True, "send_email": False, "rag_query": True, "search": True, "manage_users": False, "view_all_students": False, "view_analytics": False},
    "guest":    {"db_query": False, "score_query": False, "student_info": False, "send_email": False, "rag_query": True, "search": True, "manage_users": False, "view_all_students": False, "view_analytics": False},
}

DATA_SCOPE = {"admin": "all", "teacher": "department", "student": "self", "guest": "none"}

_USERS_FILE = Path("data") / "users.json"

def _hash_password(password: str) -> str:
    return hashlib.sha256((password + "smart-campus-salt").encode()).hexdigest()

_DEFAULT_USERS = [
    User("admin", _hash_password("admin123"), "admin", "System Admin"),
    User("teacher_wang", _hash_password("teacher123"), "teacher", "Teacher Wang"),
    User("student_zhang", _hash_password("student123"), "student", "Zhang San", "2024001", "zhangsan@campus.edu.cn"),
    User("guest", _hash_password(""), "guest", "Guest"),
]

def _init_users():
    _USERS_FILE.parent.mkdir(exist_ok=True)
    if not _USERS_FILE.exists():
        data = [{"username": u.username, "password_hash": u.password_hash, "role": u.role,
                 "display_name": u.display_name, "student_id": u.student_id, "email": u.email} for u in _DEFAULT_USERS]
        _USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _load_users() -> list:
    _init_users()
    data = json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    return [User(d["username"], d["password_hash"], d["role"],
                 d.get("display_name", d["username"]), d.get("student_id"), d.get("email")) for d in data]

_sessions: dict = {}

def authenticate(username: str, password: str) -> Optional[Session]:
    for u in _load_users():
        if u.username == username:
            if u.password_hash == _hash_password(password):
                tok = secrets.token_hex(32)
                s = Session(tok, u.username, u.role, u.display_name, "now", u.student_id)
                _sessions[tok] = s
                return s
            return None
    return None

def guest_login() -> Session:
    tok = secrets.token_hex(32)
    s = Session(tok, "guest", "guest", "Guest", "now")
    _sessions[tok] = s
    return s

def validate_session(token: str) -> Optional[Session]:
    return _sessions.get(token)

def logout(token: str):
    _sessions.pop(token, None)

def get_permissions(role: str) -> dict:
    return PERMISSIONS.get(role, PERMISSIONS["guest"])

def check_permission(role: str, action: str) -> bool:
    return get_permissions(role).get(action, False)

def get_data_scope(role: str) -> str:
    return DATA_SCOPE.get(role, "none")
