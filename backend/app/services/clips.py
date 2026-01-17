"""
배경 클립 선택 서비스

동적 클립 선택 시스템:
- 20초 이상 클립만 사용 (짧은 클립 제외)
- 실제 duration 기반으로 클립 선택 (고정 30초 X)
- 총 duration >= target_duration 될 때까지 선택
"""
import logging
import random

from app.config import get_settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ClipSelector:
    """배경 클립 선택 및 관리 서비스"""

    MIN_CLIP_DURATION = 20  # 최소 20초 이상 클립만 사용

    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )

    def select_clips(
        self,
        audio_duration: int,
        pack_id: str = "pack-free",
        exclude_recent: int = 5
    ) -> list[dict]:
        """
        오디오 길이에 맞는 배경 클립 선택 (동적 duration 기반)

        Args:
            audio_duration: 오디오 길이 (초)
            pack_id: 배경팩 ID (교회별 전용)
            exclude_recent: 최근 N개 클립 제외 (중복 방지)

        Returns:
            선택된 클립 리스트 (실제 duration 포함)
            [
                {
                    "id": "uuid",
                    "file_path": "https://r2.../clip1.mp4",
                    "category": "nature",
                    "duration": 45  # 실제 duration
                },
                ...
            ]
        """
        logger.info(
            f"Selecting clips for {audio_duration}s audio from pack: {pack_id} "
            f"(min duration: {self.MIN_CLIP_DURATION}s)"
        )

        try:
            # 1. 해당 팩의 클립 조회 (20초 이상, 사용 횟수 적은 순)
            response = self.supabase.table("clips") \
                .select("*") \
                .eq("pack_id", pack_id) \
                .eq("is_active", True) \
                .gte("duration", self.MIN_CLIP_DURATION) \
                .order("used_count", desc=False) \
                .execute()

            available_clips = response.data

            if not available_clips:
                # 20초 미만 클립만 있을 경우 모든 클립 사용 (폴백)
                logger.warning(f"No clips >= {self.MIN_CLIP_DURATION}s, using all clips")
                response = self.supabase.table("clips") \
                    .select("*") \
                    .eq("pack_id", pack_id) \
                    .eq("is_active", True) \
                    .order("used_count", desc=False) \
                    .execute()
                available_clips = response.data

            if not available_clips:
                raise ValueError(f"No clips available for pack: {pack_id}")

            # 2. 동적 선택: 총 duration >= target까지 클립 선택
            selected = self._select_by_duration(
                available_clips,
                audio_duration
            )

            # 3. 사용 횟수 업데이트
            self._update_used_count([c["id"] for c in selected])

            total_duration = sum(c.get("duration", 30) for c in selected)
            logger.info(
                f"Selected {len(selected)} clips, total duration: {total_duration}s "
                f"(target: {audio_duration}s)"
            )
            return selected

        except Exception as e:
            logger.exception(f"Failed to select clips: {e}")
            raise

    def _select_by_duration(
        self,
        clips: list[dict],
        target_duration: int
    ) -> list[dict]:
        """
        총 duration이 target_duration 이상이 될 때까지 클립 선택
        - 다양성 고려 (같은 카테고리 연속 최대 2개)
        - 사용 횟수 적은 클립 우선
        """
        if not clips:
            return []

        selected = []
        total_duration = 0
        last_category = None
        same_category_count = 0
        used_indices = set()

        # 1차: 다양성 고려하며 선택
        for idx, clip in enumerate(clips):
            if total_duration >= target_duration:
                break

            category = clip.get("category", "unknown")
            clip_duration = clip.get("duration", 30)

            # 연속 카테고리 체크
            if category == last_category:
                same_category_count += 1
                if same_category_count >= 2:
                    continue  # 스킵
            else:
                same_category_count = 1
                last_category = category

            selected.append(clip)
            total_duration += clip_duration
            used_indices.add(idx)

        # 2차: 부족하면 남은 클립에서 추가 (루프 허용)
        loop_count = 0
        max_loops = 5  # 무한 루프 방지

        while total_duration < target_duration and loop_count < max_loops:
            loop_count += 1
            added_in_loop = False

            for idx, clip in enumerate(clips):
                if total_duration >= target_duration:
                    break

                clip_duration = clip.get("duration", 30)
                selected.append(clip.copy())
                total_duration += clip_duration
                added_in_loop = True

            if not added_in_loop:
                break

        return selected

    def get_clips_by_ids(
        self,
        clip_ids: list[str],
        audio_duration: int
    ) -> list[dict]:
        """
        특정 클립 ID 리스트로 클립 조회 (템플릿 사용 시)

        Args:
            clip_ids: 선택된 클립 ID 리스트
            audio_duration: 오디오 길이 (초) - 클립 반복 계산용

        Returns:
            클립 리스트 (오디오 길이를 커버할 때까지 반복)
        """
        logger.info(f"Getting clips by IDs: {clip_ids}")

        try:
            # 클립 ID로 조회
            response = self.supabase.table("clips") \
                .select("*") \
                .in_("id", clip_ids) \
                .execute()

            clips_dict = {clip["id"]: clip for clip in response.data}

            # 선택 순서 유지하며 클립 리스트 생성
            ordered_clips = []
            for cid in clip_ids:
                if cid in clips_dict:
                    ordered_clips.append(clips_dict[cid])
                else:
                    logger.warning(f"Clip not found: {cid}")

            if not ordered_clips:
                logger.warning("No clips found, falling back to auto select")
                return self.select_clips(audio_duration, "pack-free")

            # 오디오 길이만큼 클립 반복
            result_clips = []
            total_duration = 0

            while total_duration < audio_duration:
                for clip in ordered_clips:
                    if total_duration >= audio_duration:
                        break
                    result_clips.append(clip.copy())
                    total_duration += clip.get("duration", 30)

            logger.info(
                f"Selected {len(result_clips)} clips from template "
                f"(total duration: {total_duration}s, audio: {audio_duration}s)"
            )
            return result_clips

        except Exception as e:
            logger.exception(f"Failed to get clips by IDs: {e}")
            # 실패 시 자동 선택으로 폴백
            return self.select_clips(audio_duration, "pack-free")

    def _select_with_variety(
        self,
        clips: list[dict],
        count: int
    ) -> list[dict]:
        """
        다양성을 고려한 클립 선택
        - 같은 카테고리 연속 최대 2개
        - 사용 횟수 적은 클립 우선
        """
        if not clips:
            return []

        selected = []
        last_category = None
        same_category_count = 0

        # 이미 사용 횟수 순 정렬됨
        for clip in clips:
            if len(selected) >= count:
                break

            category = clip.get("category", "unknown")

            # 연속 카테고리 체크
            if category == last_category:
                same_category_count += 1
                if same_category_count >= 2:
                    continue  # 스킵
            else:
                same_category_count = 1
                last_category = category

            selected.append(clip)

        # 부족하면 랜덤으로 채우기
        if len(selected) < count:
            remaining = [c for c in clips if c not in selected]
            random.shuffle(remaining)
            selected.extend(remaining[:count - len(selected)])

        return selected

    def _update_used_count(self, clip_ids: list[str]) -> None:
        """선택된 클립의 사용 횟수 증가"""
        try:
            for clip_id in clip_ids:
                self.supabase.rpc(
                    "increment_clip_used_count",
                    {"clip_id": clip_id}
                ).execute()
        except Exception as e:
            # 실패해도 영상 생성은 계속
            logger.warning(f"Failed to update used_count: {e}")

    def get_clip_paths(self, clips: list[dict]) -> list[str]:
        """클립 리스트에서 파일 경로만 추출"""
        return [clip["file_path"] for clip in clips]


# 싱글톤
_clip_selector: ClipSelector | None = None


def get_clip_selector() -> ClipSelector:
    """ClipSelector 싱글톤"""
    global _clip_selector
    if _clip_selector is None:
        _clip_selector = ClipSelector()
    return _clip_selector
