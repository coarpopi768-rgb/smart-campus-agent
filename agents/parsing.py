"""Supervisor 输出解析 —— 纯函数模块，无外部依赖，便于单元测试复用。

Supervisor 要求 LLM 按固定格式输出 [THINK]/[DECISION] 两个小节，
本模块负责把模型输出解析为结构化决策，并处理模型不遵守格式时的容错。
"""
import re
from typing import Tuple

# 合法的 Worker 名称（与 agents/supervisor.py 中 tool_map 的键保持一致）
VALID_WORKERS = ("db_worker", "rag_worker", "email_worker", "search_worker")


def parse_supervisor_output(raw: str) -> Tuple[str, str, str]:
    """解析 LLM 的 [THINK]/[DECISION] 输出。

    返回三元组 (next_worker, think, decision_text)：
    - next_worker: 分派目标，取值 VALID_WORKERS 之一或 "FINISH"
    - think: [THINK] 小节中的推理内容（可能为空）
    - decision_text: [DECISION] 小节的原始文本（用于日志/调试）

    容错策略：
    1. 优先按 [THINK]/[DECISION] 小节解析；
    2. 若模型忽略了格式但原文包含 "NEXT: xxx"，则回退从原文提取；
    3. 非法 worker 名一律视为 FINISH（宁可不执行，也不调用未知工具）。
    """
    nw = "FINISH"
    think = ""
    decision_text = ""

    think_match = re.search(r'\[THINK\](.*?)(?=\[DECISION\]|\Z)', raw, re.DOTALL | re.IGNORECASE)
    decide_match = re.search(r'\[DECISION\](.*)', raw, re.DOTALL | re.IGNORECASE)

    if think_match:
        think = think_match.group(1).strip()
    if decide_match:
        decision_text = decide_match.group(1).strip()
        if decision_text.upper().startswith("NEXT:"):
            candidate = decision_text.split("NEXT:")[-1].strip().lower()
            if candidate in VALID_WORKERS:
                nw = candidate

    # 容错：模型忽略格式时，尝试从原文中提取
    if nw == "FINISH" and "NEXT:" in raw.upper():
        candidate = raw.upper().split("NEXT:")[-1].strip().lower()
        if candidate in VALID_WORKERS:
            nw = candidate
            think = raw[:200]

    return nw, think, decision_text
