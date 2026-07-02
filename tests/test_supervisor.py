"""Tests: Supervisor Routing Logic - Python 3.7+ compatible"""
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('zhipuai_api_key', 'test-key')

import re
from typing import Tuple

SIMULATED_RESPONSES = {
    "lookup_score": (
        "[THINK] User wants to check Zhang San's exam scores. "
        "This requires database access via db_worker. No email needed.\n\n"
        "[DECISION] NEXT: db_worker"
    ),
    "campus_rules": (
        "[THINK] User asking about school leave process. "
        "This is campus knowledge, use rag_worker.\n\n"
        "[DECISION] NEXT: rag_worker"
    ),
    "email_notify": (
        "[THINK] User wants to send notification email. "
        "Only email_worker can handle this.\n\n"
        "[DECISION] NEXT: email_worker"
    ),
    "external_search": (
        "[THINK] User asks about Turing Award info. "
        "This is external knowledge, use search_worker.\n\n"
        "[DECISION] NEXT: search_worker"
    ),
    "casual_chat": (
        "[THINK] User just saying hello. "
        "No worker needed, just reply directly.\n\n"
        "[DECISION] FINISH"
    ),
    "multi_step": (
        "[THINK] User wants to check Zhang San's score AND email it. "
        "First: db_worker for scores. Then: email_worker if needed.\n\n"
        "[DECISION] NEXT: db_worker"
    ),
    "old_format": "NEXT: db_worker",
    "no_format": "I think you should use the database worker for this query.",
}


def parse_supervisor_response(raw):
    # type: (str) -> Tuple[str, str, str]
    """Replicate the parsing logic from supervisor_node."""
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
            if candidate in ("db_worker", "rag_worker", "email_worker", "search_worker"):
                nw = candidate

    if nw == "FINISH" and "NEXT:" in raw.upper():
        candidate = raw.upper().split("NEXT:")[-1].strip().lower()
        if candidate in ("db_worker", "rag_worker", "email_worker", "search_worker"):
            nw = candidate
            think = raw[:200]

    return nw, think, decision_text


def test_parse_db_worker():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["lookup_score"])
    assert nw == "db_worker", "Expected db_worker, got {}".format(nw)
    assert "check" in think.lower() and "zhang" in think.lower() and "score" in think.lower()

def test_parse_rag_worker():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["campus_rules"])
    assert nw == "rag_worker", "Expected rag_worker, got {}".format(nw)

def test_parse_email_worker():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["email_notify"])
    assert nw == "email_worker", "Expected email_worker, got {}".format(nw)

def test_parse_search_worker():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["external_search"])
    assert nw == "search_worker", "Expected search_worker, got {}".format(nw)

def test_parse_finish():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["casual_chat"])
    assert nw == "FINISH", "Expected FINISH, got {}".format(nw)

def test_parse_multi_step():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["multi_step"])
    assert nw == "db_worker", "Expected db_worker, got {}".format(nw)

def test_fallback_old_format():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["old_format"])
    assert nw == "db_worker", "Fallback failed, got {}".format(nw)

def test_no_format_graceful():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["no_format"])
    assert nw == "FINISH", "Expected FINISH, got {}".format(nw)

def test_unknown_worker_blocked():
    raw = "[THINK] trying\n[DECISION] NEXT: hacker_worker"
    nw, think, dec = parse_supervisor_response(raw)
    assert nw == "FINISH", "Unknown worker should default to FINISH, got {}".format(nw)

def test_think_extracted_cleanly():
    nw, think, dec = parse_supervisor_response(SIMULATED_RESPONSES["lookup_score"])
    assert "NEXT:" not in think, "THINK should not contain DECISION text"

def test_empty_response():
    nw, think, dec = parse_supervisor_response("")
    assert nw == "FINISH"

if __name__ == "__main__":
    all_tests = [f for f in dir() if f.startswith('test_')]
    passed = 0
    failed = 0
    for test_name in all_tests:
        try:
            globals()[test_name]()
            print("  PASS  {}".format(test_name))
            passed += 1
        except AssertionError as e:
            print("  FAIL  {}: {}".format(test_name, e))
            failed += 1
        except Exception as e:
            print("  ERROR {}: {}".format(test_name, e))
            failed += 1
    print("\n{} passed, {} failed out of {}".format(passed, failed, len(all_tests)))
    sys.exit(1 if failed else 0)
