"""
영상 클립 선택기 테스트 스크립트

도입/중간: 긴 영상 (25초+) → trim
마무리: 정확한 길이 (20-30초) → trim 안 함
"""
# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.fixed_segment_analyzer import (
    get_fixed_segment_analyzer,
    SegmentStrategy
)
from app.services.video_clip_selector import get_clip_selector


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


def test_video_clip_selector():
    """영상 클립 선택기 테스트"""
    print("=" * 80)
    print("영상 클립 선택기 테스트")
    print("=" * 80)

    # Step 1: 구간 분석
    print("\n[Step 1] 구간 분석")
    print("-" * 80)
    segment_analyzer = get_fixed_segment_analyzer()
    segments = segment_analyzer.analyze_segments(
        subtitles=qt_subtitles,
        subtitle_timings=qt_timings
    )

    print(f"총 {len(segments)}개 구간 분석 완료")
    for idx, segment in enumerate(segments, start=1):
        duration = segment.end_time - segment.start_time
        print(f"  [{idx}] {segment.segment_type}: "
              f"{segment.start_time:.1f}-{segment.end_time:.1f}s ({duration:.1f}초) "
              f"→ {segment.strategy}")

    # Step 2: 영상 선택 (Mock 테스트 - 실제 API 호출 대신 시뮬레이션)
    print("\n[Step 2] 영상 선택 (시뮬레이션)")
    print("-" * 80)
    print("[WARNING] 실제 Pexels API 호출 필요 - .env에 PEXELS_API_KEY 설정")
    print("[WARNING] 실제 Gemini API 호출 필요 - .env에 GEMINI_API_KEY 설정")

    # Mock 데이터로 시뮬레이션
    print("\n예상 선택 결과:")
    for idx, segment in enumerate(segments, start=1):
        duration = segment.end_time - segment.start_time

        if segment.segment_type == "fixed_closing":
            # 마무리: 20-30초 영상, trim 안 함
            print(f"\n[구간 {idx}] {segment.segment_type} ({duration:.1f}초)")
            print(f"  전략: {segment.strategy}")
            print(f"  영상 길이 범위: 20-30초")
            print(f"  Trim: 없음 (영상 자연스럽게 종료)")
            print(f"  예시: 25초짜리 sunrise 영상 전체 재생")
        else:
            # 도입/중간: 긴 영상, trim 사용
            min_duration = duration + 5.0
            print(f"\n[구간 {idx}] {segment.segment_type} ({duration:.1f}초)")
            print(f"  전략: {segment.strategy}")
            print(f"  영상 길이 범위: {min_duration:.1f}초 이상")
            print(f"  Trim: {duration:.1f}초까지만 사용")
            print(f"  예시: 35초짜리 영상 → 앞 {duration:.1f}초만 재생")

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
            print(f"  영상: 후드 입은 인물 실루엣 (고통 표현)")
        elif segment.strategy == "nature_bright":
            print(f"  영상: 해 뜨는 장면, 빛이 비추는 자연 (희망)")
        else:
            print(f"  영상: 차분한 산, 호수 풍경 (평안)")

        # Trim 정보
        if segment.segment_type == "fixed_closing":
            print(f"  처리: 20-30초 영상 전체 재생 (자연스러운 종료)")
        else:
            min_duration = duration + 5.0
            print(f"  처리: {min_duration:.1f}초+ 영상 → 앞 {duration:.1f}초만 trim")

    print("\n" + "=" * 80)
    print("실제 API 호출 테스트")
    print("=" * 80)
    print("""
실제 테스트 방법:
1. .env 파일에 API 키 설정:
   PEXELS_API_KEY=your_key
   GEMINI_API_KEY=your_key

2. 주석 해제 후 실행:
   # clip_selector = get_clip_selector()
   # selected_clips = clip_selector.select_clips(segments)

3. 결과 확인:
   - 각 구간에 선택된 영상
   - Trim 여부
   - 품질 점수
""")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_video_clip_selector()
