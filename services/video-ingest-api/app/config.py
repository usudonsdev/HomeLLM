from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    media_root: str = "/media"
    namespace: str = "video-analysis"
    database_url: str = "postgresql+psycopg://homellm:local-demo-only-change-me@postgres:5432/homellm_video"
    segmenter_image: str = "homellm/valorant-segmenter:dev"
    analyzer_image: str = "homellm/valorant-analyzer:dev"
    internal_api_base_url: str = "http://video-ingest-api:8090"
    # Fallback only when logo/transition detection finds no cuts.
    segment_fallback_seconds: float = 90.0
    stub_segment_seconds: float = 90.0  # alias kept for older env
    logo_template_dir: str = "/media/templates/valorant"
    sample_every_seconds: float = 0.5
    logo_match_threshold: float = 0.72
    min_round_gap_seconds: float = 12.0
    analyzer_poll_seconds: float = 5.0
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_timeout_seconds: float = 300.0
    ollama_keep_alive: str = "24h"
    tip_context_limit: int = 5
    # Primary path: browser on any Tailscale client → this API (not via Pi proxy).
    # 32 GiB covers typical ~1h 1080p game captures with headroom; override via UPLOAD_MAX_BYTES.
    upload_max_bytes: int = 34_359_738_368  # 32 GiB
    host_inbox_hint: str = r"Documents\HomeLLM\videos\inbox"


settings = Settings()
