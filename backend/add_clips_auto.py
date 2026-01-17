"""
nature-1 팩에 Pexels 무료 클립 자동 추가

현재: 2개 클립
목표: 7개 클립 (2분 영상에 충분)

실제 clips 테이블 스키마 (name 컬럼 없음):
- id, pack_id, file_path, category, duration, is_active, used_count, created_at
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Pexels 무료 자연/묵상 영상 URL (30초 이상, 4K)
NEW_CLIPS = [
    {
        "id": "clip-6",
        "category": "sky",
        "url": "https://videos.pexels.com/video-files/857251/857251-hd_1920_1080_25fps.mp4"
    },
    {
        "id": "clip-7",
        "category": "ocean",
        "url": "https://videos.pexels.com/video-files/1093662/1093662-uhd_2560_1440_30fps.mp4"
    },
    {
        "id": "clip-8",
        "category": "mountain",
        "url": "https://videos.pexels.com/video-files/2098989/2098989-uhd_2560_1440_30fps.mp4"
    },
    {
        "id": "clip-9",
        "category": "flower",
        "url": "https://videos.pexels.com/video-files/3843488/3843488-uhd_2560_1440_24fps.mp4"
    },
    {
        "id": "clip-10",
        "category": "sunrise",
        "url": "https://videos.pexels.com/video-files/1851190/1851190-uhd_2560_1440_24fps.mp4"
    },
]

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    client = create_client(url, key)

    # 1. 현재 클립 확인
    print("\n[현재 nature-1 팩 클립]")
    result = client.table("clips").select("*").eq("pack_id", "nature-1").execute()
    existing = result.data or []
    print(f"  현재: {len(existing)}개")
    for clip in existing:
        print(f"  - {clip['id']}: {clip.get('category', 'N/A')}")

    # 2. 새 클립 추가
    print(f"\n[{len(NEW_CLIPS)}개 클립 추가 중...]")

    added = 0
    for clip in NEW_CLIPS:
        # name 컬럼 제외 (테이블에 없음)
        data = {
            "id": clip["id"],
            "pack_id": "nature-1",
            "category": clip["category"],
            "file_path": clip["url"],
            "duration": 30,
            "is_active": True,
            "used_count": 0
        }

        try:
            client.table("clips").insert(data).execute()
            print(f"  [OK] {clip['id']}: {clip['category']}")
            added += 1
        except Exception as e:
            if "duplicate" in str(e).lower():
                print(f"  [SKIP] {clip['id']}: 이미 존재")
            else:
                print(f"  [FAIL] {clip['id']}: {e}")

    # 3. 결과 확인
    print(f"\n[결과]")
    result = client.table("clips").select("*").eq("pack_id", "nature-1").execute()
    total = len(result.data or [])
    print(f"  추가된 클립: {added}개")
    print(f"  현재 총 클립: {total}개")

    if total >= 5:
        print(f"\n[OK] 2분 영상(5개 클립 필요)에 충분합니다!")
    else:
        print(f"\n[WARN] 아직 {5 - total}개 더 필요합니다.")

    # 4. 전체 클립 목록 출력
    print(f"\n[nature-1 팩 전체 클립 목록]")
    for clip in result.data or []:
        print(f"  {clip['id']}: {clip['category']} - {clip['file_path'][:60]}...")


if __name__ == "__main__":
    main()
