"""
자동 치환 사전 API (프론트엔드 호환용)

프론트엔드에서 사용하는 엔드포인트:
- GET /api/dictionary/{church_id} - 목록 조회
- POST /api/dictionary/{church_id} - 단일 추가
- POST /api/dictionary/{church_id}/batch - 일괄 추가
- DELETE /api/dictionary/{church_id}/{entry_id} - 단일 삭제
- DELETE /api/dictionary/{church_id} - 전체 삭제
"""
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_supabase
from app.routers.auth import get_current_user
from app.services.auth_service import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dictionary", tags=["replacement-dictionary"])


# ===================
# Pydantic 모델
# ===================

class ReplacementEntryCreate(BaseModel):
    """단일 항목 추가"""
    original: str
    replacement: str


class ReplacementBatchRequest(BaseModel):
    """일괄 추가 요청"""
    entries: list[ReplacementEntryCreate]


# ===================
# 헬퍼 함수
# ===================

def _verify_church_access(current_user: UserProfile, church_id: str):
    """사용자가 해당 교회에 접근 권한이 있는지 확인"""
    # demo-church는 church_id 없어도 허용
    if church_id == "demo-church":
        return
    
    if not current_user.church_id:
        raise HTTPException(status_code=400, detail="교회 배정이 필요합니다.")
    if current_user.church_id != church_id:
        raise HTTPException(status_code=403, detail="해당 교회에 접근 권한이 없습니다.")


# ===================
# API 엔드포인트
# ===================

@router.get("/{church_id}")
async def get_replacement_dictionary(
    church_id: str,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    치환 사전 목록 조회

    Returns:
        entries: 치환 항목 리스트
        - id, church_id, original, replacement, use_count, created_at, updated_at
    """
    _verify_church_access(current_user, church_id)

    supabase = get_supabase()

    try:
        result = supabase.table("replacement_dictionary") \
            .select("*") \
            .eq("church_id", church_id) \
            .order("use_count", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return {
            "entries": result.data or [],
            "count": len(result.data) if result.data else 0,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.exception(f"Failed to get replacement dictionary: {e}")
        raise HTTPException(status_code=500, detail="사전 조회에 실패했습니다.")


@router.post("/{church_id}")
async def add_replacement_entry(
    church_id: str,
    entry: ReplacementEntryCreate,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    치환 사전에 단일 항목 추가

    동일한 original이 이미 존재하면 replacement와 use_count를 업데이트합니다.
    """
    _verify_church_access(current_user, church_id)

    if not entry.original.strip() or not entry.replacement.strip():
        raise HTTPException(status_code=400, detail="원본과 치환 텍스트가 필요합니다.")

    supabase = get_supabase()

    try:
        # upsert: church_id + original 조합이 unique
        result = supabase.table("replacement_dictionary").upsert({
            "church_id": church_id,
            "original": entry.original.strip(),
            "replacement": entry.replacement.strip(),
            "use_count": 1
        }, on_conflict="church_id,original").execute()

        return result.data[0] if result.data else None

    except Exception as e:
        logger.exception(f"Failed to add replacement entry: {e}")
        raise HTTPException(status_code=500, detail="항목 추가에 실패했습니다.")


@router.post("/{church_id}/batch")
async def add_replacement_entries_batch(
    church_id: str,
    request: ReplacementBatchRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    치환 사전에 여러 항목 일괄 추가

    자막 수정 시 감지된 변경사항을 한 번에 저장합니다.
    동일한 original이 이미 존재하면 use_count를 증가시킵니다.

    Returns:
        added: 새로 추가된 항목 수
        updated: 업데이트된 항목 수
    """
    _verify_church_access(current_user, church_id)

    if not request.entries:
        return {"added": 0, "updated": 0}

    supabase = get_supabase()

    added = 0
    updated = 0

    try:
        for entry in request.entries:
            if not entry.original.strip() or not entry.replacement.strip():
                continue

            original = entry.original.strip()
            replacement = entry.replacement.strip()

            # 동일한 original + replacement 조합인지 확인 (무의미한 저장 방지)
            if original == replacement:
                continue

            # 기존 항목 확인
            existing = supabase.table("replacement_dictionary") \
                .select("id, use_count") \
                .eq("church_id", church_id) \
                .eq("original", original) \
                .execute()

            if existing.data:
                # 기존 항목 업데이트: replacement 변경 + use_count 증가
                supabase.table("replacement_dictionary") \
                    .update({
                        "replacement": replacement,
                        "use_count": existing.data[0]["use_count"] + 1,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
                updated += 1
            else:
                # 새 항목 추가
                supabase.table("replacement_dictionary").insert({
                    "church_id": church_id,
                    "original": original,
                    "replacement": replacement,
                    "use_count": 1
                }).execute()
                added += 1

        return {"added": added, "updated": updated}

    except Exception as e:
        logger.exception(f"Failed to batch add replacement entries: {e}")
        raise HTTPException(status_code=500, detail="일괄 추가에 실패했습니다.")


@router.delete("/{church_id}/{entry_id}")
async def delete_replacement_entry(
    church_id: str,
    entry_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    치환 사전 항목 삭제
    """
    _verify_church_access(current_user, church_id)

    supabase = get_supabase()

    try:
        # 권한 확인: 해당 교회의 항목인지 확인
        entry = supabase.table("replacement_dictionary") \
            .select("id, church_id") \
            .eq("id", entry_id) \
            .execute()

        if not entry.data:
            raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")

        if entry.data[0]["church_id"] != church_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        # 삭제
        supabase.table("replacement_dictionary") \
            .delete() \
            .eq("id", entry_id) \
            .execute()

        return {"success": True, "entry_id": entry_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete replacement entry: {e}")
        raise HTTPException(status_code=500, detail="삭제에 실패했습니다.")


@router.delete("/{church_id}")
async def clear_replacement_dictionary(
    church_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    치환 사전 전체 삭제
    """
    _verify_church_access(current_user, church_id)

    supabase = get_supabase()

    try:
        # 해당 교회의 모든 항목 삭제
        supabase.table("replacement_dictionary") \
            .delete() \
            .eq("church_id", church_id) \
            .execute()

        return {"success": True, "church_id": church_id}

    except Exception as e:
        logger.exception(f"Failed to clear replacement dictionary: {e}")
        raise HTTPException(status_code=500, detail="전체 삭제에 실패했습니다.")
