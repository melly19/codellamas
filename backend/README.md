# CodellamasBackend Crew

Welcome to the CodellamasBackend Crew project, powered by [crewAI](https://crewai.com).

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) 



First, if you haven't already, install uv:
```bash
pip install uv
```

(Optional) Create a virtual environment:
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Next, navigate to your project directory and install the dependencies:
```bash
cd backend
crewai install
```

In a separate terminal run:
```bash
ollama pull phi4
ollama run phi4:latest
```
Check what models are currently running:
```bash
ollama ps
```
Run the backend  
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

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ uv add litellm
$ crewai run
```

This command initializes the codellamas_backend Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

## Understanding Your Crew

The codellamas_backend Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the CodellamasBackend Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
