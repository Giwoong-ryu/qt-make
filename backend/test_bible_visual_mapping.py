"""
성경 구절 기반 시각 묘사 생성 테스트

테스트 목적:
1. BIBLE_VISUAL_MAPPINGS 키워드 감지 확인
2. QT 특화 프롬프트 생성 키워드 품질 확인
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.visual_description_generator import (
    VisualDescriptionGenerator,
    BIBLE_VISUAL_MAPPINGS,
)


def test_bible_keyword_detection():
    """성경 키워드 감지 테스트"""
    print("=" * 60)
    print("📖 성경 키워드 감지 테스트")
    print("=" * 60)
    
    test_cases = [
        ("세례 요한은 광야에서 외쳤습니다", ["세례 요한", "광야"]),
        ("예수님의 은혜로 구원받았습니다", ["예수님", "은혜", "구원"]),
        ("헤롯왕이 분노했습니다", ["헤롯", "분노"]),
        ("좋은 아침입니다, 말씀으로", ["아침", "말씀"]),
        ("천국에서 영생을 누립니다", ["천국", "영생"]),
    ]
    
    generator = VisualDescriptionGenerator()
    
    for text, expected_keywords in test_cases:
        hints = generator._get_bible_visual_hints(text)
        print(f"\n입력: '{text}'")
        print(f"기대 키워드: {expected_keywords}")
        print(f"감지된 힌트: {hints[:80]}..." if hints else "감지된 힌트: None")
        
        # 검증
        if hints:
            found = sum(1 for kw in expected_keywords if kw in text)
            print(f"✅ {found}/{len(expected_keywords)} 키워드 감지")
        else:
            print("❌ 힌트 감지 실패")
    
    print(f"\n총 매핑 키워드 수: {len(BIBLE_VISUAL_MAPPINGS)}개")


def test_visual_description_generation():
    """시각 묘사 생성 테스트 (LLM 호출)"""
    print("\n" + "=" * 60)
    print("🎬 시각 묘사 생성 테스트 (LLM 호출)")
    print("=" * 60)
    
    test_subtitles = [
        ["말씀으로 좋은 아침입니다"],
        ["세례 요한은 광야에서", "외치는 소리로 전파했습니다"],
        ["헤로디아가 시기하고 미워했습니다"],
        ["예수님의 은혜로", "구원받은 우리"],
        ["오늘 잠깐 기도하면 어떨까요?"],
    ]
    
    generator = VisualDescriptionGenerator()
    
    for subtitles in test_subtitles:
        print(f"\n--- 자막: {' | '.join(subtitles)}")
        
        try:
            result = generator.generate_description(subtitles)
            
            print(f"  검색어: {result.visual_query}")
            print(f"  타입: {result.description_type} (신뢰도: {result.confidence:.2f})")
            if result.bible_hints:
                print(f"  성경힌트: {result.bible_hints[:60]}...")
            
            # 품질 검증
            if any(word in result.visual_query.lower() for word in 
                   ["nature", "light", "peaceful", "sunrise", "desert", "wilderness", "cross"]):
                print("  ✅ QT 관련 키워드 포함")
            else:
                print("  ⚠️ QT 키워드 확인 필요")
                
        except Exception as e:
            print(f"  ❌ 오류: {e}")


def print_mapping_summary():
    """매핑 테이블 요약"""
    print("\n" + "=" * 60)
    print("📊 BIBLE_VISUAL_MAPPINGS 요약")
    print("=" * 60)
    
    # 카테고리별 분류 (키워드 길이로 간접 추정)
    categories = {
        "인물": ["세례 요한", "예수님", "헤롯", "바울", "베드로", "다윗", "모세"],
        "장소": ["광야", "예루살렘", "갈릴리", "골고다", "성전"],
        "개념": ["죄", "은혜", "구원", "믿음", "사랑", "기도", "천국"],
        "감정": ["미움", "분노", "두려움", "슬픔", "기쁨"],
        "자연": ["빛", "물", "산", "바다", "비"],
    }
    
    for category, keywords in categories.items():
        present = [k for k in keywords if k in BIBLE_VISUAL_MAPPINGS]
        print(f"  {category}: {len(present)}/{len(keywords)} ({', '.join(present[:3])}...)")
    
    print(f"\n  총 키워드 수: {len(BIBLE_VISUAL_MAPPINGS)}개")


if __name__ == "__main__":
    print("\n🔬 VisualDescriptionGenerator QT/성경 특화 테스트\n")
    
    # 1. 매핑 테이블 요약
    print_mapping_summary()
    
    # 2. 키워드 감지 테스트 (오프라인)
    test_bible_keyword_detection()
    
    # 3. LLM 생성 테스트 (온라인 - API 호출)
    print("\n\n⚡ LLM 테스트를 실행하려면 GEMINI_API_KEY 환경변수가 필요합니다.")
    user_input = input("LLM 테스트를 실행하시겠습니까? (y/n): ").strip().lower()
    
    if user_input == 'y':
        test_visual_description_generation()
    else:
        print("LLM 테스트 건너뜀")
    
    print("\n✅ 테스트 완료")
