"""
자막 감정 분석 서비스

Gemini 2.5 Flash-Lite로 SRT 파일을 6차원 감정 데이터로 분석
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SubtitleEntry:
    """개별 자막 항목"""
    index: int
    start: float  # 초 단위
    end: float    # 초 단위
    text: str     # 2줄 포함 가능


@dataclass
class MoodData:
    """감정 분석 결과"""
    emotion: str       # joy, peace, hope, reverence, sorrow, contemplation, determination
    subject: str       # nature, abstract, light, water, sky, earth
    motion: str        # static, slow, medium, dynamic
    intensity: str     # subtle, moderate, strong
    color_tone: str    # warm, cool, neutral, golden


@dataclass
class AnalyzedSegment:
    """분석된 자막 세그먼트"""
    start: float
    end: float
    text: str
    mood: MoodData


class MoodAnalyzer:
    """자막 감정 분석기"""

    BATCH_SIZE = 5  # 5개씩 묶어서 API 호출 (비용 최소화)

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: Gemini API 키 (None이면 settings에서 가져옴)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def parse_srt(self, srt_path: str) -> List[SubtitleEntry]:
        """
        SRT 파일 파싱

        Args:
            srt_path: SRT 파일 경로

        Returns:
            SubtitleEntry 리스트
        """
        path = Path(srt_path)
        if not path.exists():
            raise FileNotFoundError(f"SRT file not found: {srt_path}")

        content = path.read_text(encoding='utf-8')
        entries = []

        # SRT 형식: 번호 → 시간 → 텍스트 → 빈 줄
        blocks = content.strip().split('\n\n')

        for block in blocks:
            lines = block.split('\n')
            if len(lines) < 3:
                continue

            try:
                index = int(lines[0])
                time_line = lines[1]
                text = '\n'.join(lines[2:])

                # 시간 파싱: 00:00:03,500 --> 00:00:07,200
                start_str, end_str = time_line.split(' --> ')
                start_sec = self._time_to_seconds(start_str)
                end_sec = self._time_to_seconds(end_str)

                entries.append(SubtitleEntry(
                    index=index,
                    start=start_sec,
                    end=end_sec,
                    text=text
                ))
            except Exception as e:
                logger.warning(f"Failed to parse SRT block: {e}")
                continue

        logger.info(f"Parsed {len(entries)} subtitle entries from {srt_path}")
        return entries

    def _time_to_seconds(self, time_str: str) -> float:
        """
        SRT 시간 형식을 초 단위로 변환

        Args:
            time_str: "00:00:03,500" 형식

        Returns:
            초 단위 (float)
        """
        # 00:00:03,500 → [00, 00, 03, 500]
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])

        return hours * 3600 + minutes * 60 + seconds

    def analyze_srt(self, srt_path: str) -> List[AnalyzedSegment]:
        """
        SRT 파일 전체 분석

        Args:
            srt_path: SRT 파일 경로

        Returns:
            AnalyzedSegment 리스트 (감정 데이터 포함)
        """
        entries = self.parse_srt(srt_path)

        # 배치 처리
        analyzed = []
        for i in range(0, len(entries), self.BATCH_SIZE):
            batch = entries[i:i + self.BATCH_SIZE]
            batch_results = self._analyze_batch(batch)
            analyzed.extend(batch_results)

        logger.info(f"Analyzed {len(analyzed)} segments")
        return analyzed

    def _analyze_batch(self, batch: List[SubtitleEntry]) -> List[AnalyzedSegment]:
        """
        자막 배치 감정 분석

        Args:
            batch: SubtitleEntry 리스트 (최대 5개)

        Returns:
            AnalyzedSegment 리스트
        """
        # 프롬프트 생성
        prompt = self._create_batch_prompt(batch)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1  # 일관성 중시
                )
            )

            # 응답 파싱
            return self._parse_gemini_response(batch, response.text)

        except Exception as e:
            logger.exception(f"Gemini API failed: {e}")
            # 폴백: 기본 mood 적용
            return [
                AnalyzedSegment(
                    start=entry.start,
                    end=entry.end,
                    text=entry.text,
                    mood=MoodData(
                        emotion='peace',
                        subject='light',
                        motion='slow',
                        intensity='subtle',
                        color_tone='warm'
                    )
                )
                for entry in batch
            ]

    def _create_batch_prompt(self, batch: List[SubtitleEntry]) -> str:
        """
        배치 분석 프롬프트 생성

        Args:
            batch: SubtitleEntry 리스트

        Returns:
            Gemini 프롬프트
        """
        subtitles_text = "\n\n".join([
            f"[{i+1}] {entry.text}"
            for i, entry in enumerate(batch)
        ])

        return f"""다음은 기독교 묵상 영상의 자막입니다. 각 자막의 감정을 6차원으로 분석해주세요.

자막:
{subtitles_text}

분석 기준:
- emotion: joy, peace, hope, reverence, sorrow, contemplation, determination
- subject: nature, abstract, light, water, sky, earth
- motion: static, slow, medium, dynamic
- intensity: subtle, moderate, strong
- color_tone: warm, cool, neutral, golden

응답 형식 (JSON):
[
  {{"emotion": "peace", "subject": "light", "motion": "slow", "intensity": "subtle", "color_tone": "warm"}},
  {{"emotion": "hope", "subject": "sky", "motion": "medium", "intensity": "moderate", "color_tone": "cool"}},
  ...
]

JSON 배열만 응답하세요."""

    def _parse_gemini_response(
        self,
        batch: List[SubtitleEntry],
        response_text: str
    ) -> List[AnalyzedSegment]:
        """
        Gemini 응답을 AnalyzedSegment로 변환

        Args:
            batch: 원본 SubtitleEntry 리스트
            response_text: Gemini JSON 응답

        Returns:
            AnalyzedSegment 리스트
        """
        import json

        try:
            # JSON 추출 (```json ... ``` 형태 가능)
            text = response_text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            moods = json.loads(text)

            # SubtitleEntry + MoodData 결합
            results = []
            for i, entry in enumerate(batch):
                mood_dict = moods[i] if i < len(moods) else moods[0]  # 부족하면 첫 번째 재사용

                results.append(AnalyzedSegment(
                    start=entry.start,
                    end=entry.end,
                    text=entry.text,
                    mood=MoodData(**mood_dict)
                ))

            return results

        except Exception as e:
            logger.exception(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response text: {response_text}")

            # 폴백: 기본 mood
            return [
                AnalyzedSegment(
                    start=entry.start,
                    end=entry.end,
                    text=entry.text,
                    mood=MoodData(
                        emotion='peace',
                        subject='light',
                        motion='slow',
                        intensity='subtle',
                        color_tone='warm'
                    )
                )
                for entry in batch
            ]


def get_mood_analyzer() -> MoodAnalyzer:
    """MoodAnalyzer 싱글톤"""
    return MoodAnalyzer()
