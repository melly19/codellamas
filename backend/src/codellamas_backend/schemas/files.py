from pydantic import BaseModel, Field

class ProjectFile(BaseModel):
    path: str = Field(..., description="Relative path e.g., pom.xml or src/main/java/...")
    content: str