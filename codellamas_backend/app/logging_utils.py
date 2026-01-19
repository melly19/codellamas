import json, os, time
from typing import Any, Dict
from .settings import settings

def ensure_log_dir() -> str:
    os.makedirs(settings.RUN_LOG_DIR, exist_ok=True)
    return settings.RUN_LOG_DIR

def log_event(run_id: str, event: str, payload: Dict[str, Any]) -> None:
    ensure_log_dir()
    record = {
        "ts": time.time(),
        "run_id": run_id,
        "event": event,
        "payload": payload,
    }
    path = os.path.join(settings.RUN_LOG_DIR, f"{run_id}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
