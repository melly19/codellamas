## Backend Architecture Overview

**HTTP Request Flow:**
1. HTTP → api.py (FastAPI endpoints)
2. → crew.py (CrewAI orchestrator)
3. → agents.yaml + tasks.yaml (AI instructions)
4. → Maven verification (optional)
5. ← Response

**File Responsibilities:**

**api.py** - FastAPI HTTP endpoints
- `/generate` - Creates exercises with code smells
- `/review` - Evaluates student solutions
- Handles Maven test verification, CSV logging, file persistence

**crew.py** - CrewAI orchestration layer
- Defines `generation_crew()` and `review_crew()` 
- Configures agent (Ollama phi4 LLM)
- Links tasks to agent

- Defines output schema (`SpringBootExercise`)

**agents.yaml** - Agent instructions
- Agent role: "University Software Engineering TA"
- Goal: Create educational refactoring exercises
- Personality/expertise definition

**tasks.yaml** - Task instructions
- `generate_exercise`: Detailed prompt for creating exercises (inject code smells, generate tests, provide reference solution)
- `review_solution`: Prompt for evaluating student code (functional correctness, code quality, feedback)

**main.py** - CLI entry point for local testing

**tools/** - Maven test runner and workspace utilities for verifying Java code

**Process:** Client sends topic + code smells → FastAPI routes to crew → CrewAI agent follows YAML instructions → Generates/evaluates with LLM → Returns structured response