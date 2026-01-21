"""
전역 클립 중복 방지 서비스
최근 10개 영상에서 사용된 클립 ID를 추적하여 중복 사용 방지
"""
import logging
from typing import Set, List
from app.database import get_supabase

logger = logging.getLogger(__name__)


class ClipHistoryService:
    """
    전역 클립 사용 이력 관리
    """

    def get_recently_used_clips(self, church_id: str, limit: int = 10) -> Set[int]:
        """
        최근 N개 영상에서 사용된 클립 ID 가져오기

        Args:
            church_id: 교회 ID
            limit: 최근 영상 개수 (기본 10개)

        Returns:
            최근 사용된 clip_id (Pexels video ID) Set
        """
        try:
            sb = get_supabase()

            # 1. 최근 N개 영상 ID 가져오기
            recent_videos = (
                sb.table("videos")
                .select("id")
                .eq("church_id", church_id)
                .eq("status", "completed")  # 완료된 영상만
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            if not recent_videos.data:
                logger.info(f"[ClipHistory] No recent videos for church {church_id[:8]}")
                return set()

            video_ids = [v["id"] for v in recent_videos.data]

            # 2. 해당 영상들에서 사용된 클립 ID 조회
            used_clips = (
                sb.table("used_clips")
                .select("clip_id")
                .in_("video_id", video_ids)
                .execute()
            )

            clip_ids = {clip["clip_id"] for clip in used_clips.data}

            logger.info(
                f"[ClipHistory] Found {len(clip_ids)} unique clips "
                f"from {len(video_ids)} recent videos (church: {church_id[:8]})"
            )

            return clip_ids

        except Exception as e:
            logger.exception(f"[ClipHistory] Failed to fetch recent clips: {e}")
            return set()  # 실패 시 빈 set 반환 (중복 방지 실패하더라도 영상 생성은 계속)

    def record_used_clips(
        self,
        church_id: str,
        video_id: str,
        clip_ids_with_urls: List[tuple]
    ) -> None:
        """
        영상 생성 후 사용된 클립 ID 기록

        Args:
            church_id: 교회 ID
            video_id: 영상 ID
            clip_ids_with_urls: [(clip_id, clip_url), ...] 리스트
        """
        try:
            sb = get_supabase()

            # used_clips 테이블에 bulk insert
            records = [
                {
                    "church_id": church_id,
                    "video_id": video_id,
                    "clip_id": clip_id,
                    "clip_url": clip_url,
                }
                for clip_id, clip_url in clip_ids_with_urls
            ]

            if records:
                sb.table("used_clips").insert(records).execute()
                logger.info(
                    f"[ClipHistory] Recorded {len(records)} clips for video {video_id[:8]}"
                )

        except Exception as e:
            # 기록 실패는 critical하지 않음 (다음 영상부터는 정상 작동)
            logger.exception(f"[ClipHistory] Failed to record used clips: {e}")

    def cleanup_old_records(self, church_id: str, keep_recent: int = 20) -> None:
        """
        오래된 클립 기록 정리 (선택적)

        Args:
            church_id: 교회 ID
            keep_recent: 유지할 최근 영상 개수 (기본 20개)
        """
        try:
            sb = get_supabase()

            # 최근 N개 영상 ID 가져오기
            recent_videos = (
                sb.table("videos")
                .select("id")
                .eq("church_id", church_id)
                .order("created_at", desc=True)
                .limit(keep_recent)
                .execute()
            )

            if not recent_videos.data:
                return

            recent_video_ids = [v["id"] for v in recent_videos.data]

            # 해당 영상이 아닌 클립 기록 삭제
            sb.table("used_clips").delete().eq("church_id", church_id).not_.in_(
                "video_id", recent_video_ids
            ).execute()

            logger.info(f"[ClipHistory] Cleaned up old clip records (church: {church_id[:8]})")

        except Exception as e:
            logger.exception(f"[ClipHistory] Cleanup failed: {e}")


def get_clip_history_service() -> ClipHistoryService:
    """ClipHistoryService 싱글톤"""
    return ClipHistoryService()
