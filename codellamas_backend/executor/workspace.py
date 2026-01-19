import os, shutil, tempfile
from typing import Dict, List
from app.api_models import ProjectContext, ProjectFile

def create_workspace(project: ProjectContext) -> str:
    tmp = tempfile.mkdtemp(prefix="codelamas_")
    for f in project.files:
        abs_path = os.path.join(tmp, f.path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as out:
            out.write(f.content)
    return tmp

def write_files(root: str, files: Dict[str, str]) -> None:
    for path, content in files.items():
        abs_path = os.path.join(root, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as out:
            out.write(content)

def override_project_files(root: str, override_files: List[ProjectFile]) -> None:
    for f in override_files:
        abs_path = os.path.join(root, f.path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as out:
            out.write(f.content)

def cleanup_workspace(root: str) -> None:
    shutil.rmtree(root, ignore_errors=True)
