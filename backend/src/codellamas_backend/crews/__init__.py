from .single import SingleAgentRunner
from .multi import MultiAgentRunner

def get_generation_runner(mode: str):
    return MultiAgentRunner() if mode == "multi" else SingleAgentRunner()

def get_review_runner(mode: str):
    return MultiAgentRunner() if mode == "multi" else SingleAgentRunner()
