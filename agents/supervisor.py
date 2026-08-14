"""Supervisor Agent - orchestrates tool workers with transparent reasoning chain, streaming, token tracking and structured logging"""
import re, time, sqlite3, asyncio, json
from pathlib import Path
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from config.settings import ZHIPUAI_API_KEY
from utils.logger import get_logger
from agents.parsing import parse_supervisor_output
from memory import upsert_profile, get_profile_summary, get_memory_context, extract_and_store
from memory.db import init_memory_tables

load_dotenv()
init_memory_tables()


def _logger():
    """结构化 JSON 日志单例"""
    return get_logger()


class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    next_worker: str
    worker_results: list[dict]
    final_response: str
    iteration_count: int
    session_id: str
    debug_trace: list[dict]
    think_chain: list[dict]
    user_role: str
    authenticated_user_id: str | None
    student_id: str | None
    display_name: str


WORKERS = {
    "db_worker": "Database queries: student info, scores, courses, teachers, statistics",
    "rag_worker": "Campus knowledge: rules, leave process, schedules, scholarships, facilities",
    "email_worker": "Send notification emails (teacher/admin only)",
    "search_worker": "External Baidu Baike search",
}

# 判定 Worker 输出为失败的标记（供状态统计与错误汇总使用）
ERROR_MARKERS = ("[Error]", "[错误]", "[权限不足]", "[??]", "Tool error:", "SQL audit failed", "DB error")

SUPERVISOR_PROMPT = """You are the Supervisor of a campus AI system. Choose the best worker for the user''s question.

Workers:
- db_worker: Database queries (student info, scores, courses, teachers)
- rag_worker: Campus knowledge (rules, leave process, schedules, scholarships)
- email_worker: Send emails (teacher/admin only)
- search_worker: External knowledge search

Rules:
- Guest users can only use rag_worker and search_worker
- Maximum 2 workers per query

You MUST reply in TWO sections:

[THINK]
Explain your reasoning step by step:
1. What does the user want? (main task + side tasks)
2. Which workers are needed and in what order?
3. Why this choice? (brief justification)
Just 1-3 short sentences.

[DECISION]
Reply with ONLY one of:
- NEXT: <worker_name>  (dispatch to worker)
- FINISH  (all done, go to finalize)"""

# 邮件抽取提示词：让 LLM 从用户原话中提取收件人/主题/正文
EMAIL_EXTRACT_PROMPT = """You extract email fields from a user request.
Reply with ONLY a JSON object, no other text:
{"to": "<recipient email>", "subject": "<short subject>", "body": "<message body>"}

Rules:
- If the recipient email is missing or unclear, set "to" to an empty string.
- subject should be a concise summary (<=20 chars).
- body should be the user's original message content.
- Keep the original language of the user message."""


def _parse_email_fields(raw: str, query: str) -> tuple:
    """解析 LLM 抽取的邮件字段 JSON；失败时回退从用户原话提取邮箱。

    返回 (to, subject, body)，收件人无法确定时 to 为空字符串。
    """
    to = subject = body = ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            to = str(data.get("to", "")).strip()
            subject = str(data.get("subject", "")).strip()
            body = str(data.get("body", "")).strip()
        except Exception:
            pass

    # 兜底：从用户原话中提取邮箱
    if not to:
        em = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
        if em:
            to = em.group(0)
    if not subject:
        subject = query[:30]
    if not body:
        body = query
    return to, subject, body


def build_supervisor_graph():
    llm = ChatZhipuAI(model="glm-4-plus", api_key=ZHIPUAI_API_KEY, temperature=0.1, timeout=120)

    from tools.db_tool import db_query
    from tools.rag_tool import school_rag_query
    from tools.email_tool import send_email
    from tools.baidu_tool import baidu_search

    tool_map = {
        "db_worker": db_query,
        "rag_worker": school_rag_query,
        "email_worker": send_email,
        "search_worker": baidu_search,
    }

    def _user_context(state: SupervisorState) -> dict:
        """构造传给工具的用户上下文（作为普通工具入参显式传递）。

        注意：langchain-core 1.x 会把参数名为 config 的入参特殊处理并丢弃，
        因此这里用独立的 user_context 参数传递，避免跨用户串号。
        """
        return {
            "role": state.get("user_role", "guest"),
            "user_id": state.get("authenticated_user_id"),
            "student_id": state.get("student_id"),
            "display_name": state.get("display_name", "Guest"),
        }

    workflow = StateGraph(SupervisorState)

    def supervisor_node(state: SupervisorState, config: RunnableConfig) -> dict:
        start = time.time()
        role = state.get("user_role", "guest")
        name = state.get("display_name", "Guest")
        session = config.get("configurable", {}).get("thread_id", "unknown")

        ctx = f"[System] User: {name}, Role: {role}\n"
        results = state.get("worker_results", [])
        if results:
            ctx += "Previous results:\n"
            for r in results:
                ctx += f"- [{r.get('worker','?')}] {str(r.get('result',''))[:200]}\n"
        ctx += f"\nUser: {state['user_query']}"

        if role == "guest":
            ctx += "\n[Note: guest - only rag_worker and search_worker allowed]"

        # Inject long-term memory context
        auth_id = state.get('authenticated_user_id', '')
        if auth_id:
            mem_ctx = get_memory_context(auth_id, query=state['user_query'], max_facts=4)
            if mem_ctx:
                ctx = mem_ctx + "\n\n" + ctx

        decision = llm.invoke([SystemMessage(content=SUPERVISOR_PROMPT), HumanMessage(content=ctx)])
        raw = decision.content.strip()
        iter_no = state.get("iteration_count", 0)

        # 解析 [THINK]/[DECISION]（含格式容错，见 agents/parsing.py）
        nw, think, decision_text = parse_supervisor_output(raw)

        # RBAC 硬校验：guest 禁止使用 db_worker / email_worker
        if nw != "FINISH" and role == "guest" and nw in ("db_worker", "email_worker"):
            think = (think + f" [BLOCKED: guest cannot use {nw}]").strip()
            nw = "FINISH"

        elapsed = int((time.time()-start)*1000)

        # Track token usage
        try:
            meta = decision.response_metadata if hasattr(decision, 'response_metadata') else {}
            usage = meta.get('token_usage', {}) if isinstance(meta, dict) else {}
            prompt_tokens = usage.get('prompt_tokens', 0) or meta.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0) or meta.get('completion_tokens', 0)
            if prompt_tokens or completion_tokens:
                _logger().token_usage(session, "supervisor", prompt_tokens, completion_tokens)
        except Exception:
            pass

        _logger().supervisor_think(session, iter_no, think, nw, elapsed)

        return {
            "next_worker": nw,
            "think_chain": [{"iteration": iter_no, "think": think, "decision": nw, "decision_raw": decision_text[:100]}],
            "debug_trace": [{"node": "supervisor", "think": think, "decision": nw, "elapsed_ms": elapsed}]
        }

    def make_worker_node(name, tool):
        def worker_node(state: SupervisorState, config: RunnableConfig) -> dict:
            start = time.time()
            query = state["user_query"]
            session = config.get("configurable", {}).get("thread_id", "unknown")
            user_ctx = _user_context(state)

            _logger().worker_start(session, name, query[:100])

            try:
                if name == "db_worker":
                    result = tool.invoke({"question": query, "user_context": user_ctx})
                elif name in ("rag_worker", "search_worker"):
                    result = tool.invoke({"query": query})
                elif name == "email_worker":
                    # 先由 LLM 抽取收件人/主题/正文，再调用邮件工具（否则参数为空必然失败）
                    extraction = llm.invoke([
                        SystemMessage(content=EMAIL_EXTRACT_PROMPT),
                        HumanMessage(content=query)
                    ]).content
                    to, subject, body = _parse_email_fields(extraction, query)
                    if not to:
                        result = "[错误] 无法识别收件人邮箱，请提供收件人地址后重试。"
                    else:
                        result = tool.invoke({
                            "to": to, "subject": subject, "body": body,
                            "user_role": user_ctx.get("role", "guest"),
                        })
                else:
                    result = tool.invoke({"query": query})
                output = str(result)
                status = "error" if any(marker in output for marker in ERROR_MARKERS) else "success"
            except Exception as e:
                output = f"Tool error: {e}"
                status = "error"

            elapsed = int((time.time()-start)*1000)
            _logger().worker_done(session, name, status, elapsed, output[:200])

            return {
                "worker_results": [{"worker": name, "result": output, "status": status, "elapsed_ms": elapsed}],
                "iteration_count": state.get("iteration_count",0)+1,
                "debug_trace": [{"node": name, "status": status, "elapsed_ms": elapsed}]
            }
        return worker_node

    def finalize_node(state: SupervisorState, config: RunnableConfig) -> dict:
        start = time.time()
        results = state.get("worker_results", [])
        role = state.get("user_role", "guest")
        name = state.get("display_name", "Guest")
        session = config.get("configurable", {}).get("thread_id", "unknown")

        if not results:
            response = llm.invoke([
                SystemMessage(content=f"You are a campus AI assistant. User: {name} ({role})."),
                HumanMessage(content=state["user_query"])
            ]).content
        else:
            all_failed = all(r.get("status") != "success" for r in results)
            if all_failed:
                errs = []
                for r in results:
                    w = r.get("worker", "?")
                    e = str(r.get("result", ""))[:300]
                    errs.append(f"- [{w}] {e}")
                response = "Query failed. Details:\n" + "\n".join(errs)
            else:
                summary = "\n".join([f"[{r['worker']}]: {r['result']}" for r in results])
                response = llm.invoke([
                    SystemMessage(content=f"You are a campus AI assistant. Summarize results. User: {name} ({role})."),
                    HumanMessage(content=f"Question: {state['user_query']}\nResults:\n{summary}\n\nReply concisely:")
                ]).content

        elapsed = int((time.time()-start)*1000)
        _logger().finalize(session, elapsed, len(response))

        return {
            "final_response": response,
            "messages": [AIMessage(content=response)],
            "debug_trace": [{"node": "finalize", "elapsed_ms": elapsed}]
        }

    workflow.add_node("supervisor", supervisor_node)
    for name, tool in tool_map.items():
        workflow.add_node(name, make_worker_node(name, tool))
    workflow.add_node("finalize", finalize_node)

    def route_supervisor(state):
        nw = state.get("next_worker", "FINISH")
        if state.get("iteration_count", 0) >= 3:
            return "finalize"
        return nw if nw in tool_map else "finalize"

    def route_after_worker(state):
        return "supervisor"

    workflow.add_edge(START, "supervisor")
    route_map = {w: w for w in tool_map}
    route_map["finalize"] = "finalize"
    workflow.add_conditional_edges("supervisor", route_supervisor, route_map)
    for name in tool_map:
        workflow.add_conditional_edges(name, route_after_worker, {"supervisor": "supervisor"})
    workflow.add_edge("finalize", END)

    return workflow


def _get_checkpointer():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(str(Path("data") / "agent_memory.db"), check_same_thread=False)
    return SqliteSaver(conn)


def _get_async_checkpointer_cm():
    """异步流式路径使用的 checkpointer 上下文管理器。

    注意：langgraph-checkpoint-sqlite 3.x 中 from_conn_string 返回的是
    异步上下文管理器（_AsyncGeneratorContextManager），必须 await __aenter__()
    之后才是真正的 AsyncSqliteSaver 实例，不能直接传给 compile()。
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    Path("data").mkdir(exist_ok=True)
    return AsyncSqliteSaver.from_conn_string(str(Path("data") / "agent_memory.db"))


_app = None
_app_async = None
# 持有 from_conn_string 返回的异步上下文管理器。
# 关键：若让其被 GC 回收，异步生成器终结器会自动 aclose() 并关闭 aiosqlite 连接，
# 导致后续请求报 "Cannot operate on a closed database"。
_async_saver_cm = None

def get_supervisor():
    global _app
    if _app is None:
        _app = build_supervisor_graph().compile(checkpointer=_get_checkpointer())
    return _app


async def get_supervisor_async():
    """返回支持异步流式（astream_events）的编译图实例（懒初始化 + 复用）"""
    global _app_async, _async_saver_cm
    if _app_async is None:
        _async_saver_cm = _get_async_checkpointer_cm()
        saver = await _async_saver_cm.__aenter__()
        _app_async = build_supervisor_graph().compile(checkpointer=saver)
    return _app_async


def run_supervisor(user_query, session_id="default", user_role="guest",
                   authenticated_user_id=None, display_name="Guest", debug=False,
                   student_id=None):
    """Run supervisor. Returns dict with "response" and optionally debug info.

    The result includes "think_chain" (list of {iteration, think, decision})
    when debug=True.
    """
    # Upsert user profile
    if authenticated_user_id:
        upsert_profile(authenticated_user_id, role=user_role,
                     student_id=student_id, display_name=display_name)

    sup = get_supervisor()
    try:
        result = sup.invoke({
        "messages": [HumanMessage(content=user_query)],
        "user_query": user_query,
        "user_role": user_role,
        "authenticated_user_id": authenticated_user_id,
        "student_id": student_id,
        "display_name": display_name,
        "iteration_count": 0,
        "worker_results": [],
    }, config={"configurable": {"thread_id": session_id}})
    except Exception as e:
        import logging
        logging.exception("Supervisor invoke failed")
        return {"response": "[系统错误] AI 服务暂时不可用: " + str(e)}

    # Extract facts from conversation for long-term memory
    if authenticated_user_id:
        try:
            extract_and_store(authenticated_user_id, user_query,
                            result.get("final_response", ""),
                            session_id=session_id)
        except Exception:
            pass

    out = {"response": result.get("final_response", "Error")}
    if debug:
        out["debug_trace"] = result.get("debug_trace", [])
        out["think_chain"] = result.get("think_chain", [])
        out["worker_results"] = result.get("worker_results", [])
        out["iteration_count"] = result.get("iteration_count", 0)
    return out


async def run_supervisor_stream(user_query, session_id="default", user_role="guest",
                                authenticated_user_id=None, display_name="Guest",
                                student_id=None):
    """Stream supervisor execution via LangGraph astream_events.

    Yields dicts: {"type": "supervisor_thinking"|"worker_start"|"worker_done"
                    |"finalize"|"done", ...}
    """
    # Upsert user profile
    if authenticated_user_id:
        upsert_profile(authenticated_user_id, role=user_role,
                     student_id=student_id, display_name=display_name)

    sup = await get_supervisor_async()
    response = ""
    try:
        initial = {
        "messages": [HumanMessage(content=user_query)],
        "user_query": user_query,
        "user_role": user_role,
        "authenticated_user_id": authenticated_user_id,
        "student_id": student_id,
        "display_name": display_name,
        "iteration_count": 0,
        "worker_results": [],
    }

        config = {"configurable": {"thread_id": session_id}}

        think_chain = []
        worker_results = []

        async for event in sup.astream_events(initial, config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_chain_start" and name == "supervisor":
                yield {"type": "supervisor_thinking", "status": "start"}
            elif kind == "on_chain_start" and name in ("db_worker", "rag_worker", "email_worker", "search_worker"):
                yield {"type": "worker_start", "worker": name}
            elif kind == "on_chain_end" and name == "supervisor":
                output = data.get("output", {})
                nw = output.get("next_worker", "FINISH")
                tc = output.get("think_chain", [])
                if tc:
                    think_chain.extend(tc)
                yield {"type": "supervisor_decided", "next_worker": nw, "think_chain": tc}
            elif kind == "on_chain_end" and name in ("db_worker", "rag_worker", "email_worker", "search_worker"):
                output = data.get("output", {})
                wr = output.get("worker_results", [])
                if wr:
                    worker_results.extend(wr)
                yield {"type": "worker_done", "worker": name, "results": wr}
            elif kind == "on_chain_start" and name == "finalize":
                yield {"type": "finalize", "status": "start"}
            elif kind == "on_chain_end" and name == "finalize":
                output = data.get("output", {})
                response = output.get("final_response", "")
                yield {"type": "done", "response": response, "think_chain": think_chain, "worker_results": worker_results}
    except Exception as e:
        import logging
        logging.exception("Supervisor stream failed")
        yield {"type": "done", "response": "[系统错误] AI 服务暂时不可用: " + str(e), "think_chain": [], "worker_results": []}

    # Extract facts for long-term memory
    if authenticated_user_id and response:
        try:
            extract_and_store(authenticated_user_id, user_query, response,
                            session_id=session_id)
        except Exception:
            pass
