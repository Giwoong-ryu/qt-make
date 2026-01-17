"""
교회별 사전 관리 서비스
"""
import logging
from typing import Any
from uuid import UUID

from supabase import Client

from app.database import get_supabase

logger = logging.getLogger(__name__)


class DictionaryService:
    """교회별 STT 사전 관리"""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ===================
    # 사전 CRUD
    # ===================

    async def get_dictionary(
        self,
        church_id: str,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        교회 사전 조회

        Args:
            church_id: 교회 ID
            category: 분류 필터 (person, place, bible, hymn, general)
            limit: 페이지 크기
            offset: 시작 위치

        Returns:
            사전 항목 리스트
        """
        try:
            query = self.supabase.table("church_dictionary") \
                .select("*") \
                .eq("church_id", church_id) \
                .eq("is_active", True) \
                .order("frequency", desc=True) \
                .range(offset, offset + limit - 1)

            if category:
                query = query.eq("category", category)

            result = query.execute()
            return result.data

        except Exception as e:
            logger.exception(f"Failed to get dictionary: {e}")
            return []

    async def add_entry(
        self,
        church_id: str,
        wrong_text: str,
        correct_text: str,
        category: str = "general"
    ) -> dict | None:
        """
        사전 항목 추가

        Args:
            church_id: 교회 ID
            wrong_text: 잘못 인식되는 텍스트
            correct_text: 올바른 텍스트
            category: 분류

        Returns:
            생성된 항목 또는 None
        """
        try:
            result = self.supabase.table("church_dictionary").upsert({
                "church_id": church_id,
                "wrong_text": wrong_text,
                "correct_text": correct_text,
                "category": category,
                "frequency": 1
            }, on_conflict="church_id,wrong_text").execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.exception(f"Failed to add dictionary entry: {e}")
            return None

    async def update_entry(
        self,
        entry_id: str,
        correct_text: str | None = None,
        category: str | None = None,
        is_active: bool | None = None
    ) -> dict | None:
        """사전 항목 수정"""
        try:
            update_data = {}
            if correct_text is not None:
                update_data["correct_text"] = correct_text
            if category is not None:
                update_data["category"] = category
            if is_active is not None:
                update_data["is_active"] = is_active

            if not update_data:
                return None

            result = self.supabase.table("church_dictionary") \
                .update(update_data) \
                .eq("id", entry_id) \
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.exception(f"Failed to update dictionary entry: {e}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """사전 항목 삭제 (소프트 삭제)"""
        try:
            self.supabase.table("church_dictionary") \
                .update({"is_active": False}) \
                .eq("id", entry_id) \
                .execute()
            return True

        except Exception as e:
            logger.exception(f"Failed to delete dictionary entry: {e}")
            return False

    async def increment_frequency(self, entry_id: str) -> None:
        """사전 항목 빈도 증가"""
        try:
            self.supabase.rpc("increment_dictionary_frequency", {
                "dict_id": entry_id
            }).execute()

        except Exception as e:
            logger.exception(f"Failed to increment frequency: {e}")

    async def bulk_import(
        self,
        church_id: str,
        entries: list[dict]
    ) -> int:
        """
        사전 일괄 등록

        Args:
            church_id: 교회 ID
            entries: [{"wrong_text": "...", "correct_text": "...", "category": "..."}]

        Returns:
            등록된 항목 수
        """
        try:
            import_data = []
            for entry in entries:
                if entry.get("wrong_text") and entry.get("correct_text"):
                    import_data.append({
                        "church_id": church_id,
                        "wrong_text": entry["wrong_text"],
                        "correct_text": entry["correct_text"],
                        "category": entry.get("category", "general"),
                        "frequency": 1
                    })

            if not import_data:
                return 0

            result = self.supabase.table("church_dictionary") \
                .upsert(import_data, on_conflict="church_id,wrong_text") \
                .execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            logger.exception(f"Failed to bulk import: {e}")
            return 0

    # ===================
    # STT 설정
    # ===================

    async def get_stt_settings(self, church_id: str) -> dict | None:
        """교회별 STT 설정 조회"""
        try:
            result = self.supabase.table("church_stt_settings") \
                .select("*") \
                .eq("church_id", church_id) \
                .single() \
                .execute()

            return result.data

        except Exception as e:
            # 설정이 없으면 기본값 반환
            logger.info(f"No STT settings for church {church_id}, using defaults")
            return None

    async def update_stt_settings(
        self,
        church_id: str,
        settings: dict
    ) -> dict | None:
        """교회별 STT 설정 업데이트"""
        try:
            # upsert로 없으면 생성, 있으면 업데이트
            data = {"church_id": church_id, **settings}

            result = self.supabase.table("church_stt_settings") \
                .upsert(data, on_conflict="church_id") \
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.exception(f"Failed to update STT settings: {e}")
            return None

    async def generate_whisper_prompt(
        self,
        church_id: str,
        max_tokens: int = 200
    ) -> str:
        """
        교회 사전에서 자주 사용되는 단어로 Whisper prompt 생성

        Args:
            church_id: 교회 ID
            max_tokens: 최대 토큰 수 (Whisper는 224 제한)

        Returns:
            comma-separated 단어 목록
        """
        try:
            # 자주 사용되는 correct_text 가져오기
            result = self.supabase.rpc("get_top_dictionary_terms", {
                "p_church_id": church_id,
                "p_limit": 50
            }).execute()

            if not result.data:
                # 기본 교회 용어
                return "묵상, 말씀, 은혜, 성경, 하나님, 예수님, 성령, 기도, 찬양, 예배"

            # 단어 추출 (중복 제거)
            words = list(set([r["correct_text"] for r in result.data]))

            # 토큰 수 제한 (대략 한글 1자 = 2토큰)
            prompt_words = []
            current_length = 0

            for word in words:
                word_tokens = len(word) * 2  # 대략적 토큰 추정
                if current_length + word_tokens > max_tokens:
                    break
                prompt_words.append(word)
                current_length += word_tokens + 2  # +2 for ", "

            return ", ".join(prompt_words)

        except Exception as e:
            logger.exception(f"Failed to generate whisper prompt: {e}")
            return "묵상, 말씀, 은혜, 성경, 하나님, 예수님, 성령"

    # ===================
    # 교정 이력
    # ===================

    async def save_correction_history(
        self,
        video_id: str,
        church_id: str,
        corrections: list[dict]
    ) -> int:
        """
        교정 이력 저장

        Args:
            video_id: 영상 ID
            church_id: 교회 ID
            corrections: [{"original": "...", "corrected": "...", "source": "ai", ...}]

        Returns:
            저장된 이력 수
        """
        try:
            history_data = []
            for c in corrections:
                if c.get("original") != c.get("corrected"):
                    history_data.append({
                        "video_id": video_id,
                        "church_id": church_id,
                        "original_text": c.get("original", ""),
                        "corrected_text": c.get("corrected", ""),
                        "correction_source": c.get("source", "ai"),
                        "subtitle_index": c.get("index"),
                        "timestamp_start": c.get("start"),
                        "timestamp_end": c.get("end"),
                        "confidence": c.get("confidence")
                    })

            if not history_data:
                return 0

            result = self.supabase.table("correction_history") \
                .insert(history_data) \
                .execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            logger.exception(f"Failed to save correction history: {e}")
            return 0

    async def get_correction_history(
        self,
        video_id: str | None = None,
        church_id: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """교정 이력 조회"""
        try:
            query = self.supabase.table("correction_history") \
                .select("*") \
                .order("created_at", desc=True) \
                .limit(limit)

            if video_id:
                query = query.eq("video_id", video_id)
            if church_id:
                query = query.eq("church_id", church_id)

            result = query.execute()
            return result.data

        except Exception as e:
            logger.exception(f"Failed to get correction history: {e}")
            return []


# 팩토리 함수
def get_dictionary_service() -> DictionaryService:
    """DictionaryService 인스턴스 생성"""
    supabase = get_supabase()
    return DictionaryService(supabase)
