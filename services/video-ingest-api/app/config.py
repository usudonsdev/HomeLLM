from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    media_root: str = "/media"
    namespace: str = "video-analysis"
    segmenter_image: str = "homellm/valorant-segmenter:dev"
    stub_segment_seconds: float = 2.0


settings = Settings()
