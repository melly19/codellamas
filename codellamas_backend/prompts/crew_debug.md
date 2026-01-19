You will fix failing tests.

Problem JSON:
{problem_json}

Current Tests JSON:
{tests_json}

Current Solution JSON:
{solution_json}

Execution Report (from mvn test):
{exec_report}

Output ONLY one JSON object:

{
  "tests_obj": { "tests": { "path": "content", "...": "..." } },
  "solution_obj": { "solution": { "path": "content", "...": "..." } },
  "notes": "brief explanation"
}

Rules:
- Prefer fixing the SOLUTION over weakening tests.
- Only change tests if tests are incorrect/impossible.
- Keep changes minimal.
Seed: {seed}
