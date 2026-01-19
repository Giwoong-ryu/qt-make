"""
고정 구간 + 유연 구간 분석기 (Fixed + Flexible Segment Analyzer)

QT 실제 구조 기반:
- 처음 10-15초: 도입+성경 (고정 nature_calm)
- 마지막 10-15초: 마무리 (고정 nature_bright/calm)
- 나머지 중간: 문제+해결 (빈도 분석, 랜덤성 강함)
"""
import logging
from dataclasses import dataclass
from typing import List, Tuple

from app.services.emotion_frequency_analyzer import (
    get_emotion_analyzer,
    EmotionFrequency
)
from app.services.template_analyzer import get_template_analyzer

logger = logging.getLogger(__name__)


@dataclass
class SegmentStrategy:
    """구간별 전략 정보"""
    start_time: float       # 시작 시간 (초)
    end_time: float         # 종료 시간 (초)
    strategy: str           # 영상 전략
    segment_type: str       # 구간 타입 (fixed_intro/flexible_middle/fixed_closing)
    confidence: float       # 확신도 (0.0-1.0)


class FixedSegmentAnalyzer:
    """고정 구간 + 유연 구간 분석기"""

    # 고정 구간 길이 (초)
    INTRO_DURATION = 15.0    # 처음 15초 (도입+성경)
    CLOSING_DURATION = 15.0  # 마지막 15초 (마무리)

    def __init__(self):
        self.frequency_analyzer = get_emotion_analyzer()
        self.template_analyzer = get_template_analyzer()

    def analyze_segments(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]]
    ) -> List[SegmentStrategy]:
        """
        고정 구간 + 유연 구간 분석

        Args:
            subtitles: 자막 텍스트 리스트
            subtitle_timings: [(start, end), ...] 초 단위

        Returns:
            SegmentStrategy 리스트 (구간별 전략)
        """
        total_duration = subtitle_timings[-1][1] if subtitle_timings else 120.0
        segments = []

        # 1. 처음 15초 (고정: 도입+성경)
        intro_segment = self._analyze_intro(
            subtitles, subtitle_timings, total_duration
        )
        segments.append(intro_segment)
        logger.info(f"Intro segment: 0-{intro_segment.end_time}s → {intro_segment.strategy}")

        # 2. 마지막 15초 (고정: 마무리)
        closing_segment = self._analyze_closing(
            subtitles, subtitle_timings, total_duration
        )
        segments.append(closing_segment)
        logger.info(f"Closing segment: {closing_segment.start_time}-{total_duration}s → {closing_segment.strategy}")

        # 3. 중간 구간 (유연: 빈도 분석)
        middle_start = intro_segment.end_time
        middle_end = closing_segment.start_time

        if middle_end > middle_start:
            middle_segments = self._analyze_middle(
                subtitles, subtitle_timings, middle_start, middle_end
            )
            segments.extend(middle_segments)
            logger.info(f"Middle segments: {len(middle_segments)}개 분석 완료")

        # 시간 순 정렬
        segments.sort(key=lambda s: s.start_time)

        return segments

    def _analyze_intro(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        total_duration: float
    ) -> SegmentStrategy:
        """처음 15초 분석 (고정: nature_calm)"""
        intro_duration = min(self.INTRO_DURATION, total_duration * 0.15)

        # 템플릿 확인 (도입+성경 패턴)
        template_sections = self.template_analyzer.analyze(subtitles)
        has_intro_pattern = any(
            s.pattern_type in ["introduction", "scripture"]
            for s in template_sections
        )

        return SegmentStrategy(
            start_time=0.0,
            end_time=intro_duration,
            strategy="nature_calm",
            segment_type="fixed_intro",
            confidence=0.95 if has_intro_pattern else 0.8
        )

    def _analyze_closing(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        total_duration: float
    ) -> SegmentStrategy:
        """마지막 15초 분석 (고정: nature_bright 또는 nature_calm)"""
        closing_duration = min(self.CLOSING_DURATION, total_duration * 0.15)
        closing_start = total_duration - closing_duration

        # 마지막 자막들 확인
        closing_indices = self._get_subtitle_indices_in_timerange(
            subtitle_timings, closing_start, total_duration
        )
        closing_subtitles = [subtitles[i] for i in closing_indices]
        closing_text = " ".join(closing_subtitles).lower()

        # 희망 키워드 많으면 bright, 아니면 calm
        hope_keywords = ["은혜", "축복", "기쁨", "사랑", "빛", "평안"]
        has_hope = any(keyword in closing_text for keyword in hope_keywords)

        strategy = "nature_bright" if has_hope else "nature_calm"

        return SegmentStrategy(
            start_time=closing_start,
            end_time=total_duration,
            strategy=strategy,
            segment_type="fixed_closing",
            confidence=0.85
        )

    def _analyze_middle(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        start_time: float,
        end_time: float
    ) -> List[SegmentStrategy]:
        """
        중간 구간 분석 (유연: 빈도 분석)

        중간 구간을 다시 2-3개로 나눠서 각각 빈도 분석
        (랜덤성 강한 문제+해결 섹션)
        """
        middle_duration = end_time - start_time

        # 중간 구간이 너무 짧으면 하나로
        if middle_duration < 30:
            return [self._analyze_middle_subsection(
                subtitles, subtitle_timings, start_time, end_time
            )]

        # 60초 이상이면 2분할, 90초 이상이면 3분할
        if middle_duration >= 90:
            num_segments = 3
        elif middle_duration >= 60:
            num_segments = 2
        else:
            num_segments = 1

        segments = []
        segment_duration = middle_duration / num_segments

        for i in range(num_segments):
            seg_start = start_time + (i * segment_duration)
            seg_end = start_time + ((i + 1) * segment_duration)

            segment = self._analyze_middle_subsection(
                subtitles, subtitle_timings, seg_start, seg_end
            )
            segments.append(segment)

        return segments

    def _analyze_middle_subsection(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        start_time: float,
        end_time: float
    ) -> SegmentStrategy:
        """중간 구간 서브섹션 빈도 분석"""
        # 이 시간대 자막들 추출
        subtitle_indices = self._get_subtitle_indices_in_timerange(
            subtitle_timings, start_time, end_time
        )
        section_subtitles = [subtitles[i] for i in subtitle_indices]

        # 빈도 분석
        frequency = self.frequency_analyzer.analyze(section_subtitles)
        strategy = self.frequency_analyzer.get_video_strategy(frequency)

        logger.info(
            f"Middle {start_time:.1f}-{end_time:.1f}s: {strategy} "
            f"(pain={frequency.pain_ratio:.1f}%, hope={frequency.hope_ratio:.1f}%)"
        )

        return SegmentStrategy(
            start_time=start_time,
            end_time=end_time,
            strategy=strategy,
            segment_type="flexible_middle",
            confidence=0.7
        )

    def _get_subtitle_indices_in_timerange(
        self,
        subtitle_timings: List[Tuple[float, float]],
        start_time: float,
        end_time: float
    ) -> List[int]:
        """시간대에 해당하는 자막 인덱스 찾기"""
        indices = []

        for idx, (sub_start, sub_end) in enumerate(subtitle_timings):
            # 자막이 구간과 겹치는지 확인
            if not (sub_end < start_time or sub_start > end_time):
                indices.append(idx)

        return indices


def get_fixed_segment_analyzer() -> FixedSegmentAnalyzer:
    """FixedSegmentAnalyzer 싱글톤"""
    return FixedSegmentAnalyzer()
