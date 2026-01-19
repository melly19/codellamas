import re
from typing import Dict, Any, List

FAIL_RE = re.compile(r"Failed tests:\s*(.*)", re.IGNORECASE)
TEST_LINE_RE = re.compile(r"^\s*([a-zA-Z0-9_.]+)\s*\(", re.MULTILINE)

def parse_maven_output(returncode: int, raw: str) -> Dict[str, Any]:
    if returncode == 0:
        return {"status": "PASS", "failed_tests": [], "errors": []}

    failed_tests: List[str] = []
    errors: List[str] = []

    m = FAIL_RE.search(raw)
    if m:
        failed_tests.append(m.group(1).strip())

    for cls in TEST_LINE_RE.findall(raw):
        if cls.endswith("Test") and cls not in failed_tests:
            failed_tests.append(cls)

    if "COMPILATION ERROR" in raw:
        errors.append("Compilation error")
    if "There are test failures" in raw:
        errors.append("Test failures")
    if "Could not resolve dependencies" in raw or "Could not find artifact" in raw:
        errors.append("Maven dependency resolution error")

    if not errors:
        errors.append("Maven test failed (see raw_log)")

    return {"status": "FAIL", "failed_tests": failed_tests[:20], "errors": errors[:20]}
