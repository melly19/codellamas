You generate a refactoring/code review exercise for a Java Spring Boot Maven project.

Return ONLY a single JSON object:

{
  "problem_md": "...",
  "instructions_md": "...",
  "tests": { "src/test/java/...": "..." },
  "solution": { "src/main/java/...": "..." }
}

Topic: {topic}
Selected smells: {smells}
Seed: {seed}

Project context:
{project_context}
