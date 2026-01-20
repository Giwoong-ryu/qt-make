"""
컷 리스트 생성기 (Stage 1: 기획자 모드)

자막 전체를 분석하여 시각적 전환 포인트를 찾고,
4-8초 간격의 의미 단위로 컷 리스트를 생성합니다.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class Cut:
    """컷 정보"""
    index: int
    start_time: float
    end_time: float
    subtitle_texts: List[str]  # 이 컷에 포함된 자막들
    duration: float

    def __post_init__(self):
        self.duration = self.end_time - self.start_time


class CutListGenerator:
    """
    LLM 기획자: 자막을 의미 단위로 분석하여 컷 리스트 생성

    Example:
        subtitles = ["산을 오르며", "기도합니다", "하나님께", "감사드립니다"]
        timings = [(0.0, 2.5), (2.5, 4.5), (4.5, 7.0), (7.0, 10.0)]

        cuts = generator.generate_cuts(subtitles, timings)
        # → [Cut(0-4.5s: "산을 오르며 기도합니다"), Cut(4.5-10.0s: "하나님께 감사드립니다")]
    """

    def __init__(self, gemini_api_key: str = None):
        """
        초기화

        Args:
            gemini_api_key: Gemini API 키
        """
        self.api_key = gemini_api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def generate_cuts(
        self,
        subtitles: List[str],
        subtitle_timings: List[Tuple[float, float]],
        min_duration: float = 8.0,
        max_duration: float = 15.0,
        target_cuts: int = 11
    ) -> List[Cut]:
        """
        자막을 의미 단위로 분석하여 컷 리스트 생성

        Args:
            subtitles: 자막 텍스트 리스트 ["산을 오르며", "기도합니다", ...]
            subtitle_timings: 타이밍 리스트 [(0.0, 2.5), (2.5, 4.5), ...]
            min_duration: 최소 컷 길이 (초)
            max_duration: 최대 컷 길이 (초)
            target_cuts: 목표 컷 개수 (기본 11개, 33개 자막 ÷ 3)

        Returns:
            컷 리스트
        """
        if not subtitles or not subtitle_timings:
            logger.warning("Empty subtitles or timings")
            return []

        # Step 1: 전체 스크립트 구성
        script_with_index = []
        for idx, (text, (start, end)) in enumerate(zip(subtitles, subtitle_timings)):
            script_with_index.append(f"[{idx}] {text} ({start:.1f}s-{end:.1f}s)")

        full_script = "\n".join(script_with_index)

        # Step 2: LLM에게 컷 포인트 요청
        prompt = f'''
You are a documentary film editor. Your task is to identify **visual transition points** in this Korean script.

Rules:
1. Group subtitles into **meaning units** (의미 단위), not individual lines.
2. **Target about {target_cuts} cuts total** (approximately every 2-4 subtitles).
3. Each cut should be between {min_duration}-{max_duration} seconds long.
4. Mark transition points where:
   - Topic/mood changes (주제/분위기 전환)
   - Scene should shift (장면 전환 필요)
   - Emotional tone shifts (감정 톤 변화)
5. Output format: List of subtitle index ranges that should be grouped together.
   Example: "0-2, 3-5, 6-9" means:
   - Cut 1: subtitles 0, 1, 2
   - Cut 2: subtitles 3, 4, 5
   - Cut 3: subtitles 6, 7, 8, 9

Script:
{full_script}

Output (only the index ranges, comma-separated):'''

        try:
            response = self.model.generate_content(prompt)
            cut_ranges_text = response.text.strip()
            logger.info(f"[CutListGenerator] LLM response: {cut_ranges_text}")

            # Step 3: 응답 파싱
            cuts = self._parse_cut_ranges(
                cut_ranges_text,
                subtitles,
                subtitle_timings,
                min_duration,
                max_duration
            )

            logger.info(f"[CutListGenerator] Generated {len(cuts)} cuts")
            for cut in cuts:
                logger.info(
                    f"  Cut {cut.index}: {cut.start_time:.1f}s-{cut.end_time:.1f}s "
                    f"({cut.duration:.1f}s) - {len(cut.subtitle_texts)} subtitles"
                )

            return cuts

        except Exception as e:
            logger.error(f"[CutListGenerator] Failed to generate cuts: {e}")
            # Fallback: 단순 시간 기반 그룹핑 (6초 단위)
            return self._fallback_cuts(subtitles, subtitle_timings, target_duration=6.0)

    def _parse_cut_ranges(
        self,
        ranges_text: str,
        subtitles: List[str],
        timings: List[Tuple[float, float]],
        min_duration: float,
        max_duration: float
    ) -> List[Cut]:
        """
        LLM 응답에서 컷 범위 파싱

        Args:
            ranges_text: "0-2, 3-5, 6-9" 형태의 문자열
            subtitles: 자막 리스트
            timings: 타이밍 리스트
            min_duration: 최소 컷 길이
            max_duration: 최대 컷 길이

        Returns:
            컷 리스트
        """
        cuts = []
        cut_index = 0

        # 패턴: "0-2" 또는 "0-2, 3-5" 형태
        range_pattern = r'(\d+)-(\d+)'
        matches = re.findall(range_pattern, ranges_text)

        if not matches:
            logger.warning("[CutListGenerator] Failed to parse cut ranges, using fallback")
            return self._fallback_cuts(subtitles, timings, target_duration=6.0)

        for start_idx_str, end_idx_str in matches:
            start_idx = int(start_idx_str)
            end_idx = int(end_idx_str)

            # 범위 검증
            if start_idx < 0 or end_idx >= len(subtitles) or start_idx > end_idx:
                logger.warning(f"Invalid range: {start_idx}-{end_idx}, skipping")
                continue

            # 컷 생성
            start_time = timings[start_idx][0]
            end_time = timings[end_idx][1]
            duration = end_time - start_time

            # 길이 검증 (너무 짧거나 긴 컷은 조정)
            if duration < min_duration:
                logger.warning(
                    f"Cut {start_idx}-{end_idx} too short ({duration:.1f}s), "
                    f"extending to next subtitle"
                )
                if end_idx + 1 < len(timings):
                    end_idx += 1
                    end_time = timings[end_idx][1]
                    duration = end_time - start_time

            if duration > max_duration:
                logger.warning(
                    f"Cut {start_idx}-{end_idx} too long ({duration:.1f}s), "
                    f"will be split in next iteration"
                )
                # TODO: 긴 컷을 자동으로 분할하는 로직 추가 가능

            cut = Cut(
                index=cut_index,
                start_time=start_time,
                end_time=end_time,
                subtitle_texts=subtitles[start_idx:end_idx+1],
                duration=duration
            )
            cuts.append(cut)
            cut_index += 1

        return cuts

    def _fallback_cuts(
        self,
        subtitles: List[str],
        timings: List[Tuple[float, float]],
        target_duration: float = 12.0,
        min_subtitles_per_cut: int = 2
    ) -> List[Cut]:
        """
        LLM 실패 시 폴백: 문장 종결 기반 그룹핑

        전략:
        1. 기본적으로 3개씩 묶기 (디폴트)
        2. 문장 종결 부호('다.', '까.', '요.') 발견 시 → 다음 자막부터 새 컷 시작
        3. 최소 2개 이상의 자막이 묶여야 컷 생성

        Args:
            subtitles: 자막 리스트
            timings: 타이밍 리스트
            target_duration: 목표 컷 길이 (초, 기본 12초 = 136초 ÷ 11)
            min_subtitles_per_cut: 컷당 최소 자막 개수

        Returns:
            컷 리스트
        """
        logger.info(
            f"[CutListGenerator] Using fallback cuts with sentence detection "
            f"(target: {target_duration}s, min: {min_subtitles_per_cut} subtitles/cut)"
        )

        # 문장 종결 패턴 (한국어 종결어미)
        SENTENCE_ENDINGS = ['다.', '까.', '요.', '죠.', '네.', '어.']

        cuts = []
        cut_index = 0
        current_start_idx = 0
        current_start_time = timings[0][0]
        subtitle_count = 0  # 현재 컷에 포함된 자막 개수

        for idx, (text, (start, end)) in enumerate(zip(subtitles, timings)):
            subtitle_count += 1
            current_duration = end - current_start_time

            # 문장 종결 여부 체크
            is_sentence_end = any(text.endswith(ending) for ending in SENTENCE_ENDINGS)

            # 컷 생성 조건
            should_cut = False

            # 조건 1: 문장 종결 + 최소 자막 개수 충족
            if is_sentence_end and subtitle_count >= min_subtitles_per_cut:
                should_cut = True
                logger.debug(
                    f"  Cut at sentence end: '{text}' "
                    f"(subtitles: {subtitle_count}, duration: {current_duration:.1f}s)"
                )

            # 조건 2: 목표 길이 도달 (문장 종결 없어도)
            elif current_duration >= target_duration:
                should_cut = True
                logger.debug(
                    f"  Cut at duration limit: {current_duration:.1f}s >= {target_duration}s "
                    f"(subtitles: {subtitle_count})"
                )

            # 조건 3: 마지막 자막
            elif idx == len(subtitles) - 1:
                should_cut = True
                logger.debug(f"  Final cut (subtitles: {subtitle_count})")

            if should_cut:
                cut = Cut(
                    index=cut_index,
                    start_time=current_start_time,
                    end_time=end,
                    subtitle_texts=subtitles[current_start_idx:idx+1],
                    duration=end - current_start_time
                )
                cuts.append(cut)

                # 다음 컷 준비
                cut_index += 1
                subtitle_count = 0  # 리셋

                if idx + 1 < len(subtitles):
                    current_start_idx = idx + 1
                    current_start_time = timings[idx + 1][0]

        logger.info(f"[CutListGenerator] Generated {len(cuts)} cuts (fallback mode)")
        return cuts
