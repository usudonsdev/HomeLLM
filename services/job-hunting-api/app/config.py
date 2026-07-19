from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://homellm:changeme@localhost:5432/homellm"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:9b"
    # Notebook GPUs often need 1–3+ minutes for RAG prompts after cold load.
    ollama_timeout_seconds: float = 300.0
    # Keep model resident so smoke/RAG does not pay ~14s reload every time.
    ollama_keep_alive: str = "24h"
    rag_max_experiences: int = 5


settings = Settings()
