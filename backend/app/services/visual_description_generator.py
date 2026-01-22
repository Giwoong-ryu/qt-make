"""
Visual Description Generator (Stage 2: 감독 모드) - QT/성경 특화 버전

자막 텍스트를 영상 감독 관점의 시각적 묘사로 변환합니다.

핵심 원칙:
- 성경 콘텐츠에 맞는 명상적/경건한 분위기
- 얼굴이 나오지 않는 자연/추상 영상 위주
- 성경 고유명사 → 적절한 시각 키워드 매핑
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Option B: 성경 키워드 매핑 테이블
# =============================================================================
BIBLE_VISUAL_MAPPINGS = {
    # -------------------------------------------------------------------------
    # 성경 인물 (Biblical Figures)
    # -------------------------------------------------------------------------
    "세례 요한": "wilderness prophet desert ancient biblical landscape dramatic sky",
    "요한": "wilderness ancient biblical landscape serene",
    "예수님": "light rays divine peaceful cross sunrise hope redemption",
    "예수": "light rays divine peaceful sunrise hope",
    "그리스도": "cross light divine sunrise redemption hope",
    "헤롯": "palace throne ancient power dramatic shadows authority",
    "헤로디아": "palace shadows tension ancient drama jealousy",
    "바울": "ancient city journey road travel ruins mediterranean",
    "베드로": "fishing boat sea water ancient disciple",
    "다윗": "shepherd hills ancient worship crown kingdom",
    "모세": "desert mountain wilderness ancient tablets law",
    "아브라함": "desert stars night ancient promise journey",
    "야곱": "ladder sky stars dream ancient journey",
    "요셉": "wheat field harvest ancient coat colorful",
    "사무엘": "temple ancient oil lamp worship night",
    "솔로몬": "temple gold wealth ancient wisdom throne",
    "엘리야": "mountain fire sky ancient prophet wilderness",
    "이사야": "scroll ancient prophet light hope vision",
    "다니엘": "lions ancient palace faith night stars",
    
    # -------------------------------------------------------------------------
    # 성경 장소 (Biblical Places)
    # -------------------------------------------------------------------------
    "광야": "desert wilderness barren landscape dramatic sky solitude",
    "예루살렘": "ancient city sunrise golden light temple walls",
    "갈릴리": "calm lake water reflection peaceful fishing boat",
    "겟세마네": "olive trees garden night prayer contemplation",
    "골고다": "cross hill dramatic sky sunrise redemption",
    "갈보리": "cross hill light rays sunrise hope sacrifice",
    "이집트": "desert pyramids ancient journey exodus sand",
    "바벨론": "ancient city river ruins tower dramatic",
    "시내산": "mountain desert wilderness tablets ancient dramatic",
    "요단강": "river water crossing ancient baptism peaceful",
    "베들레헴": "village night stars ancient manger humble",
    "나사렛": "village hills ancient peaceful humble",
    "성전": "temple ancient worship light gold sacred",
    "회당": "ancient scroll worship community gathering",
    
    # -------------------------------------------------------------------------
    # 성경 개념/신학 (Biblical Concepts)
    # -------------------------------------------------------------------------
    "죄": "dark shadows storm contemplation solitude rain chains",
    "은혜": "light rays soft golden peaceful hope sunrise waterfall",
    "용서": "light breaking through clouds embrace peaceful hope dawn",
    "회개": "rain tears cleansing renewal dawn light hope",
    "구원": "sunrise breakthrough light hope liberation cross rays",
    "부활": "sunrise empty tomb light rays hope new dawn",
    "성령": "dove wind flames light peaceful descending",
    "믿음": "mountain solid rock anchor light steadfast",
    "소망": "sunrise horizon light rays hope anchor",
    "사랑": "heart hands embrace warmth light gentle",
    "축복": "light rays golden abundance peaceful joy",
    "기도": "praying hands candle quiet contemplation worship",
    "찬양": "sunrise hands raised worship light joy",
    "감사": "harvest abundance light golden thankful peaceful",
    "평화": "calm water sunset peaceful serene tranquil",
    "기쁨": "sunrise light dancing celebration nature joy",
    "고난": "storm dark clouds rain trial path rocky",
    "시험": "desert wilderness barren dry trial solitude",
    "승리": "mountain peak sunrise light triumph rays",
    "영생": "eternal light stars cosmos peaceful serene",
    "천국": "clouds golden light ethereal heavenly peaceful paradise",
    "하나님나라": "light clouds golden glorious peaceful kingdom",
    "심판": "storm lightning dramatic sky thunder clouds",
    "말씀": "scroll book light wisdom ancient sacred",
    "진리": "light path clear mountain peak wisdom",
    "지혜": "ancient scroll light path wisdom peaceful",
    
    # -------------------------------------------------------------------------
    # 감정/분위기 (Emotions/Moods)
    # -------------------------------------------------------------------------
    "미움": "dark storm clouds rain anger shadows",
    "시기": "shadows dark jealousy storm clouds tension",
    "원한": "dark chains storm anger shadows dramatic",
    "분노": "storm fire flames clouds dark anger",
    "두려움": "dark shadows night fear storm alone",
    "외로움": "solitude alone desert path shadows quiet",
    "슬픔": "rain tears grey clouds weeping solitude",
    "절망": "dark pit shadows chains night alone",
    "소외": "alone distant shadows solitude path single",
    
    # -------------------------------------------------------------------------
    # 일상/인사 (Daily Life/Greetings)
    # -------------------------------------------------------------------------
    "아침": "sunrise coffee cup morning peaceful devotion light",
    "좋은아침": "sunrise coffee morning peaceful devotion warm",
    "저녁": "sunset evening peaceful calm reflection twilight",
    "밤": "night stars quiet contemplation peaceful moon",
    "오늘": "sunrise new day light hope morning fresh",
    "내일": "sunrise horizon hope new dawn light",
    
    # -------------------------------------------------------------------------
    # 자연 상징 (Nature Symbols)
    # -------------------------------------------------------------------------
    "빛": "light rays sunrise golden hope divine",
    "어둠": "darkness shadows night storm clouds",
    "물": "water river flowing peaceful cleansing serene",
    "불": "fire flames light warmth holy spirit",
    "바람": "wind clouds moving grass field spirit",
    "산": "mountain peak majestic peaceful solid",
    "바다": "ocean waves vast peaceful horizon",
    "강": "river flowing peaceful journey serene",
    "하늘": "sky clouds vast peaceful blue serene",
    "별": "stars night cosmos peaceful eternal",
    "비": "rain cleansing renewal fresh nature",
    "폭풍": "storm dramatic clouds lightning powerful",
}


@dataclass
class VisualDescription:
    """시각적 묘사 정보"""
    original_text: str  # 원본 한국어 자막
    visual_query: str   # Pexels 검색용 영어 묘사
    description_type: str  # "literal" 또는 "abstract"
    confidence: float  # 0.0-1.0
    bible_hints: Optional[str] = None  # 성경 키워드 힌트 (있으면)


class VisualDescriptionGenerator:
    """
    LLM 감독: 자막을 QT/성경 명상 영상 검색 키워드로 변환

    QT (Quiet Time) 특화:
        - 성경 구절에 어울리는 명상적 배경 영상
        - 얼굴 없는 자연/추상 영상 위주
        - 성경 고유명사 → 적절한 시각 키워드 매핑

    Example:
        자막: "세례 요한은 광야에서 외쳤습니다"

        ❌ 일반: "middle eastern man speaking desert"
        ✅ QT: "wilderness desert ancient biblical dramatic sky solitude"
    """

    def __init__(self, gemini_api_key: str = None, allow_people: bool = False):
        """
        초기화

        Args:
            gemini_api_key: Gemini API 키
            allow_people: True면 인물 포함 가능 (Biblical 모드), False면 자연만 (기본)
        """
        self.api_key = gemini_api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.allow_people = allow_people
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def _get_bible_visual_hints(self, text: str) -> Optional[str]:
        """
        자막에서 성경 고유명사를 감지하고 시각 힌트 반환

        Args:
            text: 한국어 자막 텍스트

        Returns:
            매핑된 시각 키워드 또는 None
        """
        hints = []
        
        # 긴 키워드부터 매칭 (예: "세례 요한"이 "요한"보다 먼저)
        sorted_keywords = sorted(BIBLE_VISUAL_MAPPINGS.keys(), key=len, reverse=True)
        
        for keyword in sorted_keywords:
            # 공백 제거 버전도 체크 (예: "좋은아침" vs "좋은 아침")
            keyword_no_space = keyword.replace(" ", "")
            text_no_space = text.replace(" ", "")
            
            if keyword in text or keyword_no_space in text_no_space:
                hints.append(BIBLE_VISUAL_MAPPINGS[keyword])
                logger.debug(f"[BibleHint] Found '{keyword}' → '{BIBLE_VISUAL_MAPPINGS[keyword][:50]}...'")
        
        if hints:
            # 중복 제거 후 합치기
            combined = " ".join(hints)
            unique_words = list(dict.fromkeys(combined.split()))
            return " ".join(unique_words[:12])  # 최대 12개 키워드
        
        return None

    def generate_description(
        self,
        subtitle_texts: List[str],
        context: str = "qt_devotion"
    ) -> VisualDescription:
        """
        자막 텍스트를 QT 명상 영상 검색 키워드로 변환

        Args:
            subtitle_texts: 하나의 컷에 포함된 자막 리스트
            context: 영상 컨텍스트 (qt_devotion, sermon, meditation)

        Returns:
            시각적 묘사 정보
        """
        combined_text = " ".join(subtitle_texts)
        
        # Step 1: 성경 키워드 힌트 추출
        bible_hints = self._get_bible_visual_hints(combined_text)
        if bible_hints:
            logger.info(f"[VisualDescGen] Bible hints found: {bible_hints[:60]}...")

        # Step 2: QT 특화 프롬프트
        prompt = f'''You are a **Christian QT (Quiet Time) video specialist**. Generate Pexels search keywords for meditation/devotional background videos.

**CRITICAL CONTEXT**: This is for Korean church QT videos - devotional content based on Bible verses.

**STRICT RULES**:
1. Output 5-8 keywords ONLY (not sentences)
2. Focus on {'NATURE and ATMOSPHERIC imagery' if not self.allow_people else 'BIBLICAL SCENES with people when appropriate'}
3. {'NEVER include human faces or specific people' if not self.allow_people else 'Include people, biblical characters, worship scenes when relevant'}
4. Match the EMOTIONAL/SPIRITUAL TONE, not literal illustrations
5. Prefer: {'landscapes, light effects, weather, abstract nature' if not self.allow_people else 'biblical scenes, worship, prayer, people in devotion, nature'}

**Content Matching Strategy**:

1. 성경 인물/사건 (Biblical references):
   - 세례요한, 광야, 선지자 → `wilderness desert ancient ruins dramatic sky`
   - 예수님, 십자가 → `cross silhouette light rays sunrise hope redemption`
   - 천국, 하나님나라 → `clouds golden light ethereal heavenly peaceful`
   - 죄, 회개 → `rain dark storm contemplation cleansing renewal`

2. 감정 톤 (Emotional tone):
   - 희망/기쁨 → `sunrise golden hour light rays nature hope`
   - 슬픔/회개 → `rain clouds moody contemplation solitude`
   - 평화/안식 → `calm water lake reflection serene quiet`
   - 경고/심판 → `storm lightning dramatic sky intense clouds`

3. 인사/마무리 (Opening/Closing):
   - 아침 인사 → `sunrise coffee cup peaceful morning devotion`
   - 기도 권유 → `praying hands candle contemplation worship`

{f"**BIBLE CONTEXT HINTS**: {bible_hints}" if bible_hints else ""}

**Korean subtitle**: "{combined_text}"

Output (JSON only):
{{
  "type": "literal" or "abstract",
  "description": "your 5-8 keywords",
  "confidence": 0.0-1.0
}}'''

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON 파싱
            import json
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # JSON 실패 → Bible hints 사용 또는 fallback
                    logger.warning(f"[VisualDescGen] JSON parse failed")
                    fallback_query = bible_hints if bible_hints else self._fallback_translation(combined_text)
                    return VisualDescription(
                        original_text=combined_text,
                        visual_query=fallback_query,
                        description_type="abstract",
                        confidence=0.6 if bible_hints else 0.4,
                        bible_hints=bible_hints
                    )

            parsed = json.loads(json_str)
            visual_query = parsed.get("description", "")
            
            # Bible hints가 있고 LLM 결과에 없으면 추가
            if bible_hints and visual_query:
                # 핵심 키워드만 추가 (중복 제거)
                llm_words = set(visual_query.lower().split())
                hint_words = bible_hints.lower().split()[:4]  # 상위 4개만
                new_words = [w for w in hint_words if w not in llm_words]
                if new_words:
                    visual_query = f"{visual_query} {' '.join(new_words)}"

            result = VisualDescription(
                original_text=combined_text,
                visual_query=visual_query or (bible_hints if bible_hints else "peaceful nature"),
                description_type=parsed.get("type", "abstract"),
                confidence=float(parsed.get("confidence", 0.8)),
                bible_hints=bible_hints
            )

            logger.info(
                f"[VisualDescGen] 자막: '{combined_text[:40]}...' → "
                f"검색어: '{result.visual_query[:60]}...'"
            )
            return result

        except Exception as e:
            logger.error(f"[VisualDescGen] Failed: {e}")
            fallback_query = bible_hints if bible_hints else self._fallback_translation(combined_text)
            return VisualDescription(
                original_text=combined_text,
                visual_query=fallback_query,
                description_type="unknown",
                confidence=0.3,
                bible_hints=bible_hints
            )

    def _fallback_translation(self, text: str) -> str:
        """
        LLM 실패 시 폴백: 기본 QT 시각 키워드

        Args:
            text: 한국어 자막

        Returns:
            영어 검색 쿼리
        """
        return "peaceful nature sunrise meditation contemplation serene"

    def generate_batch(
        self,
        subtitle_groups: List[List[str]],
        context: str = "qt_devotion"
    ) -> List[VisualDescription]:
        """
        여러 컷의 자막을 배치로 처리

        Args:
            subtitle_groups: 컷별 자막 리스트
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
                f"  원본: {desc.original_text[:50]}...\n"
                f"  검색어: {desc.visual_query}\n"
                f"  타입: {desc.description_type} (conf: {desc.confidence:.2f})"
                + (f"\n  성경힌트: {desc.bible_hints[:40]}..." if desc.bible_hints else "")
            )

        return descriptions
