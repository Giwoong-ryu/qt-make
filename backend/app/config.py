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

    # CORS (프로덕션용)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,https://www.qt-make.com,https://qt-make.com"  # 쉼표로 구분
    ALLOWED_HOSTS: str = "*"  # 프로덕션에서는 실제 도메인으로 제한
    
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

        # 프로덕션 환경에서 필수 환경변수 검증
        if self.ENV == "production":
            self._validate_production_env()

    def _validate_production_env(self):
        """프로덕션 필수 환경변수 검증"""
        required_vars = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_KEY": self.SUPABASE_KEY,
            "GROQ_API_KEY": self.GROQ_API_KEY,
            "GOOGLE_API_KEY": self.GOOGLE_API_KEY,
            "PORTONE_API_KEY": self.PORTONE_API_KEY,
            "PORTONE_API_SECRET": self.PORTONE_API_SECRET,
            "R2_ACCOUNT_ID": self.R2_ACCOUNT_ID,
            "R2_ACCESS_KEY_ID": self.R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": self.R2_SECRET_ACCESS_KEY,
        }

        missing = [key for key, value in required_vars.items() if not value]

        if missing:
            raise ValueError(
                f"❌ Missing required environment variables for production: {', '.join(missing)}\n"
                f"Please check your .env.production file."
            )

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

    # Redis (Railway/Upstash 호환)
    # REDIS_URL이 환경변수로 주어지면 그걸 사용, 없으면 HOST/PORT 조합
    REDIS_URL: str = ""  # Railway는 이 값을 통째로 제공함
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def get_redis_url(self) -> str:
        """Railway/Upstash는 REDIS_URL을 직접 제공, 로컬은 조합"""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 (캐싱)"""
    return Settings()
