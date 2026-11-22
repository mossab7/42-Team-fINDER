from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "42 Team Finder"
    environment: str = "development"
    ft_client_id: str = ""
    ft_client_secret: str = ""
    ft_api_base_url: str = "https://api.intra.42.fr/v2"
    ft_token_url: str = "https://api.intra.42.fr/oauth/token"
    public_base_url: str = "http://localhost:3000"
    auth_required: bool = False
    session_ttl_hours: int = 24
    session_cookie_secure: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/team_finder.db"
    cache_ttl_seconds: int = 3600
    avatar_cache_directory: str = "./data/avatars"
    avatar_cache_ttl_seconds: int = 86400
    avatar_max_bytes: int = 5_000_000
    request_timeout_seconds: float = 20
    max_retries: int = 4
    api_concurrency: int = 4
    # 42 applies a burst/spam limit in addition to the hourly application
    # quota. Keep requests globally paced even when pagination is concurrent.
    api_min_interval_seconds: float = 0.6
    demo_mode: bool | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("demo_mode", mode="before")
    @classmethod
    def empty_demo_mode_is_automatic(cls, value):
        return None if value == "" else value

    @property
    def use_demo_data(self) -> bool:
        return self.demo_mode if self.demo_mode is not None else not (
            self.ft_client_id and self.ft_client_secret
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/api/auth/callback"

    def ensure_database_directory(self) -> None:
        prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(prefix):
            raw_path = self.database_url.removeprefix(prefix)
            if raw_path != ":memory:":
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
