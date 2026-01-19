"""
애플리케이션 설정 관리
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # App
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # PortOne (Payment)
    PORTONE_API_KEY: str | None = None
    PORTONE_API_SECRET: str | None = None

    # Groq API
    GROQ_API_KEY: str = ""

    # Google Gemini API (STT 교정용 + 감정 분석 + Vision 검증)
    GOOGLE_API_KEY: str = ""  # Gemini 2.5 Flash-Lite
    GEMINI_API_KEY: str = ""  # Alias for Google API Key

    def __init__(self, **data):
        super().__init__(**data)
        # GEMINI_API_KEY가 비어있으면 GOOGLE_API_KEY를 사용
        if not self.GEMINI_API_KEY and self.GOOGLE_API_KEY:
            self.GEMINI_API_KEY = self.GOOGLE_API_KEY

    # Pexels API (배경 영상 검색)
    PEXELS_API_KEY: str = ""  # Free tier: 200 requests/hour

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "qt-videos"
    R2_PUBLIC_URL: str = ""  # R2 Public bucket URL 또는 Custom Domain (예: https://pub-xxx.r2.dev)

    @property
    def R2_ENDPOINT_URL(self) -> str:
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 (캐싱)"""
    return Settings()
