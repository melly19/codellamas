# CodeLlamas Backend (CrewAI + Ollama + Maven)

## Prereqs
- Python 3.11+
- Java 17+
- Maven
- Ollama running locally:
  - `ollama pull phi4`
  - `ollama serve` (if needed)

## Setup
```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
