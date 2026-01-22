"""
자막 기반 컷 생성기 (Subtitle-Driven Cut Generator)

핵심 원칙:
- 각 컷의 start_time = 첫 번째 자막의 start_time (정확히 일치!)
- 클립 전환 시점과 자막 시작이 동기화되어 시청 경험 향상
- 문장 종결어미에서 컷 나누기 선호

Usage:
    generator = SubtitleDrivenCutGenerator(min_cut_duration=4.0, max_cut_duration=12.0)
    cuts = generator.generate_cuts(subtitles, subtitle_timings)

    for cut in cuts:
        print(f"Cut {cut.index}: {cut.start_time}s ~ {cut.end_time}s")
        print(f"  Subtitles: {cut.subtitle_texts}")
"""
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from app.services.stt import WhisperService

logger = logging.getLogger(__name__)


# 한국어 문장 종결어미 패턴 (우선순위 순)
# stt.py와 기준 통일: 강력해진 패턴 사용
SENTENCE_ENDINGS = WhisperService.KOREAN_SENTENCE_ENDINGS

# 문장 중간에 오는 연결어미 (컷 분리 회피)
# stt.py와 기준 통일
CONNECTING_ENDINGS = WhisperService.KOREAN_CONNECTING_ENDINGS


@dataclass
class SubtitleCut:
    """자막 기반 컷 정보"""
    index: int
    start_time: float           # = 첫 번째 자막의 start_time (핵심!)
    end_time: float
    duration: float = field(init=False)
    subtitle_indices: List[int] = field(default_factory=list)
    subtitle_texts: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.duration = self.end_time - self.start_time


class SubtitleDrivenCutGenerator:
    """
    자막 시작 시점 기반 컷 생성기

    핵심 규칙:
    1. 각 컷의 start_time = 첫 번째 자막의 start_time (정확히!)
    2. 컷 길이가 min_cut_duration 미만이면 다음 자막과 병합
    3. 컷 길이가 max_cut_duration 초과하면 강제 분할
    4. 문장 종결어미에서 컷 나누기 선호

    Example:
        subtitles = ["산을 오르며", "기도합니다.", "하나님께", "감사드립니다."]
        timings = [(0.0, 2.5), (2.5, 5.0), (5.0, 7.0), (7.0, 10.0)]

        generator = SubtitleDrivenCutGenerator()
        cuts = generator.generate_cuts(subtitles, timings)

        # 결과:
        # Cut 0: start_time=0.0s (= 자막 0의 start) ~ 5.0s
        #        ["산을 오르며", "기도합니다."]
        # Cut 1: start_time=5.0s (= 자막 2의 start) ~ 10.0s
        #        ["하나님께", "감사드립니다."]
    """

    def __init__(
        self,
        min_cut_duration: float = 4.0,
        max_cut_duration: float = 12.0,
        prefer_sentence_end: bool = True,
        target_cut_duration: float = 8.0
    ):
        """
        초기화

        Args:
            min_cut_duration: 최소 컷 길이 (초). 이보다 짧으면 다음 자막과 병합
            max_cut_duration: 최대 컷 길이 (초). 이보다 길면 강제 분할
            prefer_sentence_end: True면 문장 종결어미에서 컷 분리 선호
            target_cut_duration: 목표 컷 길이 (초). 이상적인 컷 길이
        """
        self.min_cut_duration = min_cut_duration
        self.max_cut_duration = max_cut_duration
        self.prefer_sentence_end = prefer_sentence_end
        self.target_cut_duration = target_cut_duration

        logger.info(
            f"[SubtitleDrivenCutGenerator] Initialized: "
            f"min={min_cut_duration}s, max={max_cut_duration}s, "
            f"target={target_cut_duration}s, prefer_sentence_end={prefer_sentence_end}"
        )

    def generate_cuts(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        audio_duration: Optional[float] = None
    ) -> List[SubtitleCut]:
        """
        자막과 타이밍을 기반으로 컷 리스트 생성

        핵심: 각 컷의 start_time = 첫 번째 자막의 start_time

        Args:
            subtitles: 자막 텍스트 리스트 ["산을 오르며", "기도합니다.", ...]
            subtitle_timings: 타이밍 리스트 [(0.0, 2.5), (2.5, 5.0), ...]
            audio_duration: 전체 오디오 길이 (초). 마지막 컷 end_time 조정용

        Returns:
            SubtitleCut 리스트
        """
        if not subtitles or not subtitle_timings:
            logger.warning("[SubtitleDrivenCutGenerator] Empty subtitles or timings")
            return []

        if len(subtitles) != len(subtitle_timings):
            logger.error(
                f"[SubtitleDrivenCutGenerator] Mismatch: "
                f"{len(subtitles)} subtitles vs {len(subtitle_timings)} timings"
            )
            return []

        cuts = []
        cut_index = 0

        # 현재 컷 시작점 추적
        current_cut_start_idx = 0
        current_cut_start_time = subtitle_timings[0][0]  # 첫 자막의 start_time

        for idx in range(len(subtitles)):
            text = subtitles[idx]
            start_time, end_time = subtitle_timings[idx]

            # 현재까지의 컷 길이 계산
            current_cut_duration = end_time - current_cut_start_time

            # 컷 생성 여부 결정
            should_create_cut = self._should_create_cut(
                text=text,
                current_duration=current_cut_duration,
                is_last=idx == len(subtitles) - 1,
                subtitles_in_cut=idx - current_cut_start_idx + 1
            )

            if should_create_cut:
                # 컷 생성
                cut = SubtitleCut(
                    index=cut_index,
                    start_time=current_cut_start_time,  # 첫 자막의 start_time!
                    end_time=end_time,
                    subtitle_indices=list(range(current_cut_start_idx, idx + 1)),
                    subtitle_texts=subtitles[current_cut_start_idx:idx + 1]
                )
                cuts.append(cut)

                logger.debug(
                    f"[SubtitleDrivenCutGenerator] Created cut {cut_index}: "
                    f"{cut.start_time:.2f}s ~ {cut.end_time:.2f}s "
                    f"({cut.duration:.2f}s, {len(cut.subtitle_texts)} subtitles)"
                )

                # 다음 컷 준비
                cut_index += 1
                if idx + 1 < len(subtitles):
                    current_cut_start_idx = idx + 1
                    current_cut_start_time = subtitle_timings[idx + 1][0]  # 다음 자막의 start_time!

        # 마지막 컷의 end_time을 오디오 길이에 맞게 조정
        if cuts and audio_duration:
            if cuts[-1].end_time < audio_duration:
                cuts[-1].end_time = audio_duration
                cuts[-1].duration = cuts[-1].end_time - cuts[-1].start_time
                logger.debug(
                    f"[SubtitleDrivenCutGenerator] Extended last cut to audio duration: "
                    f"{cuts[-1].end_time:.2f}s"
                )

        # 결과 로그
        logger.info(
            f"[SubtitleDrivenCutGenerator] Generated {len(cuts)} cuts from "
            f"{len(subtitles)} subtitles"
        )
        for cut in cuts:
            logger.info(
                f"  Cut {cut.index}: {cut.start_time:.2f}s ~ {cut.end_time:.2f}s "
                f"({cut.duration:.2f}s) - subtitles {cut.subtitle_indices[0]}-{cut.subtitle_indices[-1]}"
            )

        return cuts

    def _should_create_cut(
        self,
        text: str,
        current_duration: float,
        is_last: bool,
        subtitles_in_cut: int
    ) -> bool:
        """
        현재 시점에서 컷을 생성해야 하는지 결정

        Args:
            text: 현재 자막 텍스트
            current_duration: 현재까지의 컷 길이
            is_last: 마지막 자막 여부
            subtitles_in_cut: 현재 컷에 포함된 자막 개수

        Returns:
            True면 컷 생성
        """
        # 조건 1: 마지막 자막이면 무조건 컷 생성
        if is_last:
            return True

        # 조건 2: 최대 길이 초과 시 강제 컷
        if current_duration >= self.max_cut_duration:
            logger.debug(
                f"[SubtitleDrivenCutGenerator] Force cut: duration {current_duration:.2f}s "
                f">= max {self.max_cut_duration}s"
            )
            return True

        # 조건 3: 최소 길이 미만이면 컷 생성하지 않음
        if current_duration < self.min_cut_duration:
            return False

        # 조건 4: 연결어미로 끝나면 컷 생성하지 않음 (문장 중간)
        if self._ends_with_connecting_word(text):
            return False

        # 조건 5: 문장 종결어미 선호 모드
        if self.prefer_sentence_end:
            if self._is_sentence_end(text):
                # 목표 길이 근처이면서 문장 종결이면 컷 생성
                if current_duration >= self.target_cut_duration * 0.7:
                    return True
            # 문장 종결이 아니면 목표 길이 도달해도 더 기다림
            # (단, 최대 길이는 넘지 않음 - 위에서 처리됨)
            return False

        # 조건 6: 목표 길이 도달 시 컷 생성 (prefer_sentence_end=False인 경우)
        if current_duration >= self.target_cut_duration:
            return True

        return False

    def _is_sentence_end(self, text: str) -> bool:
        """문장 종결어미로 끝나는지 확인"""
        text = text.strip()
        if not text:
            return False

        # 1. 문장부호 자체가 강력한 종결 신호
        if text.endswith(('.', '!', '?', '。')):
            return True

        # 2. 문장부호 제거 후 어미 매칭 (예: "합니다," -> "합니다")
        text_clean = text.rstrip('.!?。,"\'')
        
        for ending in SENTENCE_ENDINGS:
            if text_clean.endswith(ending):
                return True
        return False

    def _ends_with_connecting_word(self, text: str) -> bool:
        """연결어미로 끝나는지 확인 (문장 중간)"""
        text = text.strip()
        # 쉼표 등 제거
        text_clean = text.rstrip(',"\'')
        
        for ending in CONNECTING_ENDINGS:
            if text_clean.endswith(ending):
                return True
        return False

    def to_cut_list(self, cuts: List[SubtitleCut]) -> List[dict]:
        """
        SubtitleCut 리스트를 기존 Cut 형식의 dict 리스트로 변환
        (기존 코드와의 호환성 유지)

        Args:
            cuts: SubtitleCut 리스트

        Returns:
            기존 Cut 호환 dict 리스트
        """
        return [
            {
                "index": cut.index,
                "start_time": cut.start_time,
                "end_time": cut.end_time,
                "duration": cut.duration,
                "subtitle_texts": cut.subtitle_texts,
                "subtitle_indices": cut.subtitle_indices,
            }
            for cut in cuts
        ]


# 모듈 레벨 싱글톤 (선택적)
_generator: Optional[SubtitleDrivenCutGenerator] = None


def get_subtitle_driven_cut_generator(
    min_cut_duration: float = 4.0,
    max_cut_duration: float = 12.0,
    prefer_sentence_end: bool = True,
    target_cut_duration: float = 8.0
) -> SubtitleDrivenCutGenerator:
    """
    SubtitleDrivenCutGenerator 싱글톤 반환

    Args:
        min_cut_duration: 최소 컷 길이 (초)
        max_cut_duration: 최대 컷 길이 (초)
        prefer_sentence_end: 문장 종결어미 선호 여부
        target_cut_duration: 목표 컷 길이 (초)

    Returns:
        SubtitleDrivenCutGenerator 인스턴스
    """
    global _generator
    if _generator is None:
        _generator = SubtitleDrivenCutGenerator(
            min_cut_duration=min_cut_duration,
            max_cut_duration=max_cut_duration,
            prefer_sentence_end=prefer_sentence_end,
            target_cut_duration=target_cut_duration
        )
    return _generator
