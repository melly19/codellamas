from app.api_models import ProjectContext
from app.settings import settings

def pack_context(project: ProjectContext) -> str:
    budget = settings.MAX_CONTEXT_CHARS
    parts = []
    used = 0
    for f in project.files:
        header = f"\n\n### FILE: {f.path}\n"
        chunk = header + f.content
        if used + len(chunk) > budget:
            break
        parts.append(chunk)
        used += len(chunk)
    return "".join(parts)
