"""
템플릿 패턴 분석 테스트 스크립트

실제 QT 자막 예시로 템플릿 패턴 인식 검증
"""
# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.template_analyzer import get_template_analyzer

# 테스트 케이스: 전형적인 QT 구조
qt_typical = [
    "오늘 우리가 함께 묵상할 말씀은",          # 0: introduction
    "시편 23편입니다",                        # 1: scripture
    "여호와는 나의 목자시니",                 # 2: scripture
    "내게 부족함이 없으리로다",               # 3: (자유 구간)
    "우리는 때때로 두려움과 불안 속에서",     # 4: (자유 구간 - pain)
    "방황하고 좌절합니다",                    # 5: (자유 구간 - pain)
    "하지만 하나님께서는 말씀하십니다",       # 6: transition → solution
    "내가 너를 버리지 아니하리라",            # 7: solution (빈도 분석)
    "주님의 은혜가 우리와 함께하시길",        # 8: closing (bright)
    "기도합니다 아멘"                         # 9: closing
]

def test_template_analyzer():
    """템플릿 분석기 테스트"""
    analyzer = get_template_analyzer()

    print("=" * 60)
    print("템플릿 패턴 분석 테스트")
    print("=" * 60)

    # 템플릿 패턴 추출
    sections = analyzer.analyze(qt_typical)

    print(f"\n발견된 템플릿 섹션: {len(sections)}개")
    print("-" * 60)

    for section in sections:
        print(f"\n[{section.pattern_type.upper()}]")
        print(f"  위치: {section.start_idx}-{section.end_idx}번 자막")
        print(f"  전략: {section.strategy}")
        print(f"  확신도: {section.confidence:.1%}")
        print(f"  내용: {qt_typical[section.start_idx:section.end_idx+1]}")

    # 각 자막별 전략 확인
    print("\n" + "=" * 60)
    print("자막별 전략 매칭")
    print("=" * 60)

    for idx, subtitle in enumerate(qt_typical):
        strategy = analyzer.get_strategy_for_subtitle(idx, sections)
        status = f"[고정] {strategy}" if strategy else "[빈도분석]"
        print(f"{idx:2d}. {status:20s} | {subtitle}")

    print("\n" + "=" * 60)
    print("기대 결과 검증")
    print("=" * 60)

    expected = {
        0: "nature_calm",   # introduction
        1: "nature_calm",   # scripture
        2: "nature_calm",   # scripture
        4: None,            # pain (빈도 분석 필요)
        5: None,            # pain (빈도 분석 필요)
        6: "nature_bright", # transition
        7: "nature_bright", # solution
        8: "nature_bright", # closing
        9: "nature_bright"  # closing
    }

    all_pass = True
    for idx, expected_strategy in expected.items():
        actual_strategy = analyzer.get_strategy_for_subtitle(idx, sections)

        if expected_strategy is None:
            result = "[OK] 통과" if actual_strategy is None else "[FAIL] 실패"
            print(f"자막 {idx}: 빈도분석 필요 → {result}")
        else:
            result = "[OK] 통과" if actual_strategy == expected_strategy else f"[FAIL] 실패 (기대: {expected_strategy}, 실제: {actual_strategy})"
            print(f"자막 {idx}: {expected_strategy} → {result}")

        if "[FAIL]" in result:
            all_pass = False

    print("\n" + "=" * 60)
    if all_pass:
        print("전체 테스트 통과!")
    else:
        print("일부 테스트 실패 - 패턴 조정 필요")
    print("=" * 60)


if __name__ == "__main__":
    test_template_analyzer()
