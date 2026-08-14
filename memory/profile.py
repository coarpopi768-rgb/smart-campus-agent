"""用户画像管理 —— SQLite 持久化用户角色、身份信息与偏好"""
import json
from datetime import datetime
from typing import Optional
from .db import get_cursor


def upsert_profile(user_id: str, role: str = "guest", student_id: Optional[str] = None,
                   display_name: str = "用户", department: Optional[str] = None,
                   grade: Optional[str] = None) -> dict:
    """新增或更新用户画像（按 user_id 唯一）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO user_profile (user_id, role, student_id, display_name, department, grade, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "role = excluded.role, "
            "student_id = excluded.student_id, "
            "display_name = excluded.display_name, "
            "department = COALESCE(excluded.department, user_profile.department), "
            "grade = COALESCE(excluded.grade, user_profile.grade), "
            "interaction_count = user_profile.interaction_count + 1, "
            "last_seen_at = excluded.last_seen_at, "
            "updated_at = excluded.last_seen_at",
            (user_id, role, student_id, display_name, department, grade, now))
    return get_profile(user_id)


def get_profile(user_id: str) -> Optional[dict]:
    """读取用户画像"""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["preferences"] = json.loads(d.get("preferences", "{}"))
            return d
    return None


def update_preferences(user_id: str, key: str, value) -> Optional[dict]:
    """更新用户偏好（JSON 存储）"""
    profile = get_profile(user_id)
    if profile is None:
        return None
    prefs = profile.get("preferences", {})
    prefs[key] = value
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_cursor() as cur:
        cur.execute(
            "UPDATE user_profile SET preferences = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(prefs, ensure_ascii=False), now, user_id)
        )
    profile["preferences"] = prefs
    return profile


def get_profile_summary(user_id: str) -> str:
    """生成用户画像摘要，用于注入 Supervisor prompt"""
    p = get_profile(user_id)
    if not p:
        return ""
    parts = [f"角色: {p['role']}", f"姓名: {p['display_name']}"]
    if p.get("department"):
        parts.append(f"院系: {p['department']}")
    if p.get("grade"):
        parts.append(f"年级: {p['grade']}")
    if p.get("student_id"):
        parts.append(f"学号: {p['student_id']}")
    parts.append(f"交互次数: {p['interaction_count']}")
    prefs = p.get("preferences", {})
    if prefs:
        pref_str = ", ".join(f"{k}: {v}" for k, v in list(prefs.items())[:5])
        parts.append(f"偏好: {pref_str}")
    return " | ".join(parts)
