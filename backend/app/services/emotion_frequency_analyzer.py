"""
감정 단어 빈도 분석기 (Emotion Frequency Analyzer)

자막에서 고통/희망 관련 단어 빈도를 측정하여
인간 영상 vs 자연 영상 선택 결정
"""
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class EmotionFrequency:
    """감정 단어 빈도 분석 결과"""
    pain_count: int = 0       # 고통 관련 단어 빈도
    hope_count: int = 0       # 희망 관련 단어 빈도
    total_words: int = 0      # 전체 단어 수
    pain_ratio: float = 0.0   # 고통 비율 (%)
    hope_ratio: float = 0.0   # 희망 비율 (%)
    needs_human_video: bool = False  # 인간 영상 필요 여부


class EmotionFrequencyAnalyzer:
    """감정 단어 빈도 분석기"""

    # 고통 관련 키워드 (QT 콘텐츠 빈출 단어)
    PAIN_KEYWORDS = [
        # 직접적 고통
        "고통", "아픔", "힘들", "괴롭", "슬픔", "절망",
        # 결핍
        "외로움", "고독", "혼자", "버림", "상실", "잃",
        # 회개/수치
        "죄", "부끄", "수치", "회개", "용서", "잘못",
        # 두려움
        "두렵", "무서", "불안", "걱정", "염려",
        # 약함
        "연약", "무력", "지침", "피곤", "낙담"
    ]

    # 희망 관련 키워드 (긍정 전환 구간)
    HOPE_KEYWORDS = [
        # 위로
        "위로", "평안", "안식", "쉼", "안정",
        # 빛/새벽
        "빛", "새벽", "아침", "해", "밝",
        # 감사
        "감사", "은혜", "축복", "기쁨", "사랑",
        # 희망
        "희망", "소망", "기대", "회복", "치유"
    ]

    # 임계값 (전체 단어 대비 비율, %)
    PAIN_THRESHOLD = 5.0   # 고통 단어가 5% 이상이면 인간 영상 필요
    HOPE_THRESHOLD = 3.0   # 희망 단어가 3% 이상이면 밝은 자연 영상

    def analyze(self, subtitles: List[str]) -> EmotionFrequency:
        """
        자막에서 감정 단어 빈도 분석

        Args:
            subtitles: 자막 텍스트 리스트

        Returns:
            EmotionFrequency: 분석 결과
        """
        # 전체 텍스트 결합
        full_text = " ".join(subtitles)
        words = full_text.split()
        total_words = len(words)

        if total_words == 0:
            logger.warning("Empty subtitle text")
            return EmotionFrequency()

        # 고통 단어 카운트
        pain_count = sum(
            1 for word in words
            if any(keyword in word for keyword in self.PAIN_KEYWORDS)
        )

        # 희망 단어 카운트
        hope_count = sum(
            1 for word in words
            if any(keyword in word for keyword in self.HOPE_KEYWORDS)
        )

        # 비율 계산
        pain_ratio = (pain_count / total_words) * 100
        hope_ratio = (hope_count / total_words) * 100

        # 인간 영상 필요 여부 판단
        needs_human = pain_ratio >= self.PAIN_THRESHOLD

        result = EmotionFrequency(
            pain_count=pain_count,
            hope_count=hope_count,
            total_words=total_words,
            pain_ratio=pain_ratio,
            hope_ratio=hope_ratio,
            needs_human_video=needs_human
        )

        logger.info(
            f"Emotion Analysis: {pain_count} pain words ({pain_ratio:.1f}%), "
            f"{hope_count} hope words ({hope_ratio:.1f}%), "
            f"Human video: {needs_human}"
        )

        return result

    def get_video_strategy(self, frequency: EmotionFrequency) -> str:
        """
        빈도 분석 결과 기반 영상 전략 결정

        Args:
            frequency: 감정 빈도 분석 결과

        Returns:
            "human" (인간 영상) / "nature_bright" (밝은 자연) / "nature_calm" (차분한 자연)
        """
        # Case 1: 고통 강조 (빈도 > 임계값)
        if frequency.needs_human_video:
            return "human"

        # Case 2: 희망 강조 (희망 단어 많음)
        if frequency.hope_ratio >= self.HOPE_THRESHOLD:
            return "nature_bright"

        # Case 3: 기본값 (차분한 자연)
        return "nature_calm"


def get_emotion_analyzer() -> EmotionFrequencyAnalyzer:
    """EmotionFrequencyAnalyzer 싱글톤"""
    return EmotionFrequencyAnalyzer()
