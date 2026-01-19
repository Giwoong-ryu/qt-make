"""
Pexels API 실제 영상 길이 확인 테스트

우리가 원하는 시간대(30초)의 영상이 얼마나 있는지 확인
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv()

PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

def test_pexels_video_durations():
    """Pexels 영상 길이 분포 확인"""

    if not PEXELS_API_KEY:
        print("[ERROR] PEXELS_API_KEY 없음 (.env 확인)")
        return

    print("=" * 80)
    print("Pexels 영상 길이 분포 테스트")
    print("=" * 80)

    # 3가지 전략별로 검색
    test_queries = {
        "human": "person silhouette suffering dark",
        "nature_bright": "sunrise golden hour mountain",
        "nature_calm": "calm mountain landscape serene"
    }

    for strategy, query in test_queries.items():
        print(f"\n[{strategy.upper()}] 검색어: '{query}'")
        print("-" * 80)

        try:
            response = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query": query,
                    "per_page": 20,
                    "orientation": "landscape"
                },
                timeout=10
            )

            if response.status_code != 200:
                print(f"[ERROR] API 오류: {response.status_code}")
                continue

            data = response.json()
            videos = data.get('videos', [])

            if not videos:
                print("[ERROR] 검색 결과 없음")
                continue

            # 영상 길이 수집
            durations = []
            for v in videos:
                duration = v.get('duration', 0)
                durations.append(duration)

            # 통계 출력
            print(f"\n총 {len(durations)}개 영상:")
            print(f"  최소: {min(durations):.1f}초")
            print(f"  최대: {max(durations):.1f}초")
            print(f"  평균: {sum(durations)/len(durations):.1f}초")

            # 구간별 분포
            ranges = {
                "10초 미만": 0,
                "10-20초": 0,
                "20-30초": 0,
                "30-40초": 0,
                "40-60초": 0,
                "60초 이상": 0
            }

            for d in durations:
                if d < 10:
                    ranges["10초 미만"] += 1
                elif d < 20:
                    ranges["10-20초"] += 1
                elif d < 30:
                    ranges["20-30초"] += 1
                elif d < 40:
                    ranges["30-40초"] += 1
                elif d < 60:
                    ranges["40-60초"] += 1
                else:
                    ranges["60초 이상"] += 1

            print("\n구간별 분포:")
            for range_name, count in ranges.items():
                percentage = (count / len(durations)) * 100
                bar = "#" * int(percentage / 5)
                print(f"  {range_name:12s}: {count:2d}개 ({percentage:5.1f}%) {bar}")

            # 상세 목록
            print("\n상세 목록:")
            for idx, (v, dur) in enumerate(zip(videos[:10], durations[:10]), start=1):
                width = v.get('width', 0)
                height = v.get('height', 0)
                print(f"  {idx:2d}. {dur:5.1f}초 | {width}x{height} | {v['url'][:50]}...")

        except Exception as e:
            print(f"[ERROR] 오류: {e}")

    print("\n" + "=" * 80)
    print("문제 분석")
    print("=" * 80)
    print("""
우리가 원하는 것:
- 섹션 1 (0-15초): 15초짜리 영상 1개
- 섹션 2 (15-45초): 30초짜리 영상 1개
- 섹션 3 (45-75초): 30초짜리 영상 1개
- 섹션 4 (75-105초): 30초짜리 영상 1개
- 섹션 5 (105-120초): 15초짜리 영상 1개

현실:
- Pexels 영상 길이: 랜덤 (5초~120초)
- 정확히 30초짜리 영상: 거의 없음
- 대부분 10-20초 또는 40-60초

해결책 필요:
1. 긴 영상 잘라쓰기 (60초 → 30초 2개)
2. 짧은 영상 반복/이어붙이기 (15초 → 30초)
3. 시간대 매칭 유연화 (±10초 허용)
""")
    print("=" * 80)


if __name__ == "__main__":
    test_pexels_video_durations()
