from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://orbital:orbital_dev@localhost:5432/orbitalwatch"
    redis_url: str = "redis://localhost:6379/0"
    spacetrack_username: str = ""
    spacetrack_password: str = ""
    celestrak_base_url: str = "https://celestrak.org"
    cors_origins: str = "http://localhost:3000"
    app_env: str = "development"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def async_database_url(self) -> str:
        """Convert any postgres:// URL to use asyncpg driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
