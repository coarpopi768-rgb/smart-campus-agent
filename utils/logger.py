"""Structured JSON logger for multi-agent observability."""
import logging, json, time, os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class AgentLogger:
    """JSON-structured logger with node-level tracing for multi-agent systems."""

    def __init__(self, name: str = "campus-agent"):
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        # File handler: JSON lines
        fh = logging.FileHandler(LOG_DIR / "agent.jsonl", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(fh)

        # Console handler: human-readable
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"))
        self._logger.addHandler(ch)

    def _emit(self, level: str, msg: str, **kv):
        record = {
            "timestamp": time.time(),
            "level": level,
            "agent": self.name,
            "message": msg,
            **kv
        }
        self._logger.log(getattr(logging, level.upper(), logging.INFO), json.dumps(record, ensure_ascii=False))

    def info(self, msg: str, **kv):     self._emit("info", msg, **kv)
    def warn(self, msg: str, **kv):     self._emit("warning", msg, **kv)
    def error(self, msg: str, **kv):    self._emit("error", msg, **kv)
    def debug(self, msg: str, **kv):    self._emit("debug", msg, **kv)

    # Agent-specific structured methods
    def supervisor_think(self, session: str, iteration: int, think: str, decision: str, elapsed_ms: int):
        self.info("Supervisor decision", node="supervisor", session=session,
                  iteration=iteration, think=think[:300], decision=decision, elapsed_ms=elapsed_ms)

    def worker_start(self, session: str, worker: str, query_preview: str):
        self.info("Worker started", node=worker, session=session, query=query_preview[:100])

    def worker_done(self, session: str, worker: str, status: str, elapsed_ms: int, result_preview: str = ""):
        self.info("Worker finished", node=worker, session=session,
                  status=status, elapsed_ms=elapsed_ms, result=result_preview[:200])

    def finalize(self, session: str, elapsed_ms: int, response_len: int):
        self.info("Response generated", node="finalize", session=session,
                  elapsed_ms=elapsed_ms, response_length=response_len)

    def token_usage(self, session: str, node: str, prompt_tokens: int, completion_tokens: int):
        self.info("Token usage", node=node, session=session,
                  prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                  total_tokens=prompt_tokens + completion_tokens)

    def error_trace(self, session: str, node: str, error: str):
        self.error("Agent error", node=node, session=session, error=str(error)[:500])


# Singleton
_log_instance = None

def get_logger(name: str = "campus-agent") -> AgentLogger:
    global _log_instance
    if _log_instance is None:
        _log_instance = AgentLogger(name)
    return _log_instance

# Backward-compatible convenience logger
logger = logging.getLogger("campus-agent")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
