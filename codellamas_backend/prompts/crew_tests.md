You will generate JUnit tests for the exercise.

Input problem JSON:
{problem_json}

Output ONLY one JSON object:

{
  "tests": {
    "src/test/java/...Test.java": "file content",
    "...": "..."
  }
}

Rules:
- Tests MUST compile and run with `mvn test`.
- Use JUnit 5 by default.
- Make sure package names match the project's existing structure as much as possible.
Seed: {seed}
