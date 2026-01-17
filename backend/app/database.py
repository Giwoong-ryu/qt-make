"""
데이터베이스 연결 관리
"""
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings

settings = get_settings()

# Supabase 클라이언트 (싱글톤)
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Supabase 클라이언트 싱글톤"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _supabase_client
