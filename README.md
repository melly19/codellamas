# codellamas - Java Spring Boot Refactoring Exercise Generator
codellamas is a VSCode Extension that generates and evaluates **Java Spring Boot code refactoring exercises** using AI agents.

It helps students practice identifying and fixing code smells by:
- Generating realistic Spring Boot exercises
- Injecting test cases
- Verifying solutions with Maven
- Providing AI-powered feedback

---

## Features

- **AI-Orchestrated Exercise Generation**
  - Uses CrewAI-based agents to generate refactoring tasks
  - Supports single-agent and multi-agent modes

- **Automated Maven Verification**
  - Runs `mvn test` on generated or submitted code
  - Injects custom test cases
  - Reports failed tests and errors

- **AI-Powered Code Review**
  - Reviews student submissions
  - Integrates real test results into feedback
  - Supports custom student queries

- **Exercise Archiving**
  - Saves generated exercises locally
  - Logs evaluation results to CSV

---

## Key Components (Backend)

| Component | Description |
|-----------|-------------|
| `api.py` | Main FastAPI server |
| `crew_single.py` | Single-agent workflow with optional fix loop|
| `crew_multi.py` | Multi-agent workflow with mandatory fix loop |
| `verifier.py` | Maven verification interface |
| `maven_tool.py` | Runs Maven and parses output |
| `workspace.py` | Manages temporary projects |
| `agents_*.yaml` | CrewAI agent definitions |
| `tasks_*.yaml` | CrewAI task definitions |

---

## Setup

### Prerequisites

- Python 3.9+
- Java 17+
- Maven 3.8+
- Node.js
- OpenAI / LLM API key (if required)

### Install Dependencies (requirements.txt in progress)

```bash
pip install -r requirements.txt
```

### Running the Backend
Refer to README.md in ./backend