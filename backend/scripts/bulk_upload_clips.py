"""
30개 이상 배경 클립 일괄 업로드
- Pexels/Pixabay에서 검증된 무료 영상 URL
- R2에 업로드 후 DB 저장
"""
import os
import sys
import tempfile
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.storage import get_r2_storage

# 묵상/명상용 자연 영상 소스 (30개+)
# 카테고리: sky, forest, water, clouds, flowers, mountains, sunset, night
CLIP_SOURCES = [
    # === SKY (하늘) ===
    {"id": "clip-sky-01", "category": "sky", "name": "Blue Sky Clouds",
     "url": "https://cdn.pixabay.com/video/2020/05/25/40130-424930941_large.mp4", "duration": 15},
    {"id": "clip-sky-02", "category": "sky", "name": "Cloudy Sky Timelapse",
     "url": "https://cdn.pixabay.com/video/2019/06/20/24622-344760104_large.mp4", "duration": 20},
    {"id": "clip-sky-03", "category": "sky", "name": "Morning Sky",
     "url": "https://cdn.pixabay.com/video/2020/07/30/46026-446115081_large.mp4", "duration": 12},
    {"id": "clip-sky-04", "category": "sky", "name": "Clear Blue Sky",
     "url": "https://cdn.pixabay.com/video/2021/02/22/65930-515877498_large.mp4", "duration": 10},

    # === CLOUDS (구름) ===
    {"id": "clip-clouds-02", "category": "clouds", "name": "Moving Clouds",
     "url": "https://cdn.pixabay.com/video/2019/11/10/29138-372224183_large.mp4", "duration": 15},
    {"id": "clip-clouds-03", "category": "clouds", "name": "Clouds Timelapse",
     "url": "https://cdn.pixabay.com/video/2016/09/05/5007-182491765_large.mp4", "duration": 18},
    {"id": "clip-clouds-04", "category": "clouds", "name": "Soft Clouds",
     "url": "https://cdn.pixabay.com/video/2020/06/25/42846-434787521_large.mp4", "duration": 14},

    # === FOREST (숲) ===
    {"id": "clip-forest-05", "category": "forest", "name": "Forest Sunlight",
     "url": "https://cdn.pixabay.com/video/2019/07/28/25698-351656821_large.mp4", "duration": 20},
    {"id": "clip-forest-06", "category": "forest", "name": "Green Forest",
     "url": "https://cdn.pixabay.com/video/2020/05/12/38921-420056441_large.mp4", "duration": 15},
    {"id": "clip-forest-07", "category": "forest", "name": "Forest Path",
     "url": "https://cdn.pixabay.com/video/2021/08/20/86197-590878514_large.mp4", "duration": 12},
    {"id": "clip-forest-08", "category": "forest", "name": "Autumn Forest",
     "url": "https://cdn.pixabay.com/video/2019/10/16/28143-367111839_large.mp4", "duration": 18},

    # === WATER (물) ===
    {"id": "clip-water-02", "category": "water", "name": "Ocean Waves",
     "url": "https://cdn.pixabay.com/video/2019/05/31/24009-340773560_large.mp4", "duration": 20},
    {"id": "clip-water-03", "category": "water", "name": "Lake Reflection",
     "url": "https://cdn.pixabay.com/video/2020/08/12/47594-450850595_large.mp4", "duration": 15},
    {"id": "clip-water-04", "category": "water", "name": "River Stream",
     "url": "https://cdn.pixabay.com/video/2021/04/02/70213-532695393_large.mp4", "duration": 12},
    {"id": "clip-water-05", "category": "water", "name": "Waterfall",
     "url": "https://cdn.pixabay.com/video/2019/08/07/26222-354311098_large.mp4", "duration": 18},
    {"id": "clip-water-06", "category": "water", "name": "Sea Sunset",
     "url": "https://cdn.pixabay.com/video/2020/07/06/43875-438826890_large.mp4", "duration": 14},

    # === MOUNTAINS (산) ===
    {"id": "clip-mountains-01", "category": "mountains", "name": "Mountain View",
     "url": "https://cdn.pixabay.com/video/2020/05/04/38101-416768476_large.mp4", "duration": 15},
    {"id": "clip-mountains-02", "category": "mountains", "name": "Misty Mountains",
     "url": "https://cdn.pixabay.com/video/2019/09/07/27036-360009247_large.mp4", "duration": 20},
    {"id": "clip-mountains-03", "category": "mountains", "name": "Mountain Clouds",
     "url": "https://cdn.pixabay.com/video/2021/09/06/87797-599125972_large.mp4", "duration": 12},

    # === SUNSET (일몰) ===
    {"id": "clip-sunset-01", "category": "sunset", "name": "Golden Sunset",
     "url": "https://cdn.pixabay.com/video/2019/10/02/27608-363728508_large.mp4", "duration": 18},
    {"id": "clip-sunset-02", "category": "sunset", "name": "Beach Sunset",
     "url": "https://cdn.pixabay.com/video/2020/05/17/39385-421893714_large.mp4", "duration": 15},
    {"id": "clip-sunset-03", "category": "sunset", "name": "Mountain Sunset",
     "url": "https://cdn.pixabay.com/video/2021/05/23/76146-554379683_large.mp4", "duration": 20},
    {"id": "clip-sunset-04", "category": "sunset", "name": "Orange Sky",
     "url": "https://cdn.pixabay.com/video/2019/11/22/29687-375012686_large.mp4", "duration": 12},

    # === FLOWERS (꽃) ===
    {"id": "clip-flowers-01", "category": "flowers", "name": "Field of Flowers",
     "url": "https://cdn.pixabay.com/video/2020/05/01/37888-416042055_large.mp4", "duration": 15},
    {"id": "clip-flowers-02", "category": "flowers", "name": "Spring Flowers",
     "url": "https://cdn.pixabay.com/video/2019/04/20/23178-333285482_large.mp4", "duration": 12},
    {"id": "clip-flowers-03", "category": "flowers", "name": "Cherry Blossoms",
     "url": "https://cdn.pixabay.com/video/2020/04/07/35610-406449557_large.mp4", "duration": 18},

    # === NATURE (자연 일반) ===
    {"id": "clip-nature-01", "category": "nature", "name": "Green Leaves",
     "url": "https://cdn.pixabay.com/video/2020/06/09/41549-430291389_large.mp4", "duration": 14},
    {"id": "clip-nature-02", "category": "nature", "name": "Grass Field",
     "url": "https://cdn.pixabay.com/video/2020/08/01/46256-447206419_large.mp4", "duration": 15},
    {"id": "clip-nature-03", "category": "nature", "name": "Dandelion",
     "url": "https://cdn.pixabay.com/video/2019/06/07/24196-341793665_large.mp4", "duration": 10},

    # === NIGHT (밤) ===
    {"id": "clip-night-02", "category": "night", "name": "Starry Night",
     "url": "https://cdn.pixabay.com/video/2021/08/18/85916-589606089_large.mp4", "duration": 15},
    {"id": "clip-night-03", "category": "night", "name": "Moon Night",
     "url": "https://cdn.pixabay.com/video/2020/10/29/53846-476054879_large.mp4", "duration": 12},
]


def download_video(url: str, dest_path: str, timeout: int = 180) -> bool:
    """영상 다운로드"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"    [FAIL] 다운로드 실패: {e}")
        return False


def process_clip(clip: dict, temp_dir: str, r2, supabase) -> dict:
    """단일 클립 처리 (다운로드 → R2 업로드 → DB 저장)"""
    clip_id = clip["id"]
    result = {"id": clip_id, "success": False, "error": None}

    try:
        # 1. 다운로드
        temp_path = os.path.join(temp_dir, f"{clip_id}.mp4")
        print(f"  [{clip_id}] 다운로드 중...")

        if not download_video(clip["url"], temp_path):
            result["error"] = "Download failed"
            return result

        file_size = os.path.getsize(temp_path) / (1024 * 1024)
        print(f"  [{clip_id}] 다운로드 완료 ({file_size:.1f}MB)")

        # 2. R2 업로드
        print(f"  [{clip_id}] R2 업로드 중...")
        r2_url = r2.upload_file(
            file_path=temp_path,
            folder="clips",
            content_type="video/mp4"
        )
        print(f"  [{clip_id}] R2 완료")

        # 3. DB 저장
        data = {
            "id": clip_id,
            "pack_id": "nature-1",
            "category": clip["category"],
            "name": clip["name"],
            "file_path": r2_url,
            "duration": clip.get("duration", 15),
            "is_active": True,
            "used_count": 0
        }

        # Upsert (있으면 업데이트, 없으면 삽입)
        supabase.table("clips").upsert(data).execute()
        print(f"  [{clip_id}] DB 저장 완료")

        result["success"] = True
        result["r2_url"] = r2_url

        # 임시 파일 삭제
        os.remove(temp_path)

    except Exception as e:
        result["error"] = str(e)
        print(f"  [{clip_id}] 오류: {e}")

    return result


def main():
    print("=" * 60)
    print("배경 클립 일괄 업로드 (30개+)")
    print("=" * 60)

    # 클라이언트 초기화
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    supabase = create_client(supabase_url, supabase_key)
    r2 = get_r2_storage()

    print(f"\n총 {len(CLIP_SOURCES)}개 클립 업로드 예정")
    print("-" * 60)

    # 기존 클립 확인
    existing = supabase.table("clips").select("id").eq("pack_id", "nature-1").execute()
    existing_ids = {c["id"] for c in (existing.data or [])}
    print(f"기존 클립: {len(existing_ids)}개")

    # 새로 업로드할 클립 필터링
    new_clips = [c for c in CLIP_SOURCES if c["id"] not in existing_ids]
    print(f"새로 업로드: {len(new_clips)}개")

    if not new_clips:
        print("\n모든 클립이 이미 업로드되어 있습니다.")
        return

    # 임시 디렉토리에서 처리
    with tempfile.TemporaryDirectory() as temp_dir:
        success_count = 0
        fail_count = 0

        for i, clip in enumerate(new_clips, 1):
            print(f"\n[{i}/{len(new_clips)}] {clip['id']} ({clip['category']})")

            result = process_clip(clip, temp_dir, r2, supabase)

            if result["success"]:
                success_count += 1
            else:
                fail_count += 1

    # 결과 요약
    print("\n" + "=" * 60)
    print("[결과 요약]")
    print("=" * 60)
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")

    # 전체 클립 확인
    all_clips = supabase.table("clips").select("id, category, name").eq("pack_id", "nature-1").eq("is_active", True).execute()

    print(f"\n[현재 활성 클립: {len(all_clips.data or [])}개]")

    # 카테고리별 집계
    categories = {}
    for c in (all_clips.data or []):
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}개")


if __name__ == "__main__":
    main()
