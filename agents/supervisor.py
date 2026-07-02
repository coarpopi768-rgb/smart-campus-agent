"""Supervisor Agent - orchestrates tool workers with transparent reasoning chain, streaming, token tracking and structured logging"""
import re, time, sqlite3, asyncio
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

load_dotenv()


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


def build_supervisor_graph():
    llm = ChatZhipuAI(model="glm-4-plus", api_key=ZHIPUAI_API_KEY, temperature=0.1, timeout=120)

    from tools.db_tool import db_query, set_db_user_context
    from tools.rag_tool import school_rag_query
    from tools.email_tool import send_email, set_email_user_context
    from tools.baidu_tool import baidu_search

    tool_map = {
        "db_worker": db_query,
        "rag_worker": school_rag_query,
        "email_worker": send_email,
        "search_worker": baidu_search,
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

        decision = llm.invoke([SystemMessage(content=SUPERVISOR_PROMPT), HumanMessage(content=ctx)])
        raw = decision.content.strip()
        iter_no = state.get("iteration_count", 0)
        nw = "FINISH"
        think = ""
        decision_text = ""

        # Parse [THINK]/[DECISION] sections
        think_match = re.search(r'\[THINK\](.*?)(?=\[DECISION\]|\Z)', raw, re.DOTALL | re.IGNORECASE)
        decide_match = re.search(r'\[DECISION\](.*)', raw, re.DOTALL | re.IGNORECASE)

        if think_match:
            think = think_match.group(1).strip()
        if decide_match:
            decision_text = decide_match.group(1).strip()
            if decision_text.upper().startswith("NEXT:"):
                candidate = decision_text.split("NEXT:")[-1].strip().lower()
                if candidate in tool_map:
                    if role == "guest" and candidate in ("db_worker", "email_worker"):
                        nw = "FINISH"
                        think = (think + f" [BLOCKED: guest cannot use {candidate}]").strip()
                    else:
                        nw = candidate

        # Fallback: if model ignores format, try raw text
        if nw == "FINISH" and "NEXT:" in raw.upper():
            candidate = raw.upper().split("NEXT:")[-1].strip().lower()
            if candidate in tool_map:
                if not (role == "guest" and candidate in ("db_worker", "email_worker")):
                    nw = candidate
                    think = raw[:200]

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

            _logger().worker_start(session, name, query[:100])

            try:
                if name == "db_worker":
                    set_db_user_context(
                        role=state.get("user_role", "guest"),
                        user_id=state.get("authenticated_user_id"),
                        student_id=state.get("student_id"),
                        display_name=state.get("display_name", "Guest"),
                    )
                    result = tool.invoke({"question": query})
                elif name in ("rag_worker", "search_worker"):
                    result = tool.invoke({"query": query})
                elif name == "email_worker":
                    set_email_user_context(
                        role=state.get("user_role", "guest"),
                    )
                    result = tool.invoke({"to": "", "subject": "", "body": query})
                else:
                    result = tool.invoke({"query": query})
                output = str(result)
                status = "error" if "[Error]" in output or "[??]" in output else "success"
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


_app = None

def get_supervisor():
    global _app
    if _app is None:
        _app = build_supervisor_graph().compile(checkpointer=_get_checkpointer())
    return _app


def run_supervisor(user_query, session_id="default", user_role="guest",
                   authenticated_user_id=None, display_name="Guest", debug=False,
                   student_id=None):
    """Run supervisor. Returns dict with "response" and optionally debug info.

    The result includes "think_chain" (list of {iteration, think, decision})
    when debug=True.
    """
    sup = get_supervisor()
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
    sup = get_supervisor()
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
