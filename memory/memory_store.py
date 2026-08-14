"""长期记忆存储 —— SQLite 持久化用户事实，支持重要度与访问频率排序"""
from __future__ import annotations
import json, re
from datetime import datetime
from typing import Optional
from .db import get_cursor, init_memory_tables

# 确保表已创建
init_memory_tables()


def store_fact(user_id: str, fact: str, category: str = "general",
               source_session: str = "", importance: int = 1) -> int:
    """存储一条用户事实；若已存在相同事实则提升重要度并累加访问次数"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_cursor() as cur:
        # 去重：同一用户 + 同一事实视为同一条记忆
        cur.execute(
            "SELECT id FROM user_memory WHERE user_id = ? AND fact = ?",
            (user_id, fact)
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                "UPDATE user_memory SET importance = MAX(importance, ?), "
                "access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                (importance, now, existing["id"])
            )
            return existing["id"]

        cur.execute(
            "INSERT INTO user_memory (user_id, fact, category, source_session, importance, last_accessed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, fact, category, source_session, importance, now)
        )
        return cur.lastrowid


def retrieve_facts(user_id: str, query: str = "", category: str = "",
                   limit: int = 5, min_importance: int = 1) -> list:
    """按重要度/访问次数检索用户记忆，可按类别与关键词过滤"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM user_memory WHERE user_id = ? AND importance >= ?"
    params = [user_id, min_importance]

    if category:
        sql += " AND category = ?"
        params.append(category)

    if query.strip():
        keywords = [w.strip() for w in re.split(r"[\s,\uff0c]+", query) if len(w.strip()) >= 1]
        for kw in keywords:
            sql += " AND fact LIKE ?"
            params.append("%{}%".format(kw))

    sql += " ORDER BY importance DESC, access_count DESC, created_at DESC LIMIT ?"
    params.append(limit)

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

        # 命中即计入访问次数（用于后续排序）
        row_ids = [r["id"] for r in rows]
        if row_ids:
            placeholders = ",".join("?" * len(row_ids))
            cur.execute(
                "UPDATE user_memory SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN ({})".format(placeholders),
                [now] + row_ids
            )
        return [dict(r) for r in rows]


def get_recent_facts(user_id: str, limit: int = 10) -> list:
    """获取最近存入的用户记忆"""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM user_memory WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in cur.fetchall()]


def get_memory_context(user_id: str, query: str = "", max_facts: int = 5) -> str:
    """生成注入 Supervisor prompt 的记忆上下文片段"""
    facts = retrieve_facts(user_id, query=query, limit=max_facts, min_importance=2)
    if not facts:
        facts = get_recent_facts(user_id, limit=3)

    if not facts:
        return ""

    lines = ["[Memory] 以下是该用户的长期记忆"]
    for f in facts:
        cat = f.get("category", "general")
        lines.append("- [{}] {}".format(cat, f["fact"]))
    return "\n".join(lines)


def extract_and_store(user_id: str, user_message: str, assistant_response: str,
                      session_id: str = "", llm=None) -> list:
    """从对话中抽取用户持久事实并存入长期记忆。

    优先使用 LLM 抽取（语义更准）；未传入 llm 或调用失败时回退规则抽取。
    """
    if llm is None:
        return _extract_by_rules(user_id, user_message, assistant_response, session_id)

    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = (
        "从下面的对话中抽取用户相关的持久事实（如身份、偏好、目标、学业信息）。\n"
        "每条事实输出一行，格式：类别: 事实内容\n\n"
        "类别只能是：preference(偏好), identity(身份), academic(学业), personal(个人), goal(目标)\n\n"
        "用户消息：{}\n助手回复：{}\n\n事实："
    ).format(user_message[:500], assistant_response[:500])

    try:
        resp = llm.invoke([
            SystemMessage(content="你是一个用户画像抽取助手，只输出事实列表，不要输出其他内容"),
            HumanMessage(content=prompt)
        ])
        facts = []
        for line in resp.content.strip().split("\n"):
            line = line.strip()
            if ":" in line and line[0].isalpha():
                cat, fact = line.split(":", 1)
                cat = cat.strip().lower()
                fact = fact.strip()
                if len(fact) >= 3:
                    store_fact(user_id, fact, category=cat, source_session=session_id, importance=3)
                    facts.append(fact)
        return facts
    except Exception:
        return _extract_by_rules(user_id, user_message, assistant_response, session_id)


def _extract_by_rules(user_id: str, user_msg: str, assistant_msg: str, session_id: str) -> list:
    """不使用 LLM 时的规则抽取（基于关键词 + 中文标点截断）"""
    facts = []

    patterns = [
        (r"(?:我的名字是|我叫|我是)(.{1,30}?)(?:[，。！？；,\s]|$)", "identity"),
        (r"(?:我读的是|我的专业是|我在读)(.{1,30}?)(?:[，。！？；,\s]|$)", "academic"),
        (r"(?:我喜欢|我偏好|我更倾向于)(.{1,40}?)(?:[，。！？；,\s]|$)", "preference"),
        (r"(?:我的目标是|我计划|我想|我要)(.{1,40}?)(?:[，。！？；,\s]|$)", "goal"),
    ]

    for pattern, category in patterns:
        m = re.search(pattern, user_msg)
        if m and m.group(1).strip():
            fact = m.group(1).strip()[:100]
            store_fact(user_id, fact, category=category, source_session=session_id, importance=2)
            facts.append(fact)

    return facts
