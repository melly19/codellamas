import subprocess
from typing import Dict, Any, List
from app.settings import settings
from app.logging_utils import log_event
from app.api_models import ProjectContext, ProjectFile
from .workspace import create_workspace, write_files, override_project_files, cleanup_workspace
from .result_parser import parse_maven_output

def run_maven_tests(
    run_id: str,
    project: ProjectContext,
    override_files: List[ProjectFile],
    inject_tests: Dict[str, str],
) -> Dict[str, Any]:
    root = create_workspace(project)
    try:
        if override_files:
            override_project_files(root, override_files)
        if inject_tests:
            write_files(root, inject_tests)

        cmd = [settings.MVN_CMD, "-q", "test"]
        log_event(run_id, "maven.run", {"cmd": cmd})

        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=settings.MVN_TEST_TIMEOUT_SEC
        )

        raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
        parsed = parse_maven_output(proc.returncode, raw)

        log_event(run_id, "maven.result", {"status": parsed["status"], "returncode": proc.returncode})
        return {**parsed, "raw_log": raw}

    except subprocess.TimeoutExpired:
        msg = f"Maven tests timed out after {settings.MVN_TEST_TIMEOUT_SEC}s"
        log_event(run_id, "maven.timeout", {"error": msg})
        return {"status": "FAIL", "failed_tests": [], "errors": [msg], "raw_log": ""}

    finally:
        cleanup_workspace(root)
