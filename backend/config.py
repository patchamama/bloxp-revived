from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    generated_dir: str = "./generated"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    job_ttl_seconds: int = 86400  # 24h

    class Config:
        env_file = ".env"


settings = Settings()
