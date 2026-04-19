# codellamas - Java Spring Boot Refactoring Exercise Generator
codellamas is a VSCode Extension that generates and evaluates **Java Spring Boot code refactoring exercises** using AI agents.

It helps students practice identifying and fixing code smells by:
- Generating realistic Spring Boot exercises
- Injecting test cases
- Verifying solutions with Maven
- Providing AI-powered feedback

## Backend

Requirements: Python `>=3.10` and `<3.14`.

Install `uv` if needed:

```bash
pip install uv
pip3 instal uv #Mac
```

Fill in `backend/.env` with the required values first, especially `MODEL` and `API_BASE`.

### Run locally

```bash
cd backend
crewai install
source .venv/bin/activate  # macOS
cd src/codellamas_backend
source .venv/bin/activate  #FOR MAC
uv add litellm
uv add apscheduler
uvicorn api:app --reload
```

If you want to use Ollama locally, start the model in another terminal first:

```bash
ollama pull phi4
ollama run phi4:latest
```

To check running models:

```bash
ollama ps
```

If you need a clean reinstall:

```bash
cd backend
deactivate
rm -rf .venv
rm uv.lock
```

### Run with Docker

```bash
cd backend
docker compose up --build
```
