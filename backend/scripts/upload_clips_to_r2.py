"""
배경 클립을 R2에 업로드하고 DB 업데이트

장기 운영을 위한 안정적인 클립 관리:
1. Pexels에서 영상 다운로드 (1회)
2. R2에 업로드 (영구 저장)
3. clips 테이블에 R2 URL 저장

사용법:
    python scripts/upload_clips_to_r2.py
"""
import os
import sys
import tempfile
import requests
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.storage import get_r2_storage

# Pexels 묵상/명상용 자연 영상 URL
# [다운로드 테스트 완료] 403 없이 접근 가능한 URL만
# 주의: 영상 내용은 직접 확인 필요!
CLIP_SOURCES = [
    # === 이미 R2에 업로드 완료된 클립 (스킵됨) ===
    # clip-forest-02, clip-sky-01은 이미 DB에 있음

    # === 추가 클립 (다운로드 테스트 완료) ===
    {
        "id": "clip-forest-03",
        "category": "forest",
        "source_url": "https://videos.pexels.com/video-files/5692315/5692315-hd_1920_1080_30fps.mp4",
        "description": "숲속 햇빛 광선"
    },
    {
        "id": "clip-night-01",
        "category": "night",
        "source_url": "https://videos.pexels.com/video-files/857195/857195-sd_640_360_25fps.mp4",
        "description": "밤하늘 은하수 타임랩스"
    },
    {
        "id": "clip-water-01",
        "category": "water",
        "source_url": "https://videos.pexels.com/video-files/1093655/1093655-hd_1920_1080_30fps.mp4",
        "description": "잔잔한 물결"
    },
    {
        "id": "clip-clouds-01",
        "category": "clouds",
        "source_url": "https://videos.pexels.com/video-files/854672/854672-hd_1920_1080_25fps.mp4",
        "description": "구름 하늘"
    },
]


def download_video(url: str, dest_path: str) -> bool:
    """Pexels에서 영상 다운로드"""
    try:
        print(f"  다운로드 중: {url[:60]}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=120)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  다운로드 완료: {size_mb:.1f}MB")
        return True

    except Exception as e:
        print(f"  [FAIL] 다운로드 실패: {e}")
        return False


def main():
    print("=" * 60)
    print("배경 클립 R2 업로드 스크립트")
    print("=" * 60)

    # 클라이언트 초기화
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    supabase = create_client(supabase_url, supabase_key)
    r2 = get_r2_storage()

    print(f"\n[1/3] 클립 소스 확인: {len(CLIP_SOURCES)}개")

    # 임시 디렉토리
    with tempfile.TemporaryDirectory() as temp_dir:
        uploaded = []

        print(f"\n[2/3] 다운로드 및 R2 업로드")
        print("-" * 40)

        for i, clip in enumerate(CLIP_SOURCES, 1):
            print(f"\n({i}/{len(CLIP_SOURCES)}) {clip['id']}: {clip['category']}")

            # 다운로드
            temp_path = os.path.join(temp_dir, f"{clip['id']}.mp4")
            if not download_video(clip["source_url"], temp_path):
                continue

            # R2 업로드
            try:
                print(f"  R2 업로드 중...")
                r2_url = r2.upload_file(
                    file_path=temp_path,
                    folder="clips",
                    content_type="video/mp4"
                )
                print(f"  [OK] R2 URL: {r2_url[:60]}...")

                uploaded.append({
                    **clip,
                    "r2_url": r2_url
                })

            except Exception as e:
                print(f"  [FAIL] R2 업로드 실패: {e}")

        print(f"\n[3/3] DB 업데이트: {len(uploaded)}개")
        print("-" * 40)

        # 기존 클립 삭제 (nature-1 팩)
        try:
            supabase.table("clips").delete().eq("pack_id", "nature-1").execute()
            print("  기존 클립 삭제 완료")
        except Exception as e:
            print(f"  [WARN] 기존 클립 삭제 실패: {e}")

        # 새 클립 추가
        for clip in uploaded:
            try:
                data = {
                    "id": clip["id"],
                    "pack_id": "nature-1",
                    "category": clip["category"],
                    "file_path": clip["r2_url"],
                    "duration": 30,
                    "is_active": True,
                    "used_count": 0
                }
                supabase.table("clips").insert(data).execute()
                print(f"  [OK] {clip['id']}: {clip['category']}")

            except Exception as e:
                print(f"  [FAIL] {clip['id']}: {e}")

        # 결과 확인
        print("\n" + "=" * 60)
        print("[결과]")
        print("=" * 60)

        result = supabase.table("clips").select("id, category, file_path").eq("pack_id", "nature-1").execute()
        clips = result.data or []

        print(f"총 클립: {len(clips)}개")
        for clip in clips:
            is_r2 = "r2.dev" in clip["file_path"]
            status = "[R2]" if is_r2 else "[EXT]"
            print(f"  {status} {clip['id']}: {clip['category']}")

        if len(clips) >= 5:
            print(f"\n[OK] 2분 영상 생성에 충분합니다!")
        else:
            print(f"\n[WARN] 클립이 부족합니다. {5 - len(clips)}개 더 필요.")


if __name__ == "__main__":
    main()
