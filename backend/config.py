from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "2.0.9"
    max_posts_limit: int = 9999
    page_cache_ttl_seconds: int = 86400
    redis_url: str = "redis://localhost:6379/0"
    generated_dir: str = "./generated"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    job_ttl_seconds: int = 86400  # 24h
    max_concurrent_jobs: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
