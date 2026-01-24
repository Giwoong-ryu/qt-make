"""
Celery 인스턴스 설정
"""
import logging
from datetime import datetime, timezone, timedelta
from celery import Celery

from app.config import get_settings

settings = get_settings()

# 한국시간 로깅 Formatter
class KSTFormatter(logging.Formatter):
    """한국시간(KST)으로 로그 출력하는 Formatter"""
    def formatTime(self, record, datefmt=None):
        kst = timezone(timedelta(hours=9))
        ct = datetime.fromtimestamp(record.created, tz=kst)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.strftime("%Y-%m-%d %H:%M:%S")

# 로깅 설정 (KST 적용)
handler = logging.StreamHandler()
handler.setFormatter(KSTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])

# Celery 앱 생성
redis_url = settings.get_redis_url()
celery_app = Celery(
    "qt_video",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분 타임아웃
    worker_prefetch_multiplier=1,  # 한 번에 1개 작업만
)
