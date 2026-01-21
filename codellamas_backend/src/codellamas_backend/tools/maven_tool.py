from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from codellamas_backend.tools.workspace import Workspace, FileLike


@dataclass
class MavenTestResult:
    status: str  # "PASS" or "FAIL"
    returncode: int
    failed_tests: List[str]
    errors: List[str]
    raw_log: str

    def raw_log_head(self, n: int = 4000) -> str:
        return self.raw_log[:n]


class MavenTool:
    """
    Runs `mvn test` in an isolated temp workspace built from in-memory files.
    """

    def __init__(
        self,
        mvn_cmd: str = "mvn",
        timeout_sec: int = 120,
        quiet: bool = True,
    ):
        self.mvn_cmd = mvn_cmd
        self.timeout_sec = timeout_sec
        self.quiet = quiet

    def run_tests(
        self,
        project_files: List[FileLike],
        override_files: Optional[List[FileLike]] = None,
        inject_tests: Optional[Dict[str, str]] = None,
        extra_mvn_args: Optional[Sequence[str]] = None,
    ) -> MavenTestResult:
        override_files = override_files or []
        inject_tests = inject_tests or {}
        extra_mvn_args = list(extra_mvn_args or [])

        with Workspace(prefix="codelamas_") as ws:
            # 1) materialize base project (from VS Code)
            ws.write_files(project_files)

            # 2) apply student edits (override)
            if override_files:
                ws.write_files(override_files)

            # 3) inject generated tests (path -> content)
            if inject_tests:
                ws.write_file_map(inject_tests)

            # 4) run mvn test
            cmd = [self.mvn_cmd]
            if self.quiet:
                cmd += ["-q"]
            cmd += ["test"]
            cmd += extra_mvn_args

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=ws.root,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                    env=self._safe_env(),
                )
            except subprocess.TimeoutExpired:
                return MavenTestResult(
                    status="FAIL",
                    returncode=124,
                    failed_tests=[],
                    errors=[f"mvn test timed out after {self.timeout_sec}s"],
                    raw_log="",
                )

            raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
            status, failed_tests, errors = self._parse_maven_output(proc.returncode, raw)

            return MavenTestResult(
                status=status,
                returncode=proc.returncode,
                failed_tests=failed_tests,
                errors=errors,
                raw_log=raw,
            )

    def _safe_env(self) -> Dict[str, str]:
        """
        You can add env hardening here later.
        For now, inherit and ensure consistent encoding.
        """
        env = dict(os.environ)
        env.setdefault("MAVEN_OPTS", "")
        return env

    def _parse_maven_output(self, returncode: int, raw: str) -> Tuple[str, List[str], List[str]]:
        if returncode == 0:
            return "PASS", [], []

        errors: List[str] = []
        failed_tests: List[str] = []

        if "COMPILATION ERROR" in raw:
            errors.append("Compilation error")
        if "There are test failures" in raw:
            errors.append("Test failures")
        if "Could not resolve dependencies" in raw or "Could not find artifact" in raw:
            errors.append("Dependency resolution error")
        if "BUILD FAILURE" in raw:
            errors.append("Build failure")

        # Try to find surefire-style failed test names:
        # Examples may include:
        # "Failed tests:   someTest(com.example.MyTest)"
        # "Tests run: X, Failures: Y, Errors: Z, Skipped: W"
        failed_tests += self._extract_failed_tests(raw)

        if not errors:
            errors.append("mvn test failed (see raw_log)")

        # de-dup
        failed_tests = list(dict.fromkeys(failed_tests))[:30]
        errors = list(dict.fromkeys(errors))[:20]
        return "FAIL", failed_tests, errors

    def _extract_failed_tests(self, raw: str) -> List[str]:
        out: List[str] = []

        # Pattern 1: "Failed tests:   testName(ClassName)"
        m = re.search(r"Failed tests:\s*(.+)", raw, flags=re.IGNORECASE)
        if m:
            out.append(m.group(1).strip())

        # Pattern 2: Common JUnit stack traces show test class names; heuristic:
        for cls in re.findall(r"([a-zA-Z0-9_.]+Test)\b", raw):
            if cls not in out:
                out.append(cls)

        return out
