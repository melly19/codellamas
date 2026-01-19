import json
from typing import Any, Dict

def extract_json_object(text: str) -> Dict[str, Any]:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start '{' found in output.")
    for end in range(len(text) - 1, start, -1):
        if text[end] == "}":
            candidate = text[start:end+1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    raise ValueError("Could not parse a valid JSON object from output.")
