from app.settings import settings

# LangChain Ollama chat model
from langchain_community.chat_models import ChatOllama

def build_crewai_llm():
    """
    Returns a LangChain-compatible chat model that CrewAI Agents can use.
    """
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.2,
    )
