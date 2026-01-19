"""
고정 구간 분석기 테스트 스크립트

처음 20초 (도입) + 마지막 20초 (마무리) 고정
중간 구간은 빈도 분석 (랜덤성 강함)
"""
# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.fixed_segment_analyzer import get_fixed_segment_analyzer

# 테스트 케이스: 2분 QT (자막 + 타이밍)
qt_subtitles = [
    "오늘 우리가 함께 묵상할 말씀은",          # 0: 0-5초 (도입)
    "시편 23편입니다",                        # 1: 5-10초 (성경)
    "여호와는 나의 목자시니",                 # 2: 10-15초 (성경)
    "내게 부족함이 없으리로다",               # 3: 15-20초
    "우리는 때때로",                          # 4: 20-30초
    "두려움과 불안 속에서 방황하고",          # 5: 30-40초 (pain)
    "좌절하고 낙담합니다",                    # 6: 40-50초 (pain)
    "외로움과 고독이",                        # 7: 50-60초 (pain)
    "우리를 짓누릅니다",                      # 8: 60-70초 (pain)
    "하지만 하나님께서는 말씀하십니다",       # 9: 70-80초 (transition)
    "내가 너를 버리지 아니하리라",            # 10: 80-90초 (solution)
    "내가 너와 함께하리라",                   # 11: 90-100초 (solution)
    "주님의 은혜가 우리와 함께하시길",        # 12: 100-110초 (closing)
    "기도합니다 아멘"                         # 13: 110-120초 (closing)
]

qt_timings = [
    (0, 5), (5, 10), (10, 15), (15, 20),
    (20, 30), (30, 40), (40, 50), (50, 60),
    (60, 70), (70, 80), (80, 90), (90, 100),
    (100, 110), (110, 120)
]


def test_fixed_segment_analyzer():
    """고정 구간 분석기 테스트"""
    analyzer = get_fixed_segment_analyzer()

    print("=" * 80)
    print("고정 구간 분석 테스트 (처음 20s + 마지막 20s 고정)")
    print("=" * 80)

    # 구간 분석
    segments = analyzer.analyze_segments(
        subtitles=qt_subtitles,
        subtitle_timings=qt_timings
    )

    print(f"\n총 {len(segments)}개 구간 분석 완료")
    print("=" * 80)

    total_duration = 0
    for idx, segment in enumerate(segments, start=1):
        duration = segment.end_time - segment.start_time
        total_duration += duration

        print(f"\n[구간 {idx}] {segment.start_time:.1f}-{segment.end_time:.1f}초 ({duration:.1f}초)")
        print(f"  타입: {segment.segment_type}")
        print(f"  전략: {segment.strategy}")
        print(f"  확신도: {segment.confidence:.0%}")

        # 이 구간에 해당하는 자막 표시
        section_subs = [
            (i, sub) for i, (start, end) in enumerate(qt_timings)
            if not (end < segment.start_time or start > segment.end_time)
            for sub in [qt_subtitles[i]]
        ]

        print(f"  자막:")
        for sub_idx, sub_text in section_subs:
            print(f"    {sub_idx:2d}. {sub_text}")

    print(f"\n총 영상 길이: {total_duration:.1f}초")

    # 기대 결과 검증
    print("\n" + "=" * 80)
    print("기대 결과 검증")
    print("=" * 80)

    # 구간 타입 확인
    segment_types = [s.segment_type for s in segments]
    has_fixed_intro = "fixed_intro" in segment_types
    has_fixed_closing = "fixed_closing" in segment_types
    has_flexible_middle = "flexible_middle" in segment_types

    print(f"도입 고정 구간: {'[OK] 있음' if has_fixed_intro else '[FAIL] 없음'}")
    print(f"마무리 고정 구간: {'[OK] 있음' if has_fixed_closing else '[FAIL] 없음'}")
    print(f"유연 중간 구간: {'[OK] 있음' if has_flexible_middle else '[FAIL] 없음'}")

    # 첫 구간과 마지막 구간 확인
    first_segment = segments[0]
    last_segment = segments[-1]

    print(f"\n첫 구간 (0-20초 기대):")
    print(f"  실제: {first_segment.start_time:.1f}-{first_segment.end_time:.1f}초")
    print(f"  전략: {first_segment.strategy} ({'[OK] 통과' if first_segment.strategy == 'nature_calm' else '[FAIL] 실패'})")

    print(f"\n마지막 구간 (100-120초 기대):")
    print(f"  실제: {last_segment.start_time:.1f}-{last_segment.end_time:.1f}초")
    print(f"  전략: {last_segment.strategy} ({'[OK] 통과' if last_segment.strategy in ['nature_bright', 'nature_calm'] else '[FAIL] 실패'})")

    # 타임라인 시뮬레이션
    print("\n" + "=" * 80)
    print("예상 타임라인 (2분 QT 영상)")
    print("=" * 80)

    for idx, segment in enumerate(segments, start=1):
        duration = segment.end_time - segment.start_time
        print(f"\n[{segment.start_time:5.1f}s - {segment.end_time:5.1f}s] ({duration:4.1f}초)")
        print(f"  타입: {segment.segment_type}")
        print(f"  전략: {segment.strategy}")

        # 영상 종류 설명
        if segment.strategy == "human":
            print(f"  영상: 후드 입은 인물 실루엣, 고개 숙인 자세 (고통 표현)")
        elif segment.strategy == "nature_bright":
            print(f"  영상: 해 뜨는 장면, 빛이 비추는 자연 (희망)")
        else:
            print(f"  영상: 차분한 산, 호수 풍경 (평안)")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_fixed_segment_analyzer()
