from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "2.1.35"
    max_posts_limit: int = 9999
    page_cache_ttl_seconds: int = 86400
    processed_post_cache_ttl_seconds: int = 86400
    admin_auth_secret: str = "change-me-dev-secret"
    admin_token_ttl_seconds: int = 28800
    admin_users_json: str = '{"admin":"pbkdf2_sha256$200000$2c4c14d9bfd648aa92da45063abe8e7d$fa642fc7877bbde4fea1fd6b6bf1bce10f954cad1e698f0314181d20d07e913a"}'
    redis_url: str = "redis://localhost:6379/0"
    generated_dir: str = "./generated"
    calibre_ebook_convert_path: str = "/usr/bin/ebook-convert"
    calibre_path: str = "/usr/bin/calibre"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    job_ttl_seconds: int = 86400  # 24h
    max_concurrent_jobs: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
