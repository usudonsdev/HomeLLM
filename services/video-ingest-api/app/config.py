from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    media_root: str = "/media"
    namespace: str = "video-analysis"
    database_url: str = "postgresql+psycopg://homellm:local-demo-only-change-me@postgres:5432/homellm_video"
    segmenter_image: str = "homellm/valorant-segmenter:dev"
    analyzer_image: str = "homellm/valorant-analyzer:dev"
    internal_api_base_url: str = "http://video-ingest-api:8090"
    stub_segment_seconds: float = 2.0
    analyzer_poll_seconds: float = 5.0
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_timeout_seconds: float = 300.0
    ollama_keep_alive: str = "24h"
    tip_context_limit: int = 5


settings = Settings()
