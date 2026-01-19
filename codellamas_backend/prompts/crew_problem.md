Generate the exercise definition. Output ONLY one JSON object.

Schema:
{
  "problem_md": "markdown",
  "instructions_md": "markdown",
  "target_files": ["src/main/java/..."],
  "constraints": ["..."]
}

Topic: {topic}
Selected smells: {smells}
Seed: {seed}

Project context:
{project_context}

Rules:
- Must be grounded in the given project context (classes, packages, naming).
- Smells must be truly present and refactoring must be meaningful.
- Keep it runnable in a Maven Spring Boot project.
