"""
QT 템플릿 패턴 분석기 (Template Pattern Analyzer)

QT 구조에서 반복되는 공통 패턴을 인식하여
해당 섹션에 고정된 영상 전략을 자동 적용
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TemplateSection:
    """템플릿 섹션 정보"""
    start_idx: int      # 시작 자막 인덱스
    end_idx: int        # 종료 자막 인덱스
    pattern_type: str   # 패턴 타입 (introduction/scripture/problem/solution/closing)
    strategy: str       # 고정 전략 (human/nature_bright/nature_calm)
    confidence: float   # 매칭 확신도 (0.0-1.0)


class QTTemplateAnalyzer:
    """QT 템플릿 패턴 분석기"""

    # 도입부 패턴 (항상 nature_calm)
    INTRODUCTION_KEYWORDS = [
        "오늘 우리가 함께 묵상할",
        "오늘의 성경 구절",
        "오늘 나눌 말씀",
        "함께 묵상하겠습니다",
        "말씀을 나누겠습니다"
    ]

    # 성경 구절 패턴 (항상 nature_calm)
    SCRIPTURE_KEYWORDS = [
        "시편", "창세기", "출애굽기", "레위기", "민수기", "신명기",
        "여호수아", "사사기", "룻기", "사무엘", "열왕기", "역대",
        "에스라", "느헤미야", "에스더", "욥기", "잠언", "전도서",
        "아가", "이사야", "예레미야", "예레미야애가", "에스겔", "다니엘",
        "호세아", "요엘", "아모스", "오바댜", "요나", "미가",
        "나훔", "하박국", "스바냐", "학개", "스가랴", "말라기",
        "마태복음", "마가복음", "누가복음", "요한복음",
        "사도행전", "로마서", "고린도", "갈라디아", "에베소",
        "빌립보", "골로새", "데살로니가", "디모데", "디도", "빌레몬",
        "히브리서", "야고보서", "베드로", "요한", "유다서", "요한계시록",
        "장", "절", "말씀하시"
    ]

    # 마무리/기도 패턴 (nature_bright 또는 nature_calm)
    CLOSING_KEYWORDS = [
        "오늘도 주님과 함께",
        "주님의 은혜가",
        "기도합니다",
        "아멘",
        "축복합니다",
        "함께하시길",
        "인도하시길"
    ]

    # 전환 키워드 (문제 → 해결 구간 인식)
    TRANSITION_KEYWORDS = [
        "하지만",
        "그러나",
        "그럼에도 불구하고",
        "하나님께서는",
        "주님께서는",
        "말씀하십니다"
    ]

    def analyze(self, subtitles: List[str]) -> List[TemplateSection]:
        """
        자막에서 템플릿 패턴 추출

        Args:
            subtitles: 자막 텍스트 리스트

        Returns:
            TemplateSection 리스트 (매칭된 섹션들)
        """
        sections = []

        # 1. 도입부 패턴 (처음 3개 자막 내에서 검색)
        intro_section = self._find_introduction(subtitles[:3])
        if intro_section:
            sections.append(intro_section)
            logger.info(f"Introduction pattern found: lines 0-{intro_section.end_idx}")

        # 2. 성경 구절 패턴 (처음 5개 자막 내에서 검색)
        scripture_section = self._find_scripture(subtitles[:5])
        if scripture_section:
            sections.append(scripture_section)
            logger.info(f"Scripture pattern found: lines {scripture_section.start_idx}-{scripture_section.end_idx}")

        # 3. 마무리 패턴 (마지막 3개 자막 내에서 검색)
        closing_section = self._find_closing(subtitles[-3:], len(subtitles))
        if closing_section:
            sections.append(closing_section)
            logger.info(f"Closing pattern found: lines {closing_section.start_idx}-{closing_section.end_idx}")

        # 4. 전환 구간 패턴 (중간 섹션에서 검색)
        transition_sections = self._find_transitions(subtitles)
        sections.extend(transition_sections)

        # 인덱스 순서로 정렬
        sections.sort(key=lambda s: s.start_idx)

        logger.info(f"Template analysis complete: {len(sections)} sections identified")
        return sections

    def _find_introduction(self, subtitles: List[str]) -> Optional[TemplateSection]:
        """도입부 패턴 찾기 (처음 3개 자막)"""
        full_text = " ".join(subtitles).lower()

        for keyword in self.INTRODUCTION_KEYWORDS:
            if keyword in full_text:
                return TemplateSection(
                    start_idx=0,
                    end_idx=min(2, len(subtitles) - 1),  # 최대 3개 자막
                    pattern_type="introduction",
                    strategy="nature_calm",
                    confidence=0.9
                )

        return None

    def _find_scripture(self, subtitles: List[str]) -> Optional[TemplateSection]:
        """성경 구절 패턴 찾기 (처음 5개 자막)"""
        for idx, subtitle in enumerate(subtitles):
            text = subtitle.lower()

            # 성경 책명 + 장절 패턴
            for keyword in self.SCRIPTURE_KEYWORDS:
                if keyword in text:
                    return TemplateSection(
                        start_idx=idx,
                        end_idx=min(idx + 1, len(subtitles) - 1),  # 2개 자막
                        pattern_type="scripture",
                        strategy="nature_calm",
                        confidence=0.95
                    )

        return None

    def _find_closing(self, subtitles: List[str], total_length: int) -> Optional[TemplateSection]:
        """마무리 패턴 찾기 (마지막 3개 자막)"""
        full_text = " ".join(subtitles).lower()

        for keyword in self.CLOSING_KEYWORDS:
            if keyword in full_text:
                start_idx = max(0, total_length - 3)

                # 희망 키워드 많으면 nature_bright, 아니면 nature_calm
                strategy = "nature_bright" if any(
                    word in full_text for word in ["은혜", "축복", "기쁨", "사랑"]
                ) else "nature_calm"

                return TemplateSection(
                    start_idx=start_idx,
                    end_idx=total_length - 1,
                    pattern_type="closing",
                    strategy=strategy,
                    confidence=0.85
                )

        return None

    def _find_transitions(self, subtitles: List[str]) -> List[TemplateSection]:
        """전환 구간 찾기 (문제 → 해결)"""
        sections = []

        for idx, subtitle in enumerate(subtitles):
            text = subtitle.lower()

            for keyword in self.TRANSITION_KEYWORDS:
                if keyword in text:
                    # 전환 키워드 이후 2-3개 자막은 희망 섹션
                    sections.append(TemplateSection(
                        start_idx=idx,
                        end_idx=min(idx + 2, len(subtitles) - 1),
                        pattern_type="solution",
                        strategy="nature_bright",
                        confidence=0.8
                    ))
                    logger.info(f"Transition pattern found at line {idx}: '{keyword}'")

        return sections

    def get_strategy_for_subtitle(
        self,
        subtitle_idx: int,
        sections: List[TemplateSection]
    ) -> Optional[str]:
        """
        특정 자막 인덱스에 고정 전략이 있는지 확인

        Args:
            subtitle_idx: 자막 인덱스
            sections: 템플릿 섹션 리스트

        Returns:
            고정 전략 (있으면), 없으면 None (빈도 분석 필요)
        """
        for section in sections:
            if section.start_idx <= subtitle_idx <= section.end_idx:
                return section.strategy

        return None  # 템플릿 매칭 없음 → 빈도 분석 사용


def get_template_analyzer() -> QTTemplateAnalyzer:
    """QTTemplateAnalyzer 싱글톤"""
    return QTTemplateAnalyzer()
