from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    RUN_LOG_DIR: str = "./logs"
    MAX_CONTEXT_CHARS: int = 200_000

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "phi4"

    MVN_CMD: str = "mvn"
    MVN_TEST_TIMEOUT_SEC: int = 120

    MAX_DEBUG_RETRIES: int = 2

settings = Settings()
