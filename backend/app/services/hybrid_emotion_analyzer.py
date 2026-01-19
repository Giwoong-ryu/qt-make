"""
하이브리드 감정 분석기 (Hybrid Emotion Analyzer)

템플릿 매칭 + 빈도 분석을 결합하여
3분할 섹션별로 최적의 영상 전략 결정
"""
import logging
from dataclasses import dataclass
from typing import List, Tuple

from app.services.emotion_frequency_analyzer import (
    get_emotion_analyzer,
    EmotionFrequency
)
from app.services.template_analyzer import (
    get_template_analyzer,
    TemplateSection
)

logger = logging.getLogger(__name__)


@dataclass
class SectionStrategy:
    """섹션별 전략 정보"""
    start_time: float       # 시작 시간 (초)
    end_time: float         # 종료 시간 (초)
    strategy: str           # 영상 전략
    source: str             # 전략 출처 (template/frequency)
    confidence: float       # 확신도 (0.0-1.0)


class HybridEmotionAnalyzer:
    """하이브리드 감정 분석기 (템플릿 + 빈도)"""

    def __init__(self):
        self.frequency_analyzer = get_emotion_analyzer()
        self.template_analyzer = get_template_analyzer()

    def analyze_sections(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        num_sections: int = 3
    ) -> List[SectionStrategy]:
        """
        3분할 섹션별 전략 분석 (템플릿 우선, 빈도 보조)

        Args:
            subtitles: 자막 텍스트 리스트
            subtitle_timings: [(start, end), ...] 초 단위
            num_sections: 분할 개수 (기본 3)

        Returns:
            SectionStrategy 리스트 (섹션별 전략)
        """
        total_duration = subtitle_timings[-1][1] if subtitle_timings else 120.0
        section_duration = total_duration / num_sections

        # 1. 템플릿 패턴 추출
        template_sections = self.template_analyzer.analyze(subtitles)
        logger.info(f"Template sections found: {len(template_sections)}")

        # 2. 각 섹션 분석
        section_strategies = []

        for section_idx in range(num_sections):
            start_time = section_idx * section_duration
            end_time = (section_idx + 1) * section_duration

            # 이 시간대에 해당하는 자막 인덱스 찾기
            subtitle_indices = self._get_subtitle_indices_in_timerange(
                subtitle_timings, start_time, end_time
            )

            if not subtitle_indices:
                # 자막 없으면 기본값
                section_strategies.append(SectionStrategy(
                    start_time=start_time,
                    end_time=end_time,
                    strategy="nature_calm",
                    source="default",
                    confidence=0.5
                ))
                continue

            # 3. 템플릿 매칭 확인 (우선)
            template_strategy = self._check_template_match(
                subtitle_indices, template_sections
            )

            if template_strategy:
                section_strategies.append(SectionStrategy(
                    start_time=start_time,
                    end_time=end_time,
                    strategy=template_strategy.strategy,
                    source="template",
                    confidence=template_strategy.confidence
                ))
                logger.info(
                    f"Section {section_idx+1}: template={template_strategy.strategy} "
                    f"({template_strategy.pattern_type})"
                )
                continue

            # 4. 빈도 분석 (템플릿 매칭 실패 시)
            section_subtitles = [subtitles[i] for i in subtitle_indices]
            frequency = self.frequency_analyzer.analyze(section_subtitles)
            strategy = self.frequency_analyzer.get_video_strategy(frequency)

            section_strategies.append(SectionStrategy(
                start_time=start_time,
                end_time=end_time,
                strategy=strategy,
                source="frequency",
                confidence=0.7  # 빈도 분석 확신도
            ))
            logger.info(
                f"Section {section_idx+1}: frequency={strategy} "
                f"(pain={frequency.pain_ratio:.1f}%, hope={frequency.hope_ratio:.1f}%)"
            )

        return section_strategies

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

    def _check_template_match(
        self,
        subtitle_indices: List[int],
        template_sections: List[TemplateSection]
    ) -> TemplateSection | None:
        """
        자막 인덱스들이 템플릿 섹션과 매칭되는지 확인

        Returns:
            매칭된 TemplateSection (없으면 None)
        """
        # 자막 인덱스들이 템플릿 섹션 범위에 50% 이상 포함되면 매칭
        for template in template_sections:
            overlap_count = sum(
                1 for idx in subtitle_indices
                if template.start_idx <= idx <= template.end_idx
            )

            overlap_ratio = overlap_count / len(subtitle_indices)

            if overlap_ratio >= 0.5:  # 50% 이상 겹치면 매칭
                return template

        return None


def get_hybrid_analyzer() -> HybridEmotionAnalyzer:
    """HybridEmotionAnalyzer 싱글톤"""
    return HybridEmotionAnalyzer()
