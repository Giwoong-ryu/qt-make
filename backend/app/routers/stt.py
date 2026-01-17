"""
STT 교정 API
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.stt_correction import get_correction_service
from app.services.dictionary_service import get_dictionary_service
from app.routers.auth import get_current_user
from app.services.auth_service import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/videos", tags=["stt"])


# ===================
# Pydantic 모델
# ===================

class SubtitleItem(BaseModel):
    index: int
    start: float
    end: float
    text: str


class CorrectSubtitlesRequest(BaseModel):
    subtitles: list[SubtitleItem]
    quality_mode: bool = False  # True: Gemini 2.5 Pro, False: Gemini 2.5 Flash


class SingleCorrectionRequest(BaseModel):
    original_text: str
    corrected_text: str
    subtitle_index: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None


# ===================
# STT 교정 API
# ===================

@router.post("/{video_id}/correct-subtitles")
async def correct_subtitles(
    video_id: str,
    request: CorrectSubtitlesRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    자막 AI 교정

    Gemini 2.5 Flash를 사용해 전체 자막을 컨텍스트 기반으로 교정합니다.

    Args:
        video_id: 영상 UUID
        request: 자막 리스트 + 품질 모드

    Returns:
        corrected_subtitles: 교정된 자막 리스트
        corrections_count: 교정된 항목 수

    Header: Authorization: Bearer <token>
    """
    church_id = current_user.church_id
    if not church_id:
        raise HTTPException(status_code=400, detail="교회 배정이 필요합니다. /api/auth/set-church를 먼저 호출하세요.")

    # 사전 서비스에서 교회 사전 가져오기
    dict_service = get_dictionary_service()
    church_dict = await dict_service.get_dictionary(church_id, limit=100)

    # STT 설정 가져오기
    stt_settings = await dict_service.get_stt_settings(church_id)
    context_words = stt_settings.get("context_words", []) if stt_settings else []

    # 자막 포맷 변환
    subtitles = [s.model_dump() for s in request.subtitles]

    # AI 교정 실행
    correction_service = get_correction_service()
    corrected = await correction_service.correct_subtitles(
        subtitles=subtitles,
        church_dictionary=church_dict,
        context_words=context_words,
        quality_mode=request.quality_mode
    )

    # 교정된 항목 수 계산
    corrections_count = sum(
        1 for s in corrected
        if s.get("correction")
    )

    # 교정 이력 저장 (자동 학습용)
    if corrections_count > 0:
        corrections_to_save = [
            {
                "index": s.get("index"),
                "original": s["correction"]["original"],
                "corrected": s["correction"]["corrected"],
                "confidence": s["correction"].get("confidence"),
                "source": "ai",
                "start": s.get("start"),
                "end": s.get("end")
            }
            for s in corrected
            if s.get("correction")
        ]
        await dict_service.save_correction_history(
            video_id=video_id,
            church_id=church_id,
            corrections=corrections_to_save
        )

    return {
        "subtitles": corrected,
        "corrections_count": corrections_count,
        "quality_mode": request.quality_mode
    }


@router.post("/{video_id}/subtitles/{subtitle_index}/feedback")
async def submit_correction_feedback(
    video_id: str,
    subtitle_index: int,
    request: SingleCorrectionRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사용자 수정 피드백 제출

    사용자가 자막을 직접 수정한 경우 호출합니다.
    자동으로 교회 사전에 반영됩니다 (auto_learn 활성화 시).

    Args:
        video_id: 영상 UUID
        subtitle_index: 자막 인덱스
        request: 원본/수정 텍스트

    Returns:
        success: 성공 여부
        added_to_dictionary: 사전 추가 여부

    Header: Authorization: Bearer <token>
    """
    church_id = current_user.church_id
    if not church_id:
        raise HTTPException(status_code=400, detail="교회 배정이 필요합니다.")

    if request.original_text == request.corrected_text:
        return {"success": True, "added_to_dictionary": False}

    dict_service = get_dictionary_service()

    # 교정 이력 저장 (source: 'user' → 자동으로 사전 추가됨)
    saved_count = await dict_service.save_correction_history(
        video_id=video_id,
        church_id=church_id,
        corrections=[{
            "index": request.subtitle_index,
            "original": request.original_text,
            "corrected": request.corrected_text,
            "source": "user",
            "start": request.timestamp_start,
            "end": request.timestamp_end
        }]
    )

    return {
        "success": saved_count > 0,
        "added_to_dictionary": True  # trigger에서 자동 추가
    }


@router.post("/{video_id}/apply-dictionary")
async def apply_dictionary_to_subtitles(
    video_id: str,
    request: CorrectSubtitlesRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    사전 기반 자막 교정 (AI 없이)

    교회 사전에 등록된 패턴만 적용합니다.
    빠르고 비용이 없지만, 새로운 오류는 수정되지 않습니다.

    Args:
        video_id: 영상 UUID
        request: 자막 리스트

    Returns:
        subtitles: 교정된 자막 리스트
        applied_count: 적용된 교정 수

    Header: Authorization: Bearer <token>
    """
    church_id = current_user.church_id
    if not church_id:
        raise HTTPException(status_code=400, detail="교회 배정이 필요합니다.")

    dict_service = get_dictionary_service()
    correction_service = get_correction_service()

    # 교회 사전 가져오기
    church_dict = await dict_service.get_dictionary(church_id, limit=200)

    if not church_dict:
        return {
            "subtitles": [s.model_dump() for s in request.subtitles],
            "applied_count": 0
        }

    # 각 자막에 사전 적용
    result_subtitles = []
    total_applied = 0

    for subtitle in request.subtitles:
        corrected_text, applied = correction_service.apply_dictionary(
            text=subtitle.text,
            church_dictionary=church_dict
        )

        result = subtitle.model_dump()
        if corrected_text != subtitle.text:
            result["text"] = corrected_text
            result["correction"] = {
                "original": subtitle.text,
                "corrected": corrected_text,
                "source": "dictionary",
                "applied_rules": applied
            }
            total_applied += len(applied)

        result_subtitles.append(result)

    return {
        "subtitles": result_subtitles,
        "applied_count": total_applied
    }
