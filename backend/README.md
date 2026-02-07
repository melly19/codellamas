# CodellamasBackend Crew

Welcome to the CodellamasBackend Crew project, powered by [crewAI](https://crewai.com).

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) 



First, if you haven't already, install uv:
```bash
pip install uv
pip3 instal uv #Mac
```


Uninstall old venv if needed
```bash
cd backend
deactivate
rm -rf .venv
rm uv.lock

```

Next, navigate to your project directory and install the dependencies
crewai install will create virtual environment:
```bash
cd backend
crewai install

```

activate the 
```bash
source .venv/bin/activate  #FOR MAC
.venv\Scripts\activate     #FOR WINDOWS
uv add litellm
```

In a separate terminal run:
```bash
ollama pull phi4
ollama run phi4:latest
/bye
```
Check what models are currently running:
```bash
ollama ps
```


Run the backend  
```bash
source .venv/bin/activate  #FOR MAC
.venv\Scripts\activate     #FOR WINDOWS
cd src/codellamas_backend
uvicorn api:app 
```


Run the backend with uvicorn
```bash
cd src/codellamas_backend
uvicorn api:app
```


### Customizing

**Add your `MODEL` and `API_BASE` into the `.env` file**

- Modify `src/codellamas_backend/config/agents.yaml` to define your agents
- Modify `src/codellamas_backend/config/tasks.yaml` to define your tasks
- Modify `src/codellamas_backend/crew.py` to add your own logic, tools and specific args
- Modify `src/codellamas_backend/main.py` to add custom inputs for your agents and tasks

