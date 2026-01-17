"""
STT 교정 서비스
Gemini 2.5 Flash를 활용한 자막 교정
"""
import logging
import json
import re
from typing import Any

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class STTCorrectionService:
    """Gemini 기반 STT 교정 서비스"""

    # 모델 설정
    DEFAULT_MODEL = "gemini-2.5-flash"      # 기본 (저비용)
    QUALITY_MODEL = "gemini-3-flash-preview"  # 품질 모드 (고정밀)

    def __init__(self):
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(self.DEFAULT_MODEL)
            self.quality_model = genai.GenerativeModel(self.QUALITY_MODEL)
        else:
            logger.warning("GOOGLE_API_KEY not set. STT correction disabled.")
            self.model = None
            self.quality_model = None

    async def correct_subtitles(
        self,
        subtitles: list[dict],
        church_dictionary: list[dict] | None = None,
        context_words: list[str] | None = None,
        quality_mode: bool = False
    ) -> list[dict]:
        """
        자막 전체를 컨텍스트 기반으로 교정

        Args:
            subtitles: 자막 리스트 [{"index": 1, "start": 0.0, "end": 3.0, "text": "..."}]
            church_dictionary: 교회 사전 [{"wrong_text": "...", "correct_text": "..."}]
            context_words: 추가 컨텍스트 단어 (교회명, 담임목사명 등)
            quality_mode: True면 Gemini 2.5 Pro 사용

        Returns:
            교정된 자막 리스트 (corrections 필드 추가)
        """
        if not self.model:
            logger.warning("Gemini model not initialized. Returning original subtitles.")
            return subtitles

        if not subtitles:
            return subtitles

        try:
            # 1. 전체 텍스트로 컨텍스트 파악
            full_text = " ".join([s.get("text", "") for s in subtitles])

            # 2. 교정 프롬프트 생성
            prompt = self._build_correction_prompt(
                subtitles=subtitles,
                church_dictionary=church_dictionary,
                context_words=context_words,
                full_context=full_text
            )

            # 3. Gemini API 호출
            model = self.quality_model if quality_mode else self.model
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # 낮은 온도 = 일관성
                    max_output_tokens=4096
                )
            )

            # 4. 응답 파싱
            corrected = self._parse_correction_response(response.text, subtitles)

            return corrected

        except Exception as e:
            logger.exception(f"STT correction failed: {e}")
            return subtitles

    def _build_correction_prompt(
        self,
        subtitles: list[dict],
        church_dictionary: list[dict] | None,
        context_words: list[str] | None,
        full_context: str
    ) -> str:
        """교정 프롬프트 생성"""

        # 사전 정보 포맷팅
        dict_section = ""
        if church_dictionary:
            dict_items = [f"- {d['wrong_text']} -> {d['correct_text']}"
                          for d in church_dictionary[:30]]  # 최대 30개
            dict_section = f"""
## 교회 사전 (잘못 인식되는 패턴)
{chr(10).join(dict_items)}
"""

        # 컨텍스트 단어
        context_section = ""
        if context_words:
            context_section = f"""
## 추가 컨텍스트
- 관련 단어: {', '.join(context_words)}
"""

        # 자막 데이터 포맷팅
        subtitle_lines = []
        for s in subtitles:
            subtitle_lines.append(f"{s.get('index', 0)}|{s.get('text', '')}")

        prompt = f"""당신은 한국어 자막 교정 전문가입니다.
교회 설교/묵상 영상의 자막을 교정합니다.

## 작업
아래 자막에서 음성 인식 오류를 찾아 교정하세요.

## 규칙
1. 문맥을 파악하여 자연스러운 한국어로 교정
2. 교회/성경 용어는 정확하게 교정 (예: "예수그리스도", "하나님", "말씀")
3. 인명, 지명은 사전 정보를 참고
4. 확실한 오류만 교정하고, 애매한 것은 원본 유지
5. 띄어쓰기, 맞춤법 오류도 교정

## 전체 맥락
{full_context[:500]}...
{dict_section}
{context_section}
## 자막 데이터 (인덱스|텍스트)
{chr(10).join(subtitle_lines)}

## 출력 형식 (JSON)
교정이 필요한 자막만 출력하세요:
```json
[
  {{"index": 1, "original": "원본 텍스트", "corrected": "교정된 텍스트", "confidence": 0.9}},
  ...
]
```

교정할 내용이 없으면 빈 배열 `[]`을 출력하세요.
"""
        return prompt

    def _parse_correction_response(
        self,
        response_text: str,
        original_subtitles: list[dict]
    ) -> list[dict]:
        """Gemini 응답 파싱 및 자막에 적용"""

        try:
            # JSON 블록 추출
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSON 블록 없으면 전체 텍스트에서 배열 찾기
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return original_subtitles

            corrections = json.loads(json_str)

            if not corrections:
                return original_subtitles

            # 교정 사항을 인덱스 기반 딕셔너리로 변환
            correction_map = {c['index']: c for c in corrections}

            # 원본 자막에 교정 적용
            result = []
            for subtitle in original_subtitles:
                idx = subtitle.get('index', 0)
                new_subtitle = subtitle.copy()

                if idx in correction_map:
                    correction = correction_map[idx]
                    new_subtitle['text'] = correction['corrected']
                    new_subtitle['correction'] = {
                        'original': correction['original'],
                        'corrected': correction['corrected'],
                        'confidence': correction.get('confidence', 0.8),
                        'source': 'ai'
                    }

                result.append(new_subtitle)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse correction response: {e}")
            return original_subtitles
        except Exception as e:
            logger.exception(f"Error applying corrections: {e}")
            return original_subtitles

    def apply_dictionary(
        self,
        text: str,
        church_dictionary: list[dict]
    ) -> tuple[str, list[dict]]:
        """
        사전 기반 단순 치환 (AI 호출 없이)

        Args:
            text: 원본 텍스트
            church_dictionary: 교회 사전

        Returns:
            (교정된 텍스트, 적용된 교정 목록)
        """
        corrected_text = text
        applied_corrections = []

        # 빈도 높은 순으로 정렬 (긴 패턴 우선)
        sorted_dict = sorted(
            church_dictionary,
            key=lambda x: (-x.get('frequency', 0), -len(x.get('wrong_text', '')))
        )

        for entry in sorted_dict:
            wrong = entry.get('wrong_text', '')
            correct = entry.get('correct_text', '')

            if wrong and wrong in corrected_text:
                corrected_text = corrected_text.replace(wrong, correct)
                applied_corrections.append({
                    'wrong_text': wrong,
                    'correct_text': correct,
                    'source': 'dictionary'
                })

        return corrected_text, applied_corrections

    def apply_replacement_dictionary(
        self,
        text: str,
        replacement_dictionary: list[dict]
    ) -> tuple[str, list[dict]]:
        """
        자동 치환 사전 기반 교정 (original/replacement 형식)

        자막 수정 시 자동 저장된 치환 사전을 적용합니다.

        Args:
            text: 원본 텍스트
            replacement_dictionary: 치환 사전 [{"original": "...", "replacement": "...", "use_count": N}]

        Returns:
            (교정된 텍스트, 적용된 교정 목록)
        """
        corrected_text = text
        applied_corrections = []

        # use_count 높은 순으로 정렬 (긴 패턴 우선)
        sorted_dict = sorted(
            replacement_dictionary,
            key=lambda x: (-x.get('use_count', 0), -len(x.get('original', '')))
        )

        for entry in sorted_dict:
            original = entry.get('original', '')
            replacement = entry.get('replacement', '')

            if original and original in corrected_text:
                corrected_text = corrected_text.replace(original, replacement)
                applied_corrections.append({
                    'original': original,
                    'replacement': replacement,
                    'source': 'replacement_dictionary'
                })

        return corrected_text, applied_corrections

    def apply_replacement_to_subtitles(
        self,
        subtitles: list[dict],
        replacement_dictionary: list[dict]
    ) -> list[dict]:
        """
        자막 리스트에 치환 사전 적용

        Args:
            subtitles: 자막 리스트 [{"index": 1, "text": "..."}]
            replacement_dictionary: 치환 사전

        Returns:
            교정된 자막 리스트
        """
        if not replacement_dictionary:
            return subtitles

        result = []
        for subtitle in subtitles:
            new_subtitle = subtitle.copy()
            original_text = subtitle.get('text', '')

            corrected_text, corrections = self.apply_replacement_dictionary(
                original_text, replacement_dictionary
            )

            if corrected_text != original_text:
                new_subtitle['text'] = corrected_text
                new_subtitle['auto_corrections'] = corrections

            result.append(new_subtitle)

        return result


# 싱글톤
_correction_service: STTCorrectionService | None = None


def get_correction_service() -> STTCorrectionService:
    """STTCorrectionService 싱글톤"""
    global _correction_service
    if _correction_service is None:
        _correction_service = STTCorrectionService()
    return _correction_service
