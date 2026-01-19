from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any

Mode = Literal["single", "multi"]

class ProjectFile(BaseModel):
    path: str
    content: str

class ProjectContext(BaseModel):
    root_name: str = "springboot-project"
    files: List[ProjectFile] = Field(default_factory=list)

class GenerateExerciseRequest(BaseModel):
    topic: str
    code_smells: List[str] = Field(default_factory=list)
    mode: Mode = "multi"
    seed: int = 42
    project: ProjectContext

class ExerciseArtifact(BaseModel):
    problem_md: str
    instructions_md: str
    tests: Dict[str, str]
    solution: Dict[str, str]
    review_notes: str = ""

class GenerateExerciseResponse(BaseModel):
    run_id: str
    seed: int
    mode: Mode
    artifacts: ExerciseArtifact
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

class EvaluateSubmissionRequest(BaseModel):
    run_id: Optional[str] = None
    seed: int = 42
    project: ProjectContext
    student_files: List[ProjectFile] = Field(default_factory=list)
    tests: Dict[str, str] = Field(default_factory=dict)

class EvaluateSubmissionResponse(BaseModel):
    run_id: str
    status: Literal["PASS", "FAIL"]
    failed_tests: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    raw_log: str = ""
    feedback: str = ""
