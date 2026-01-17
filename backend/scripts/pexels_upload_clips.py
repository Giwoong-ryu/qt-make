"""
Pexels API로 자연 영상 30개+ 다운로드 후 R2 업로드
"""
import os
import sys
import tempfile
import requests
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.storage import get_r2_storage

PEXELS_API_KEY = "t0VbFmuYS15Ac6kBlKThps8QAMANJVt4wir2XgMs4JJl2sCmNq98H2qz"

# 검색 키워드 및 카테고리 매핑
SEARCH_QUERIES = [
    {"query": "sky clouds timelapse", "category": "sky", "count": 5},
    {"query": "forest sunlight nature", "category": "forest", "count": 5},
    {"query": "ocean waves calm", "category": "water", "count": 5},
    {"query": "mountain landscape fog", "category": "mountains", "count": 4},
    {"query": "sunset golden hour", "category": "sunset", "count": 4},
    {"query": "flowers field nature", "category": "flowers", "count": 3},
    {"query": "grass wind nature", "category": "nature", "count": 2},
    {"query": "stars night sky", "category": "night", "count": 2},
]


def search_pexels_videos(query: str, per_page: int = 10) -> list:
    """Pexels API로 영상 검색"""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "medium"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json().get("videos", [])


def get_best_video_file(video: dict) -> dict | None:
    """최적의 영상 파일 선택 (HD 우선)"""
    files = video.get("video_files", [])

    # HD (1080p 또는 720p) 우선
    for f in files:
        if f.get("quality") == "hd" and f.get("width", 0) >= 1280:
            return f

    # SD 중 가장 큰 것
    sd_files = [f for f in files if f.get("quality") == "sd"]
    if sd_files:
        return max(sd_files, key=lambda x: x.get("width", 0))

    return files[0] if files else None


def download_video(url: str, dest_path: str) -> bool:
    """영상 다운로드"""
    try:
        response = requests.get(url, stream=True, timeout=180)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"    [FAIL] 다운로드 실패: {e}")
        return False


def main():
    print("=" * 60)
    print("Pexels API - 자연 영상 30개+ R2 업로드")
    print("=" * 60)

    # 클라이언트 초기화
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    supabase = create_client(supabase_url, supabase_key)
    r2 = get_r2_storage()

    # 기존 클립 ID 확인
    existing = supabase.table("clips").select("id").eq("pack_id", "nature-1").execute()
    existing_ids = {c["id"] for c in (existing.data or [])}
    print(f"기존 클립: {len(existing_ids)}개")

    uploaded_count = 0
    clip_counter = {}  # 카테고리별 카운터

    with tempfile.TemporaryDirectory() as temp_dir:
        for search in SEARCH_QUERIES:
            query = search["query"]
            category = search["category"]
            target_count = search["count"]

            print(f"\n[검색] '{query}' ({category}) - 목표: {target_count}개")

            try:
                videos = search_pexels_videos(query, per_page=target_count + 5)
                print(f"  API 결과: {len(videos)}개")
            except Exception as e:
                print(f"  [FAIL] API 오류: {e}")
                continue

            added = 0
            for video in videos:
                if added >= target_count:
                    break

                video_file = get_best_video_file(video)
                if not video_file:
                    continue

                # 클립 ID 생성
                cat_count = clip_counter.get(category, 0) + 1
                clip_counter[category] = cat_count
                clip_id = f"clip-{category}-{cat_count:02d}"

                # 이미 존재하면 스킵
                if clip_id in existing_ids:
                    print(f"  [{clip_id}] 이미 존재, 스킵")
                    continue

                download_url = video_file.get("link")
                duration = video.get("duration", 15)

                print(f"  [{clip_id}] 다운로드 중... ({video_file.get('width')}x{video_file.get('height')})")

                # 다운로드
                temp_path = os.path.join(temp_dir, f"{clip_id}.mp4")
                if not download_video(download_url, temp_path):
                    continue

                file_size = os.path.getsize(temp_path) / (1024 * 1024)
                print(f"  [{clip_id}] 다운로드 완료 ({file_size:.1f}MB)")

                # R2 업로드
                try:
                    print(f"  [{clip_id}] R2 업로드 중...")
                    r2_url = r2.upload_file(
                        file_path=temp_path,
                        folder="clips",
                        content_type="video/mp4"
                    )
                    print(f"  [{clip_id}] R2 완료")
                except Exception as e:
                    print(f"  [{clip_id}] R2 실패: {e}")
                    continue

                # DB 저장
                try:
                    data = {
                        "id": clip_id,
                        "pack_id": "nature-1",
                        "category": category,
                        "file_path": r2_url,
                        "duration": duration,
                        "is_active": True,
                        "used_count": 0
                    }
                    supabase.table("clips").upsert(data).execute()
                    print(f"  [{clip_id}] DB 저장 완료")

                    uploaded_count += 1
                    added += 1
                    existing_ids.add(clip_id)

                except Exception as e:
                    print(f"  [{clip_id}] DB 실패: {e}")

                # 임시 파일 삭제
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                # API 레이트 리밋 방지
                time.sleep(0.5)

    # 결과 요약
    print("\n" + "=" * 60)
    print("[결과 요약]")
    print("=" * 60)
    print(f"새로 업로드: {uploaded_count}개")

    # 전체 클립 확인
    all_clips = supabase.table("clips").select("id, category").eq("pack_id", "nature-1").eq("is_active", True).execute()

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
