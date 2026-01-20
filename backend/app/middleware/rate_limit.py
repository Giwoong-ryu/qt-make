"""
Rate Limiting 미들웨어
slowapi 기반 API 호출 제한
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limiter() -> Limiter:
    """Rate limiter 인스턴스 생성"""
    return Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],  # 기본 제한: 분당 100회
        storage_uri="memory://",  # 메모리 저장 (프로덕션에서는 Redis 사용 권장)
    )
