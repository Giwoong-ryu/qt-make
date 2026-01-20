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
You are a {context} film director. Your task is to translate Korean subtitle text into **visual imagery descriptions** suitable for stock video search (Pexels, Shutterstock).

Critical Rules:
1. **Focus on ATMOSPHERE, MOOD, COLOR TONE**, not literal objects.
2. **Describe what the scene would LOOK LIKE**, not what it MEANS.
3. Use **cinematic language**: "shadowy lighting", "golden hour", "slow motion", "cinematic style", "serene atmosphere".
4. Output in **English**, 1-2 sentences, optimized for video search.

Hybrid Strategy:
- If text contains **factual/literal content** (names, places, objects):
  → Describe the SETTING/CONTEXT (e.g., "John the Baptist" → "prophet in wilderness wearing ancient robes")
- If text contains **emotional/abstract content** (anger, sadness, hope):
  → Describe VISUAL METAPHORS (e.g., "hatred" → "dark stormy sky with red tones, tension, aggressive atmosphere")

Examples:
- "헤로디아가 불편했습니다" → "A woman looking anxious and jealous in an ancient palace, shadowy lighting, tense atmosphere, cinematic style"
- "원한은 독과 같습니다" → "Dark smoke spreading in black background, silhouette of person in pain, ominous atmosphere, slow motion"
- "세례 요한이 광야에서" → "Prophet figure in desert wilderness, ancient clothing, golden sunset light, cinematic wide shot"
- "산을 오르며 기도합니다" → "Person climbing mountain path with hands in prayer, peaceful sunrise, serene nature, inspirational atmosphere"

Korean subtitle: "{combined_text}"

Step 1: Analyze if this is LITERAL (factual) or ABSTRACT (emotional).
Step 2: Generate visual description in English.

Output format (JSON):
{{
  "type": "literal" or "abstract",
  "description": "your visual description here",
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

            return VisualDescription(
                original_text=combined_text,
                visual_query=parsed.get("description", response_text),
                description_type=parsed.get("type", "abstract"),
                confidence=float(parsed.get("confidence", 0.8))
            )

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
