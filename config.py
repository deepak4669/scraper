from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configures the settings."""

    base_path: str = "."
    retry_count: int = 3
    retry_delay: int = 3


settings = Settings()
