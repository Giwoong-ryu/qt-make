"""
하이브리드 분석 테스트 스크립트

템플릿 + 빈도 분석 결합 시스템 검증
"""
# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.hybrid_emotion_analyzer import get_hybrid_analyzer

# 테스트 케이스: 2분 QT (자막 + 타이밍)
qt_subtitles = [
    "오늘 우리가 함께 묵상할 말씀은",          # 0: 0-5초 (introduction)
    "시편 23편입니다",                        # 1: 5-10초 (scripture)
    "여호와는 나의 목자시니",                 # 2: 10-15초 (scripture)
    "내게 부족함이 없으리로다",               # 3: 15-20초
    "우리는 때때로",                          # 4: 20-30초
    "두려움과 불안 속에서 방황하고",          # 5: 30-40초 (pain - 섹션1)
    "좌절하고 낙담합니다",                    # 6: 40-50초 (pain)
    "외로움과 고독이",                        # 7: 50-60초 (pain)
    "우리를 짓누릅니다",                      # 8: 60-70초 (pain - 섹션2 시작)
    "하지만 하나님께서는 말씀하십니다",       # 9: 70-80초 (transition)
    "내가 너를 버리지 아니하리라",            # 10: 80-90초 (solution)
    "내가 너와 함께하리라",                   # 11: 90-100초 (solution - 섹션3)
    "주님의 은혜가 우리와 함께하시길",        # 12: 100-110초 (closing)
    "기도합니다 아멘"                         # 13: 110-120초 (closing)
]

qt_timings = [
    (0, 5), (5, 10), (10, 15), (15, 20),
    (20, 30), (30, 40), (40, 50), (50, 60),
    (60, 70), (70, 80), (80, 90), (90, 100),
    (100, 110), (110, 120)
]


def test_hybrid_analyzer():
    """하이브리드 분석기 테스트"""
    analyzer = get_hybrid_analyzer()

    print("=" * 80)
    print("하이브리드 감정 분석 테스트 (템플릿 + 빈도)")
    print("=" * 80)

    # 3분할 섹션 분석
    sections = analyzer.analyze_sections(
        subtitles=qt_subtitles,
        subtitle_timings=qt_timings,
        num_sections=3
    )

    print(f"\n총 {len(sections)}개 섹션 분석 완료")
    print("=" * 80)

    for idx, section in enumerate(sections, start=1):
        print(f"\n[섹션 {idx}] {section.start_time:.1f}-{section.end_time:.1f}초")
        print(f"  전략: {section.strategy}")
        print(f"  출처: {section.source} (확신도 {section.confidence:.0%})")

        # 이 섹션에 해당하는 자막 표시
        section_subs = [
            (i, sub) for i, (start, end) in enumerate(qt_timings)
            if not (end < section.start_time or start > section.end_time)
            for sub in [qt_subtitles[i]]
        ]

        print(f"  자막:")
        for sub_idx, sub_text in section_subs:
            print(f"    {sub_idx:2d}. {sub_text}")

    # 기대 결과 검증
    print("\n" + "=" * 80)
    print("기대 결과 검증")
    print("=" * 80)

    expected = [
        ("nature_calm", "template"),    # 섹션 1: 도입+성경 (템플릿)
        ("human", "frequency"),          # 섹션 2: 고통 강조 (빈도)
        ("nature_bright", "template")    # 섹션 3: 해결+마무리 (템플릿+빈도)
    ]

    all_pass = True
    for idx, (section, (exp_strategy, exp_source)) in enumerate(zip(sections, expected), start=1):
        strategy_match = section.strategy == exp_strategy
        source_match = section.source == exp_source

        if strategy_match and source_match:
            print(f"섹션 {idx}: [OK] 통과 ({exp_strategy}, {exp_source})")
        else:
            print(f"섹션 {idx}: [FAIL] 실패")
            print(f"  기대: {exp_strategy} (from {exp_source})")
            print(f"  실제: {section.strategy} (from {section.source})")
            all_pass = False

    print("\n" + "=" * 80)
    if all_pass:
        print("전체 테스트 통과!")
        print("템플릿 매칭 + 빈도 분석 하이브리드 시스템 정상 작동")
    else:
        print("일부 테스트 실패 - 로직 조정 필요")
    print("=" * 80)

    # 타임라인 시뮬레이션
    print("\n" + "=" * 80)
    print("예상 타임라인 (2분 QT 영상)")
    print("=" * 80)

    for idx, section in enumerate(sections, start=1):
        duration = section.end_time - section.start_time
        print(f"\n[{section.start_time:5.1f}s - {section.end_time:5.1f}s] "
              f"({duration:4.1f}초)")
        print(f"  전략: {section.strategy}")
        print(f"  출처: {section.source}")

        # 영상 종류 설명
        if section.strategy == "human":
            print(f"  영상: 후드 입은 인물 실루엣, 고개 숙인 자세")
        elif section.strategy == "nature_bright":
            print(f"  영상: 해 뜨는 장면, 빛이 비추는 자연")
        else:
            print(f"  영상: 차분한 산, 호수 풍경")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_hybrid_analyzer()
