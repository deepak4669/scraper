from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    base_path:str = "."
    retry_count:int = 3
    retry_delay:int = 3

settings = Settings()
