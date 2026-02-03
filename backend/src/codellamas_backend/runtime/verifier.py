from typing import List, Dict, Optional, Iterable, Protocol
from dataclasses import dataclass

from codellamas_backend.tools.maven_tool import MavenTool
from codellamas_backend.tools.workspace import FileLike


class HasPathContent(Protocol):
    path: str
    content: str

def to_filelikes(files: Iterable[HasPathContent]) -> list[FileLike]:
    return [FileLike(path=f.path, content=f.content) for f in files]

@dataclass
class VerificationResult:
    status: str                 # PASS | FAIL | ERROR
    failed_tests: List[str]
    errors: List[str]
    raw_log: str

    def summary(self) -> str:
        return self.raw_log[:4000]


class MavenVerifier:
    """
    Canonical runtime verifier for Spring Boot exercises.

    Responsibilities:
    - Materialize project files into a temp workspace
    - Inject / override code and tests
    - Run mvn test (includes compilation)
    - Return structured, comparable results
    """

    def __init__(self, timeout_sec: int = 180, quiet: bool = True):
        self.maven = MavenTool(timeout_sec=timeout_sec, quiet=quiet)

    def verify(
        self,
        base_project: List[FileLike],
        override_files: Optional[List[FileLike]] = None,
        injected_tests: Optional[Dict[str, str]] = None,
    ) -> VerificationResult:
        override_files = override_files or []
        injected_tests = injected_tests or {}

        result = self.maven.run_tests(
            project_files=base_project,
            override_files=override_files,
            inject_tests=injected_tests,
        )

        return VerificationResult(
            status=result.status,
            failed_tests=result.failed_tests,
            errors=result.errors,
            raw_log=result.raw_log_head(8000),
        )
