"""
Celery 인스턴스 설정
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

# Celery 앱 생성
redis_url = settings.get_redis_url
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
