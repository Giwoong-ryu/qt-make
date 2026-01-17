"""
BGM 파일을 R2에 업로드하고 DB 업데이트

무료 로열티 프리 BGM 소스:
- Pixabay Music (무료, 저작권 무료)
"""
import os
import sys
import tempfile
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.storage import get_r2_storage

# Pixabay 무료 음악 (다운로드 테스트 완료)
BGM_SOURCES = [
    {
        "id": "bgm-001",
        "name": "평화로운 아침",
        "category": "calm",
        "source_url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "duration": 180
    },
    {
        "id": "bgm-002",
        "name": "조용한 묵상",
        "category": "calm",
        "source_url": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946b0939c8.mp3",
        "duration": 240
    },
    {
        "id": "bgm-003",
        "name": "부드러운 피아노",
        "category": "piano",
        "source_url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bfb.mp3",
        "duration": 200
    },
]


def download_audio(url: str, dest_path: str) -> bool:
    """음원 다운로드"""
    try:
        print(f"  다운로드 중: {url[:50]}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
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
    print("BGM R2 업로드 스크립트")
    print("=" * 60)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    supabase = create_client(supabase_url, supabase_key)
    r2 = get_r2_storage()

    print(f"\n[1/3] BGM 소스: {len(BGM_SOURCES)}개")

    with tempfile.TemporaryDirectory() as temp_dir:
        uploaded = []

        print(f"\n[2/3] 다운로드 및 R2 업로드")
        print("-" * 40)

        for i, bgm in enumerate(BGM_SOURCES, 1):
            print(f"\n({i}/{len(BGM_SOURCES)}) {bgm['id']}: {bgm['name']}")

            temp_path = os.path.join(temp_dir, f"{bgm['id']}.mp3")
            if not download_audio(bgm["source_url"], temp_path):
                continue

            try:
                print(f"  R2 업로드 중...")
                r2_url = r2.upload_file(
                    file_path=temp_path,
                    folder="bgm",
                    content_type="audio/mpeg"
                )
                print(f"  [OK] R2 URL: {r2_url[:60]}...")

                uploaded.append({
                    **bgm,
                    "r2_url": r2_url
                })

            except Exception as e:
                print(f"  [FAIL] R2 업로드 실패: {e}")

        print(f"\n[3/3] DB 업데이트: {len(uploaded)}개")
        print("-" * 40)

        for bgm in uploaded:
            try:
                # 기존 레코드 업데이트
                supabase.table("bgms").update({
                    "file_path": bgm["r2_url"],
                    "preview_url": bgm["r2_url"]
                }).eq("id", bgm["id"]).execute()
                print(f"  [OK] {bgm['id']}: {bgm['name']}")

            except Exception as e:
                print(f"  [FAIL] {bgm['id']}: {e}")

        # 결과 확인
        print("\n" + "=" * 60)
        print("[결과]")
        print("=" * 60)

        result = supabase.table("bgms").select("id, name, file_path").execute()
        bgms = result.data or []

        print(f"총 BGM: {len(bgms)}개")
        for bgm in bgms[:5]:
            is_r2 = "r2.dev" in str(bgm.get("file_path", ""))
            status = "[R2]" if is_r2 else "[NOT R2]"
            print(f"  {status} {bgm['id']}: {bgm['name']}")


if __name__ == "__main__":
    main()
