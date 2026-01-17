"""
교회 사전 관리 API
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.dictionary_service import get_dictionary_service
from app.routers.auth import get_current_user
from app.services.auth_service import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/churches", tags=["dictionary"])


# ===================
# Pydantic 모델
# ===================

class DictionaryEntry(BaseModel):
    wrong_text: str
    correct_text: str
    category: str = "general"


class DictionaryEntryUpdate(BaseModel):
    correct_text: str | None = None
    category: str | None = None
    is_active: bool | None = None


class BulkImportRequest(BaseModel):
    entries: list[DictionaryEntry]


class STTSettingsUpdate(BaseModel):
    whisper_prompt: str | None = None
    whisper_language: str | None = None
    correction_enabled: bool | None = None
    quality_mode: bool | None = None
    auto_learn: bool | None = None
    min_confidence: float | None = None
    context_words: list[str] | None = None


# ===================
# 사전 API
# ===================

def _verify_church_access(current_user: UserProfile, church_id: str):
    """사용자가 해당 교회에 접근 권한이 있는지 확인"""
    if not current_user.church_id:
        raise HTTPException(status_code=400, detail="교회 배정이 필요합니다.")
    if current_user.church_id != church_id:
        raise HTTPException(status_code=403, detail="해당 교회에 접근 권한이 없습니다.")


@router.get("/{church_id}/dictionary")
async def get_dictionary(
    church_id: str,
    category: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    교회 사전 조회

    Args:
        church_id: 교회 UUID
        category: 분류 필터 (person, place, bible, hymn, general)
        limit: 페이지 크기 (최대 500)
        offset: 시작 위치

    Returns:
        entries: 사전 항목 리스트

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    entries = await service.get_dictionary(
        church_id=church_id,
        category=category,
        limit=limit,
        offset=offset
    )

    return {
        "entries": entries,
        "count": len(entries),
        "offset": offset,
        "limit": limit
    }


@router.post("/{church_id}/dictionary")
async def add_dictionary_entry(
    church_id: str,
    entry: DictionaryEntry,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 항목 추가

    Args:
        church_id: 교회 UUID
        entry: 추가할 항목 (wrong_text, correct_text, category)

    Returns:
        생성/업데이트된 항목

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    result = await service.add_entry(
        church_id=church_id,
        wrong_text=entry.wrong_text,
        correct_text=entry.correct_text,
        category=entry.category
    )

    if not result:
        raise HTTPException(status_code=500, detail="사전 항목 추가에 실패했습니다.")

    return result


@router.put("/{church_id}/dictionary/{entry_id}")
async def update_dictionary_entry(
    church_id: str,
    entry_id: str,
    update: DictionaryEntryUpdate,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 항목 수정

    Args:
        church_id: 교회 UUID
        entry_id: 항목 ID
        update: 수정할 필드

    Returns:
        업데이트된 항목

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    result = await service.update_entry(
        entry_id=entry_id,
        correct_text=update.correct_text,
        category=update.category,
        is_active=update.is_active
    )

    if not result:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")

    return result


@router.delete("/{church_id}/dictionary/{entry_id}")
async def delete_dictionary_entry(
    church_id: str,
    entry_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 항목 삭제 (소프트 삭제)

    Args:
        church_id: 교회 UUID
        entry_id: 항목 ID

    Returns:
        삭제 결과

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    success = await service.delete_entry(entry_id)

    if not success:
        raise HTTPException(status_code=500, detail="삭제에 실패했습니다.")

    return {"success": True, "entry_id": entry_id}


@router.post("/{church_id}/dictionary/import")
async def bulk_import_dictionary(
    church_id: str,
    request: BulkImportRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 일괄 등록

    Args:
        church_id: 교회 UUID
        request: 등록할 항목 리스트

    Returns:
        등록된 항목 수

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    count = await service.bulk_import(
        church_id=church_id,
        entries=[e.model_dump() for e in request.entries]
    )

    return {
        "success": True,
        "imported_count": count,
        "total_submitted": len(request.entries)
    }


# ===================
# STT 설정 API
# ===================

@router.get("/{church_id}/stt-settings")
async def get_stt_settings(
    church_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    교회별 STT 설정 조회

    Args:
        church_id: 교회 UUID

    Returns:
        STT 설정 (없으면 기본값)

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    settings = await service.get_stt_settings(church_id)

    if settings:
        return settings

    # 기본값 반환
    return {
        "church_id": church_id,
        "whisper_prompt": None,
        "whisper_language": "ko",
        "correction_enabled": True,
        "quality_mode": False,
        "auto_learn": True,
        "min_confidence": 0.7,
        "context_words": []
    }


@router.put("/{church_id}/stt-settings")
async def update_stt_settings(
    church_id: str,
    settings: STTSettingsUpdate,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    교회별 STT 설정 업데이트

    Args:
        church_id: 교회 UUID
        settings: 업데이트할 설정

    Returns:
        업데이트된 설정

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()

    # None이 아닌 필드만 추출
    update_data = {k: v for k, v in settings.model_dump().items() if v is not None}

    result = await service.update_stt_settings(church_id, update_data)

    if not result:
        raise HTTPException(status_code=500, detail="설정 업데이트에 실패했습니다.")

    return result


@router.post("/{church_id}/stt-settings/generate-prompt")
async def generate_whisper_prompt(
    church_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 기반 Whisper prompt 자동 생성

    교회 사전에서 자주 사용되는 단어를 기반으로
    Whisper initial_prompt를 생성합니다.

    Args:
        church_id: 교회 UUID

    Returns:
        생성된 prompt

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    prompt = await service.generate_whisper_prompt(church_id)

    # 설정에 자동 저장
    await service.update_stt_settings(church_id, {"whisper_prompt": prompt})

    return {
        "whisper_prompt": prompt,
        "token_estimate": len(prompt) * 2  # 대략적 추정
    }


# ===================
# 교정 이력 API
# ===================

@router.get("/{church_id}/correction-history")
async def get_correction_history(
    church_id: str,
    video_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    교정 이력 조회

    Args:
        church_id: 교회 UUID
        video_id: 특정 영상만 조회 (옵션)
        limit: 최대 개수

    Returns:
        교정 이력 리스트

    Header: Authorization: Bearer <token>
    """
    _verify_church_access(current_user, church_id)

    service = get_dictionary_service()
    history = await service.get_correction_history(
        video_id=video_id,
        church_id=church_id,
        limit=limit
    )

    return {"history": history, "count": len(history)}
