"""Enhanced Eval Runner —— 基于真实 LLM 路由 + LLM-as-Judge 语义打分
用法: python tests/run_eval_v2.py
"""
import sys, os, json, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def load_eval_set(path="data/eval_set.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Part 1: 真实 LLM Supervisor 路由评测
# ============================================================

TOOL_MAP = {"db_worker", "rag_worker", "email_worker", "search_worker"}


def eval_supervisor_real(eval_set, limit=10):
    """真实调用 ChatZhipuAI 验证 Supervisor 路由准确率"""
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from config.settings import ZHIPUAI_API_KEY

    llm = ChatZhipuAI(model="glm-4-plus", api_key=ZHIPUAI_API_KEY, temperature=0.1, timeout=120)

    WORKER_DESC = {
        "db_worker": "数据库查询：学生信息、成绩、课程、教师",
        "rag_worker": "校园知识库检索：制度、请假流程、课表、奖学金",
        "email_worker": "发送邮件通知（教师/管理员）",
        "search_worker": "外部知识搜索",
    }

    prompt = """You are the Supervisor of a campus AI system.
For the user's question, choose the single best worker.

Workers:
- db_worker: {db}
- rag_worker: {rag}
- email_worker: {email}
- search_worker: {search}

Rules:
- Guest users can only use rag_worker and search_worker
- If the user just greets or chats, no worker is needed

Reply with EXACTLY one word: the worker name (db_worker, rag_worker, email_worker, search_worker) or NONE.""".format(
        db=WORKER_DESC["db_worker"],
        rag=WORKER_DESC["rag_worker"],
        email=WORKER_DESC["email_worker"],
        search=WORKER_DESC["search_worker"],
    )

    results = []
    test_set = eval_set[:limit] if limit else eval_set
    correct = 0
    total_latency = 0

    print("\n" + "=" * 60)
    print(f"  Supervisor LLM Routing Eval ({len(test_set)} cases)")
    print("=" * 60)

    for i, item in enumerate(test_set):
        query = item["query"]
        role = item.get("user_role", "guest")
        expected = item.get("expected_worker", "FINISH")

        ctx = f"[System] User role: {role}\nUser: {query}"
        if role == "guest":
            ctx += "\n[Note: guest - only rag_worker and search_worker allowed]"

        start = time.time()
        try:
            resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=ctx)])
            decision = resp.content.strip().lower()
        except Exception as e:
            decision = f"ERROR: {e}"

        elapsed_ms = int((time.time() - start) * 1000)
        total_latency += elapsed_ms

        if decision not in TOOL_MAP:
            decision = "FINISH"

        is_correct = (decision == expected)
        if is_correct:
            correct += 1

        status = "PASS" if is_correct else "FAIL"
        print(f"  [{status}] [{role}] {query[:40]}... -> {decision} (expected {expected}) [{elapsed_ms}ms]")

        results.append({
            "query": query,
            "role": role,
            "expected": expected,
            "decision": decision,
            "correct": is_correct,
            "latency_ms": elapsed_ms,
        })

    accuracy = correct / len(test_set) * 100 if test_set else 0
    avg_latency = total_latency / len(test_set) if test_set else 0

    print(f"\n  Accuracy: {correct}/{len(test_set)} = {accuracy:.1f}%")
    print(f"  Avg Latency: {avg_latency:.0f}ms")

    return accuracy, avg_latency, results


# ============================================================
# Part 2: LLM-as-Judge 语义打分
# ============================================================

JUDGE_PROMPT = """You are an evaluator for a campus AI assistant. Rate the assistant's response.

Evaluation criteria (score 1-5 each):
1. Relevance: Does the response directly address the user's question?
2. Accuracy: Is the information factually correct based on campus context?
3. Completeness: Does the response cover what was asked?
4. Clarity: Is the response clear and well-structured?

Output ONLY a JSON object:
{"relevance": <1-5>, "accuracy": <1-5>, "completeness": <1-5>, "clarity": <1-5>, "overall": <1-5>, "comment": "<brief comment>"}"""


def judge_response(query: str, response: str, expected_contains=None) -> dict:
    """LLM-as-Judge: 评价 Agent 回答质量"""
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from config.settings import ZHIPUAI_API_KEY

    llm = ChatZhipuAI(model="glm-4-plus", api_key=ZHIPUAI_API_KEY, temperature=0.0, timeout=60)

    eval_text = f"User question: {query}\n\nAssistant response:\n{response[:800]}"
    if expected_contains:
        eval_text += f"\n\nExpected content keywords: {', '.join(expected_contains)}"

    try:
        resp = llm.invoke([SystemMessage(content=JUDGE_PROMPT), HumanMessage(content=eval_text)])
        content = resp.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception:
        pass

    return {"relevance": 0, "accuracy": 0, "completeness": 0, "clarity": 0, "overall": 0, "comment": "Judge error"}


def run_llm_judge(eval_set, limit=5):
    """对 RAG 回答进行 LLM-as-Judge 打分"""
    from agents.supervisor import run_supervisor

    rag_items = [i for i in eval_set if i.get("expected_worker") == "rag_worker"][:limit]

    if not rag_items:
        print("\n  [Skip] No RAG test cases for LLM Judge")
        return None

    print("\n" + "=" * 60)
    print(f"  LLM-as-Judge Quality Eval ({len(rag_items)} cases)")
    print("=" * 60)

    all_scores = []
    for i, item in enumerate(rag_items):
        query = item["query"]
        role = item.get("user_role", "student")
        expected_kw = item.get("expected_contains", [])

        print(f"  [{i+1}/{len(rag_items)}] Running supervisor for: {query[:50]}...")
        result = run_supervisor(query, session_id=f"eval_{i}", user_role=role,
                                display_name=f"Eval{role}", debug=False)
        response = result.get("response", "")

        judge = judge_response(query, response, expected_kw)
        all_scores.append(judge)

        overall = judge.get("overall", 0)
        star = "\u2605" * int(overall) + "\u2606" * (5 - int(overall))
        comment = judge.get("comment", "")[:60]
        print(f"    Score: {star} ({overall}/5) | {comment}")

    if all_scores:
        avg_overall = sum(s.get("overall", 0) for s in all_scores) / len(all_scores)
        avg_rel = sum(s.get("relevance", 0) for s in all_scores) / len(all_scores)
        avg_acc = sum(s.get("accuracy", 0) for s in all_scores) / len(all_scores)
        avg_comp = sum(s.get("completeness", 0) for s in all_scores) / len(all_scores)
        avg_cla = sum(s.get("clarity", 0) for s in all_scores) / len(all_scores)

        print(f"\n  Avg Scores:")
        print(f"    Relevance:   {avg_rel:.1f}/5")
        print(f"    Accuracy:    {avg_acc:.1f}/5")
        print(f"    Completeness:{avg_comp:.1f}/5")
        print(f"    Clarity:     {avg_cla:.1f}/5")
        print(f"    Overall:     {avg_overall:.1f}/5")

        return {
            "avg_overall": avg_overall,
            "avg_relevance": avg_rel,
            "avg_accuracy": avg_acc,
            "avg_completeness": avg_comp,
            "avg_clarity": avg_cla,
            "details": all_scores,
        }
    return None


# ============================================================
# Part 3: 汇总输出
# ============================================================

def run_full_eval_v2(limit_real_llm=10, limit_judge=5):
    print("\n" + "=" * 60)
    print("  Smart Campus AI -- Enhanced Evaluation Report v2")
    print("  Time: {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 60)

    eval_set = load_eval_set()
    print(f"\n  Loaded {len(eval_set)} eval cases")

    routing_acc = None
    routing_lat = None
    judge_scores = None

    # 1. 真实 LLM 路由评测
    try:
        routing_acc, routing_lat, routing_results = eval_supervisor_real(eval_set, limit=limit_real_llm)
    except Exception as e:
        print(f"\n  [SKIP] Real LLM routing eval failed: {e}")

    # 2. LLM-as-Judge 打分
    try:
        judge_scores = run_llm_judge(eval_set, limit=limit_judge)
    except Exception as e:
        print(f"\n  [SKIP] LLM Judge failed: {e}")

    # 汇总
    print("\n" + "=" * 60)
    print("  SUMMARY")
    if routing_acc is not None:
        print(f"  LLM Routing Accuracy:     {routing_acc:.1f}%")
        print(f"  Avg Routing Latency:      {routing_lat:.0f}ms")
    if judge_scores:
        print(f"  LLM-as-Judge Overall:     {judge_scores['avg_overall']:.1f}/5")
        print(f"  LLM-as-Judge Relevance:   {judge_scores['avg_relevance']:.1f}/5")
        print(f"  LLM-as-Judge Accuracy:    {judge_scores['avg_accuracy']:.1f}/5")
    print("=" * 60 + "\n")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_size": len(eval_set),
        "routing_accuracy": routing_acc,
        "routing_avg_latency_ms": routing_lat,
        "judge_scores": judge_scores,
    }

    # 保存报告
    report_path = "data/eval_report_v2.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"  Report saved to {report_path}")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enhanced Agent Evaluation")
    parser.add_argument("--routing", type=int, default=10, help="Number of routing test cases (0 to skip)")
    parser.add_argument("--judge", type=int, default=5, help="Number of LLM Judge cases (0 to skip)")
    args = parser.parse_args()

    try:
        run_full_eval_v2(limit_real_llm=args.routing, limit_judge=args.judge)
    except ImportError as e:
        print(f"\n  [SKIP] Missing dependency: {e}")
        print("  Install: pip install langchain-community langchain-core zhipuai python-dotenv")
    except Exception as e:
        print(f"\n  [ERROR] Eval failed: {e}")
        import traceback
        traceback.print_exc()
