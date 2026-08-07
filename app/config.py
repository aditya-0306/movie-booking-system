from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_BOOTSTRAP_SECRET: str

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    MOVIE_CACHE_TTL_SECONDS: int = 300
    SHOW_CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"


settings = Settings()
