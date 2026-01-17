"""
API 라우터 모듈
"""
from app.routers.stt import router as stt_router
from app.routers.dictionary import router as dictionary_router

__all__ = ["stt_router", "dictionary_router"]
