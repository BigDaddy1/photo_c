from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://photocolor:photocolor@localhost:5432/photocolor"
    storage_path: Path = Path("./data/images")
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
