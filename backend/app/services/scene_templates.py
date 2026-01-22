"""
장면 템플릿 기반 쿼리 생성 (v1.5)

한국어 자막 키워드 → 영어 검색 쿼리팩 변환
보고서 기반 키워드 전략 적용
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SceneTemplate:
    """장면 템플릿 정의"""
    scene_type: str  # landscape, symbolic, human
    must_have: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)
    query_pack: Dict[str, str] = field(default_factory=dict)


# 한국어 키워드 → 장면 템플릿 매핑 (보고서 기반)
SCENE_TEMPLATES: Dict[str, SceneTemplate] = {
    # ===== 감정/상태 =====
    "회개": SceneTemplate(
        scene_type="symbolic",
        must_have=["kneeling", "praying", "solitary", "dim light"],
        avoid=["city", "crowd", "stage", "microphone"],
        query_pack={
            "core": "kneeling prayer silhouette alone",
            "mood": "solemn contemplative repentance",
            "symbol": "tearful prayer cross humility",
            "negative": "city office logo stage concert"
        }
    ),
    "기도": SceneTemplate(
        scene_type="symbolic",
        must_have=["praying hands", "kneeling", "worship"],
        avoid=["stage", "concert", "crowd"],
        query_pack={
            "core": "praying hands closeup candlelight",
            "mood": "reverent peaceful devotion",
            "symbol": "worship hands raised sunset",
            "negative": "stage concert microphone logo"
        }
    ),
    "묵상": SceneTemplate(
        scene_type="landscape",
        must_have=["peaceful", "nature", "quiet", "solitary"],
        avoid=["crowd", "city", "noise"],
        query_pack={
            "core": "peaceful nature morning solitary",
            "mood": "meditation contemplative reflection",
            "symbol": "bible open soft light",
            "negative": "crowd city office modern"
        }
    ),
    "사랑": SceneTemplate(
        scene_type="symbolic",
        must_have=["embrace", "silhouette", "warm light"],
        avoid=["kissing", "romantic", "intimate"],
        query_pack={
            "core": "loving embrace silhouette sunset",
            "mood": "warm tender compassion",
            "symbol": "holding hands heart light",
            "negative": "romantic kissing intimate city"
        }
    ),
    "고통": SceneTemplate(
        scene_type="human",
        must_have=["suffering", "silhouette", "dark", "alone"],
        avoid=["violence", "blood", "graphic"],
        query_pack={
            "core": "person suffering silhouette dark",
            "mood": "pain sorrow anguish loneliness",
            "symbol": "hooded figure shadow despair",
            "negative": "violence blood graphic city"
        }
    ),
    "희망": SceneTemplate(
        scene_type="landscape",
        must_have=["sunrise", "light", "golden", "rays"],
        avoid=["dark", "night", "shadow"],
        query_pack={
            "core": "sunrise golden hour mountain hope",
            "mood": "hopeful bright new beginning",
            "symbol": "light breaking clouds rays",
            "negative": "dark night shadow city"
        }
    ),
    "평안": SceneTemplate(
        scene_type="landscape",
        must_have=["calm", "peaceful", "water", "nature"],
        avoid=["turbulent", "storm", "crowd"],
        query_pack={
            "core": "calm lake mountain reflection",
            "mood": "peaceful serene tranquil",
            "symbol": "still water zen garden",
            "negative": "storm turbulent crowd city"
        }
    ),
    "감사": SceneTemplate(
        scene_type="symbolic",
        must_have=["hands", "light", "blessing"],
        avoid=["party", "celebration", "crowd"],
        query_pack={
            "core": "hands raised gratitude light",
            "mood": "thankful blessed joyful peaceful",
            "symbol": "sunrise blessing abundance harvest",
            "negative": "party celebration crowd modern"
        }
    ),
    
    # ===== 성경 장소/장면 =====
    "광야": SceneTemplate(
        scene_type="landscape",
        must_have=["desert", "wilderness", "barren", "vast"],
        avoid=["city", "highway", "car", "building"],
        query_pack={
            "core": "desert wilderness barren land",
            "mood": "vast empty solitary horizon",
            "symbol": "walking desert silhouette journey",
            "negative": "city highway road car building"
        }
    ),
    "갈릴리": SceneTemplate(
        scene_type="landscape",
        must_have=["sea", "lake", "boat", "fishing"],
        avoid=["modern", "yacht", "speedboat"],
        query_pack={
            "core": "sea of galilee sunrise lake",
            "mood": "peaceful morning mist water",
            "symbol": "wooden boat fishing ancient",
            "negative": "modern yacht speedboat city"
        }
    ),
    "예루살렘": SceneTemplate(
        scene_type="landscape",
        must_have=["ancient", "walls", "stone", "temple"],
        avoid=["modern", "tourist", "crowd"],
        query_pack={
            "core": "jerusalem ancient walls stone",
            "mood": "holy sacred reverent ancient",
            "symbol": "temple dome sunrise holy",
            "negative": "modern tourist crowd bus"
        }
    ),
    "십자가": SceneTemplate(
        scene_type="symbolic",
        must_have=["cross", "silhouette", "sacrifice"],
        avoid=["graphic", "blood", "violence"],
        query_pack={
            "core": "cross silhouette sunset hope",
            "mood": "solemn sacrifice redemption",
            "symbol": "wooden cross hill calvary",
            "negative": "graphic blood violence modern"
        }
    ),
    
    # ===== 추상 개념 =====
    "은혜": SceneTemplate(
        scene_type="landscape",
        must_have=["light", "rays", "blessing", "beauty"],
        avoid=["dark", "gloomy", "harsh"],
        query_pack={
            "core": "light rays blessing nature",
            "mood": "graceful beautiful divine",
            "symbol": "golden light stream forest",
            "negative": "dark gloomy harsh city"
        }
    ),
    "믿음": SceneTemplate(
        scene_type="symbolic",
        must_have=["trust", "journey", "path", "walking"],
        avoid=["doubt", "fear", "darkness"],
        query_pack={
            "core": "path journey walking forward",
            "mood": "trusting confident hopeful",
            "symbol": "footpath mountain climbing ascending",
            "negative": "doubt fear darkness lost"
        }
    ),
    "순종": SceneTemplate(
        scene_type="human",
        must_have=["kneeling", "humble", "surrendered"],
        avoid=["rebellion", "defiance", "proud"],
        query_pack={
            "core": "kneeling humble surrendered silhouette",
            "mood": "obedient willing submitted",
            "symbol": "bowing head prayer submission",
            "negative": "rebellion defiance proud modern"
        }
    ),
    "성령": SceneTemplate(
        scene_type="symbolic",
        must_have=["dove", "fire", "wind", "breath"],
        avoid=["dark", "evil", "demonic"],
        query_pack={
            "core": "dove flying light spirit",
            "mood": "ethereal holy divine presence",
            "symbol": "fire flame pentecost wind",
            "negative": "dark evil demonic city"
        }
    ),
}


def get_template_for_keyword(keyword: str) -> Optional[SceneTemplate]:
    """
    한국어 키워드에 맞는 장면 템플릿 반환
    
    Args:
        keyword: 한국어 키워드 (예: "회개", "광야")
        
    Returns:
        SceneTemplate 또는 None
    """
    return SCENE_TEMPLATES.get(keyword)


def get_query_pack_for_keyword(keyword: str) -> Optional[Dict[str, str]]:
    """
    한국어 키워드에 맞는 쿼리팩 반환
    
    Args:
        keyword: 한국어 키워드
        
    Returns:
        쿼리팩 딕셔너리 또는 None
    """
    template = get_template_for_keyword(keyword)
    return template.query_pack if template else None


def find_matching_keywords(text: str) -> List[str]:
    """
    텍스트에서 매칭되는 키워드 찾기
    
    Args:
        text: 자막 텍스트
        
    Returns:
        매칭된 키워드 리스트 (우선순위순)
    """
    matched = []
    for keyword in SCENE_TEMPLATES.keys():
        if keyword in text:
            matched.append(keyword)
    return matched


def get_best_query_for_text(text: str) -> str:
    """
    자막 텍스트에 가장 적합한 검색 쿼리 반환
    
    Args:
        text: 자막 텍스트
        
    Returns:
        영어 검색 쿼리
    """
    keywords = find_matching_keywords(text)
    
    if not keywords:
        logger.debug(f"No template match for: {text[:30]}...")
        return "peaceful nature landscape"  # 기본 폴백
    
    # 첫 번째 매칭 키워드의 core 쿼리 반환
    template = SCENE_TEMPLATES[keywords[0]]
    return template.query_pack.get("core", "peaceful nature")


class SceneTemplateService:
    """장면 템플릿 서비스"""
    
    def __init__(self):
        self.templates = SCENE_TEMPLATES
    
    def analyze_subtitle(self, subtitle_text: str) -> Dict:
        """
        자막 텍스트 분석 → 장면 정보 반환
        
        Args:
            subtitle_text: 자막 텍스트
            
        Returns:
            {
                "matched_keywords": [...],
                "scene_type": "landscape" | "symbolic" | "human",
                "query_pack": {...},
                "negative": "..."
            }
        """
        keywords = find_matching_keywords(subtitle_text)
        
        if not keywords:
            return {
                "matched_keywords": [],
                "scene_type": "landscape",
                "query_pack": {
                    "core": "peaceful nature landscape",
                    "mood": "calm serene",
                    "negative": "city car building"
                },
                "negative": "city car building office"
            }
        
        template = self.templates[keywords[0]]
        return {
            "matched_keywords": keywords,
            "scene_type": template.scene_type,
            "query_pack": template.query_pack,
            "negative": template.query_pack.get("negative", "")
        }


# 싱글톤
_scene_template_service = None

def get_scene_template_service() -> SceneTemplateService:
    """SceneTemplateService 싱글톤"""
    global _scene_template_service
    if _scene_template_service is None:
        _scene_template_service = SceneTemplateService()
    return _scene_template_service
