"""
Visual Description Generator (Stage 2: 감독 모드)

자막 텍스트를 영상 감독 관점의 시각적 묘사로 변환합니다.

핵심 원칙:
- 단어가 아니라 장면을 묘사한다
- 구체적인 사물보다 분위기 위주
- 사실 설명(Literal) vs 감정 묘사(Abstract) 자동 판단
"""
import logging
from dataclasses import dataclass
from typing import List

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class VisualDescription:
    """시각적 묘사 정보"""
    original_text: str  # 원본 한국어 자막
    visual_query: str   # Pexels 검색용 영어 묘사
    description_type: str  # "literal" 또는 "abstract"
    confidence: float  # 0.0-1.0


class VisualDescriptionGenerator:
    """
    LLM 감독: 자막을 영상 감독 관점의 시각적 묘사로 변환

    Example:
        자막: "헤로디아가 불편했습니다"

        ❌ 단순 번역: "Herodias uncomfortable"
        ✅ 감독 모드: "A woman looking anxious and jealous in an ancient palace,
                      shadowy lighting, tense atmosphere, cinematic style"

    Hybrid Search:
        - Literal (사실): "세례 요한" → "prophet in wilderness, ancient clothing"
        - Abstract (감정): "미움, 시기" → "dark red tones, storm, tension"
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

    def generate_description(
        self,
        subtitle_texts: List[str],
        context: str = "documentary"
    ) -> VisualDescription:
        """
        자막 텍스트를 시각적 묘사로 변환

        Args:
            subtitle_texts: 하나의 컷에 포함된 자막 리스트
                           ["산을 오르며", "기도합니다"]
            context: 영상 컨텍스트 (documentary, sermon, meditation, etc)

        Returns:
            시각적 묘사 정보
        """
        combined_text = " ".join(subtitle_texts)

        prompt = f'''
You are a video search specialist. Analyze the Korean subtitle text and generate **specific, concrete search keywords** for stock video (Pexels).

Critical Rules:
1. **IGNORE verse numbers** (e.g., "21절에서 34절")
2. **Focus on CONCRETE VISUAL ELEMENTS** that match the subtitle content
3. **Analyze the NARRATIVE FLOW**: What specific scene/action does this subtitle describe?
4. Output **SHORT, SPECIFIC KEYWORDS** (5-8 words max), NOT long sentences
5. **Prefer CONCRETE OBJECTS/ACTIONS** over abstract atmosphere descriptions

Content-Based Matching Strategy:
- Greeting/Morning → coffee cup, sunrise, morning ritual
- Biblical characters → middle eastern person, ancient robe, desert/wilderness
- Teaching/Preaching → religious figure teaching crowd, biblical scene
- Authority/Anger → ancient king, throne, palace, rage
- Negative emotions → back view person, dark clouds, stormy weather
- Physical actions → fist hitting table, hands gesturing
- Love/Positive → hands making heart shape, light, warmth
- Prayer → praying hands, black white, contemplation

Few-shot Examples (CRITICAL - Follow this pattern):
- "말씀으로 좋은 아침입니다" → "coffee cup sunrise morning peaceful"
- "세례 요한은 광야에 외치는 소리로" → "middle eastern man walking desert wilderness ancient robe"
- "설교하며 합당한 회개의 열매를" → "ancient religious figure teaching crowd biblical scene"
- "그 원한이 세례요한을 죽였습니다" → "ancient king angry palace throne authority rage"
- "원한, 미움, 시기" → "back view person angry dark stormy clouds"
- "그것을 우리가 품고있을때 남들을 죽일뿐만아니라" → "fist hitting table anger aggression slam"
- "미움이 아니라 사랑을" → "hands making heart shape love gesture fingers"
- "오늘 잠깐 기도하면 어떨까요?" → "praying hands black white contemplation prayer"

Korean subtitle: "{combined_text}"

Step 1: What is the MAIN SUBJECT/ACTION in this subtitle?
Step 2: Generate concrete search keywords (5-8 words, Pexels-optimized).

Output format (JSON):
{{
  "type": "literal" or "abstract",
  "description": "your search keywords here (SHORT!)",
  "confidence": 0.0-1.0
}}'''

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON 파싱 시도
            import json
            import re

            # JSON 블록 추출 (```json ... ``` 또는 { ... })
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # JSON 파싱 실패 → 전체 텍스트를 description으로 사용
                    logger.warning(f"[VisualDescGen] Failed to parse JSON, using raw text")
                    return VisualDescription(
                        original_text=combined_text,
                        visual_query=response_text,
                        description_type="abstract",
                        confidence=0.7
                    )

            parsed = json.loads(json_str)

            result = VisualDescription(
                original_text=combined_text,
                visual_query=parsed.get("description", response_text),
                description_type=parsed.get("type", "abstract"),
                confidence=float(parsed.get("confidence", 0.8))
            )

            logger.info(f"[VisualDescGen] 자막: '{combined_text[:50]}...' → 검색어: '{result.visual_query[:80]}...'")
            return result

        except Exception as e:
            logger.error(f"[VisualDescGen] Failed to generate description: {e}")

            # Fallback: 단순 영어 번역 (최악의 경우)
            fallback_query = self._fallback_translation(combined_text)
            return VisualDescription(
                original_text=combined_text,
                visual_query=fallback_query,
                description_type="unknown",
                confidence=0.3
            )

    def _fallback_translation(self, text: str) -> str:
        """
        LLM 실패 시 폴백: 단순 영어 번역 + 기본 시각 키워드 추가

        Args:
            text: 한국어 자막

        Returns:
            영어 검색 쿼리
        """
        # 간단한 키워드 추출 + 기본 시각 키워드
        fallback_keywords = [
            "peaceful", "serene", "nature", "cinematic",
            "slow motion", "golden hour", "calm"
        ]

        # 실제 환경에서는 간단한 번역 API 또는 사전 기반 변환 사용 가능
        # 여기서는 기본 키워드 조합으로 처리
        return f"{text} peaceful nature cinematic"

    def generate_batch(
        self,
        subtitle_groups: List[List[str]],
        context: str = "documentary"
    ) -> List[VisualDescription]:
        """
        여러 컷의 자막을 배치로 처리

        Args:
            subtitle_groups: 컷별 자막 리스트
                            [["산을 오르며", "기도합니다"], ["하나님께", "감사드립니다"]]
            context: 영상 컨텍스트

        Returns:
            시각적 묘사 리스트
        """
        descriptions = []

        for idx, subtitle_texts in enumerate(subtitle_groups):
            logger.info(f"[VisualDescGen] Processing cut {idx+1}/{len(subtitle_groups)}")

            desc = self.generate_description(subtitle_texts, context)
            descriptions.append(desc)

            logger.info(
                f"  Original: {desc.original_text}\n"
                f"  Visual Query: {desc.visual_query}\n"
                f"  Type: {desc.description_type} (confidence: {desc.confidence:.2f})"
            )

        return descriptions
