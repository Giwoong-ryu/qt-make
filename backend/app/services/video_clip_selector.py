"""
영상 클립 선택기 (Video Clip Selector)

섹션별 최적 영상 선택:
- 도입: 25초+ 영상 → 성경 구절 끝나는 지점까지 trim (정확)
- 중간: 짧은 영상 → 반복 재생으로 구간 채움 (대략적)
- 마무리: 20-30초 영상 → trim 안 함 (자연스럽게 종료)
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.services.background_video_search import (
    PexelsVideoSearch,
    PexelsVideo
)
from app.services.fixed_segment_analyzer import SegmentStrategy

logger = logging.getLogger(__name__)


@dataclass
class SelectedClip:
    """선택된 영상 클립 정보"""
    video: PexelsVideo          # Pexels 영상 정보 (단일 영상)
    segment: SegmentStrategy    # 구간 정보
    trim_duration: Optional[float]  # trim할 길이 (None이면 전체 재생)
    additional_videos: List[PexelsVideo] = None  # 추가 영상 (human 2개 조합 시)

    def __post_init__(self):
        if self.additional_videos is None:
            self.additional_videos = []

    @property
    def needs_trim(self) -> bool:
        """trim 필요 여부"""
        return self.trim_duration is not None

    @property
    def is_multi_video(self) -> bool:
        """여러 영상 조합 여부"""
        return len(self.additional_videos) > 0

    @property
    def all_videos(self) -> List[PexelsVideo]:
        """모든 영상 리스트 (메인 + 추가)"""
        return [self.video] + self.additional_videos


class VideoClipSelector:
    """
    영상 클립 선택기

    전략:
    - 도입: 25초+ 영상 선택 → 성경 구절 끝나는 지점까지 trim (정확)
    - 중간: 10-20초 영상 선택 → 반복 재생으로 구간 채움 (대략적)
    - 마무리: 20-30초 영상 선택 → trim 안 함 (자연스럽게 종료)
    """

    # 도입 구간 최소 영상 길이 (초)
    INTRO_MIN_DURATION = 25.0

    # 마무리 구간 영상 길이 범위 (초) - trim 안 함
    CLOSING_MIN_DURATION = 20.0
    CLOSING_MAX_DURATION = 30.0

    # 중간 구간 영상 선호도 (초)
    MIDDLE_IDEAL_MIN = 30.0   # 이상적: 30~40초 (1번 재생)
    MIDDLE_IDEAL_MAX = 40.0
    MIDDLE_FALLBACK_MIN = 15.0  # 대안: 15~20초 (2번 반복)
    MIDDLE_FALLBACK_MAX = 20.0

    def __init__(self):
        self.video_search = PexelsVideoSearch()

    def select_clips(
        self,
        segments: List[SegmentStrategy]
    ) -> List[SelectedClip]:
        """
        모든 구간에 대해 영상 선택

        Args:
            segments: 구간 전략 리스트 (fixed_segment_analyzer 출력)

        Returns:
            선택된 클립 리스트
        """
        selected_clips = []

        for segment in segments:
            clip = self._select_clip_for_segment(segment)

            if clip:
                selected_clips.append(clip)
                if clip.is_multi_video:
                    total_duration = sum(v.duration for v in clip.all_videos)
                    logger.info(
                        f"Selected {len(clip.all_videos)} clips for {segment.segment_type} "
                        f"({segment.start_time:.1f}-{segment.end_time:.1f}s): "
                        f"total={total_duration:.1f}s"
                    )
                else:
                    logger.info(
                        f"Selected clip for {segment.segment_type} "
                        f"({segment.start_time:.1f}-{segment.end_time:.1f}s): "
                        f"video={clip.video.duration:.1f}s, "
                        f"trim={clip.trim_duration if clip.needs_trim else 'none'}"
                    )
            else:
                logger.error(
                    f"Failed to select clip for {segment.segment_type} "
                    f"({segment.start_time:.1f}-{segment.end_time:.1f}s)"
                )

        return selected_clips

    def _select_clip_for_segment(
        self,
        segment: SegmentStrategy
    ) -> Optional[SelectedClip]:
        """
        단일 구간에 대해 영상 선택

        Args:
            segment: 구간 전략

        Returns:
            선택된 클립 (실패 시 None)
        """
        segment_duration = segment.end_time - segment.start_time

        # 마무리 구간: 20-30초 영상, trim 안 함
        if segment.segment_type == "fixed_closing":
            return self._select_closing_clip(segment, segment_duration)

        # 도입 구간: 25초+ 영상, 성경 구절 끝나는 지점까지 trim
        if segment.segment_type == "fixed_intro":
            return self._select_intro_clip(segment, segment_duration)

        # 중간 구간: 10-20초 영상, 반복 재생으로 구간 채움
        return self._select_middle_clip(segment, segment_duration)

    def _select_intro_clip(
        self,
        segment: SegmentStrategy,
        segment_duration: float
    ) -> Optional[SelectedClip]:
        """
        도입 구간 영상 선택 (25초+, 성경 구절 끝나는 지점까지 trim)

        Args:
            segment: 구간 전략
            segment_duration: 구간 길이 (초) - 성경 구절이 끝나는 동적 지점

        Returns:
            선택된 클립
        """
        # Pexels 검색 (전략 기반)
        verified_videos = self.video_search.search_by_mood(
            mood=None,
            duration_needed=int(segment_duration),
            max_results=10,
            strategy=segment.strategy
        )

        if not verified_videos:
            logger.error(f"No videos found for intro segment (strategy={segment.strategy})")
            return None

        # 25초 이상 필터링
        candidates = [
            v for v in verified_videos
            if v.duration >= self.INTRO_MIN_DURATION
        ]

        if not candidates:
            # 25초 미달 시 가장 긴 것
            candidates = sorted(
                verified_videos,
                key=lambda v: v.duration,
                reverse=True
            )
            logger.warning(
                f"No videos >= {self.INTRO_MIN_DURATION:.1f}s, using longest: {candidates[0].duration:.1f}s"
            )

        # 품질 점수 최고인 것 선택
        selected = max(candidates, key=lambda v: v.quality_score)

        return SelectedClip(
            video=selected,
            segment=segment,
            trim_duration=segment_duration  # 성경 구절 끝나는 지점까지 trim
        )

    def _select_closing_clip(
        self,
        segment: SegmentStrategy,
        segment_duration: float
    ) -> Optional[SelectedClip]:
        """
        마무리 구간 영상 선택 (20-30초, trim 안 함)

        Args:
            segment: 구간 전략
            segment_duration: 구간 길이 (초)

        Returns:
            선택된 클립
        """
        # Pexels 검색 (전략 기반)
        verified_videos = self.video_search.search_by_mood(
            mood=None,
            duration_needed=int(segment_duration),
            max_results=10,
            strategy=segment.strategy
        )

        if not verified_videos:
            logger.error(f"No videos found for closing segment (strategy={segment.strategy})")
            return None

        # 20-30초 범위 필터링
        candidates = [
            v for v in verified_videos
            if self.CLOSING_MIN_DURATION <= v.duration <= self.CLOSING_MAX_DURATION
        ]

        if not candidates:
            # 범위 내 없으면 가장 가까운 것
            candidates = sorted(
                verified_videos,
                key=lambda v: abs(v.duration - segment_duration)
            )
            logger.warning(
                f"No videos in 20-30s range, using closest: {candidates[0].duration:.1f}s"
            )

        # 품질 점수 최고인 것 선택
        selected = max(candidates, key=lambda v: v.quality_score)

        return SelectedClip(
            video=selected,
            segment=segment,
            trim_duration=None  # trim 안 함 (자연스럽게 종료)
        )

    def _select_middle_clip(
        self,
        segment: SegmentStrategy,
        segment_duration: float
    ) -> Optional[SelectedClip]:
        """
        중간 구간 영상 선택 (30-40초 우선, 없으면 15-20초 반복)

        Args:
            segment: 구간 전략
            segment_duration: 구간 길이 (초)

        Returns:
            선택된 클립

        Note:
            선호도 순서:
            1. 30~40초 영상 → 1번 재생 (자연스러움)
            2. 15~20초 영상 → 2번 반복 (자연 풍경만, 사람은 제외)

            ⚠️ human 전략은 반복 시 부자연스러우므로 긴 영상 필수!
        """
        # Pexels 검색 (전략 기반)
        verified_videos = self.video_search.search_by_mood(
            mood=None,
            duration_needed=int(segment_duration),
            max_results=10,
            strategy=segment.strategy
        )

        if not verified_videos:
            logger.error(
                f"No videos found for {segment.segment_type} (strategy={segment.strategy})"
            )
            return None

        # human 전략은 반복 불가 → 구간 길이 이상 영상 필수
        is_human = segment.strategy == "human"

        if is_human:
            # human: 구간 길이 이상 영상만 (반복 금지)
            candidates = [
                v for v in verified_videos
                if v.duration >= segment_duration
            ]

            if candidates:
                selected = max(candidates, key=lambda v: v.quality_score)
                logger.info(
                    f"Selected human video: {selected.duration:.1f}s (>= {segment_duration:.1f}s, no repeat)"
                )
                return SelectedClip(
                    video=selected,
                    segment=segment,
                    trim_duration=segment_duration  # 정확히 trim (반복 금지)
                )
            else:
                # human: 2개 영상 조합 (반복 대신!)
                # 길이 순 정렬 (긴 것부터)
                sorted_videos = sorted(
                    verified_videos,
                    key=lambda v: v.duration,
                    reverse=True
                )

                if len(sorted_videos) >= 2:
                    # 가장 긴 것 + 두 번째로 긴 것
                    video1 = sorted_videos[0]
                    video2 = sorted_videos[1]
                    total_duration = video1.duration + video2.duration

                    logger.warning(
                        f"No human video >= {segment_duration:.1f}s, using 2 videos: "
                        f"{video1.duration:.1f}s + {video2.duration:.1f}s = {total_duration:.1f}s "
                        f"(target: {segment_duration:.1f}s)"
                    )

                    return SelectedClip(
                        video=video1,
                        segment=segment,
                        trim_duration=None,  # 전체 재생
                        additional_videos=[video2]  # 두 번째 영상 추가
                    )
                else:
                    # 영상이 1개밖에 없으면 그것만 사용 (최악)
                    selected = sorted_videos[0]
                    logger.error(
                        f"Only 1 human video available: {selected.duration:.1f}s (need {segment_duration:.1f}s)"
                    )
                    return SelectedClip(
                        video=selected,
                        segment=segment,
                        trim_duration=None  # 전체 재생 (부족하지만 어쩔 수 없음)
                    )

        # 자연 풍경 (nature_calm, nature_bright): 반복 가능
        # 우선순위 1: 30-40초 영상 (이상적)
        ideal_candidates = [
            v for v in verified_videos
            if self.MIDDLE_IDEAL_MIN <= v.duration <= self.MIDDLE_IDEAL_MAX
        ]

        if ideal_candidates:
            selected = max(ideal_candidates, key=lambda v: v.quality_score)
            logger.info(
                f"Selected ideal middle video: {selected.duration:.1f}s (30-40s range)"
            )
            return SelectedClip(
                video=selected,
                segment=segment,
                trim_duration=None  # 1번 재생 (반복 없음)
            )

        # 우선순위 2: 15-20초 영상 (대안 - 2번 반복 OK, 자연 풍경이므로)
        fallback_candidates = [
            v for v in verified_videos
            if self.MIDDLE_FALLBACK_MIN <= v.duration <= self.MIDDLE_FALLBACK_MAX
        ]

        if fallback_candidates:
            selected = max(fallback_candidates, key=lambda v: v.quality_score)
            logger.info(
                f"Selected fallback middle video: {selected.duration:.1f}s (15-20s range, will repeat)"
            )
            return SelectedClip(
                video=selected,
                segment=segment,
                trim_duration=None  # 2번 반복
            )

        # 마지막 대안: 구간 길이의 절반에 가장 가까운 영상
        target_duration = segment_duration / 2
        candidates = sorted(
            verified_videos,
            key=lambda v: abs(v.duration - target_duration)
        )
        selected = candidates[0]
        logger.warning(
            f"No videos in ideal ranges, using closest to {target_duration:.1f}s: {selected.duration:.1f}s"
        )

        return SelectedClip(
            video=selected,
            segment=segment,
            trim_duration=None  # 반복 재생
        )


def get_clip_selector() -> VideoClipSelector:
    """VideoClipSelector 싱글톤"""
    return VideoClipSelector()
