"""애플리케이션 설정 — 모든 민감정보는 환경변수에서 로딩."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 앱 기본
    app_name: str = "saju-app"
    app_env: str = "local"
    log_level: str = "DEBUG"

    # DB
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sajuapp"

    # 보안
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7일

    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # CORS
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """ALLOWED_ORIGINS 문자열을 리스트로 변환."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
