"""
nature-1 팩에 클립 추가 스크립트

현재 상태:
- nature-1 팩에 2개 클립만 있음 (clip-4, clip-5)
- 2분 영상에 5개 클립 필요 → 루프 발생

이 스크립트로 클립을 추가합니다.
"""
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("[FAIL] SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        return

    client = create_client(url, key)

    # 1. 현재 nature-1 팩의 클립 확인
    print("\n[현재 nature-1 팩 클립]")
    result = client.table("clips").select("*").eq("pack_id", "nature-1").execute()

    existing_clips = result.data or []
    print(f"  현재 클립 수: {len(existing_clips)}")
    for clip in existing_clips:
        print(f"  - {clip['id']}: {clip.get('name', 'N/A')} ({clip.get('category', 'N/A')})")
        print(f"    URL: {clip['file_path']}")

    # 2. R2 베이스 URL 추출
    if existing_clips:
        sample_url = existing_clips[0]['file_path']
        # https://pub-xxx.r2.dev/clips/xxx.mp4 형태에서 베이스 추출
        base_url = sample_url.rsplit('/', 2)[0]  # clips 폴더까지
        print(f"\n  R2 Base URL: {base_url}")
    else:
        print("\n[WARN] 기존 클립이 없습니다. R2 URL을 직접 입력해주세요.")
        base_url = input("R2 Base URL (예: https://pub-xxx.r2.dev/clips): ").strip()

    # 3. 새 클립 추가 여부 확인
    print("\n" + "="*50)
    print("[클립 추가 옵션]")
    print("="*50)
    print("1. Pexels/Mazwai 무료 영상 URL로 추가 (직접 입력)")
    print("2. R2에 이미 업로드된 영상으로 추가")
    print("3. 테스트용 더미 클립 추가 (기존 URL 복제)")
    print("0. 취소")

    choice = input("\n선택: ").strip()

    if choice == "1":
        add_clips_from_urls(client, base_url)
    elif choice == "2":
        add_clips_from_r2(client, base_url)
    elif choice == "3":
        add_dummy_clips(client, existing_clips)
    else:
        print("취소됨")


def add_clips_from_urls(client, base_url):
    """Pexels/Mazwai 무료 영상 URL로 클립 추가"""
    print("\n[Pexels 무료 영상 URL 입력]")
    print("형식: URL,카테고리,이름")
    print("예: https://pexels.com/video/123.mp4,nature,산속 풍경")
    print("입력 완료 시 빈 줄 입력\n")

    clips_to_add = []
    while True:
        line = input("입력: ").strip()
        if not line:
            break

        parts = line.split(",")
        if len(parts) >= 3:
            url, category, name = parts[0].strip(), parts[1].strip(), parts[2].strip()
            clips_to_add.append({
                "url": url,
                "category": category,
                "name": name
            })
            print(f"  추가됨: {name}")

    if not clips_to_add:
        print("추가할 클립이 없습니다.")
        return

    # 클립 ID 생성 및 DB 삽입
    for i, clip in enumerate(clips_to_add):
        clip_id = f"clip-nature-{100 + i}"
        data = {
            "id": clip_id,
            "pack_id": "nature-1",
            "name": clip["name"],
            "category": clip["category"],
            "file_path": clip["url"],
            "duration": 30,
            "is_active": True,
            "used_count": 0
        }

        try:
            client.table("clips").insert(data).execute()
            print(f"[OK] {clip_id} 추가됨")
        except Exception as e:
            print(f"[FAIL] {clip_id}: {e}")


def add_clips_from_r2(client, base_url):
    """R2에 이미 업로드된 영상으로 클립 추가"""
    print("\n[R2 영상 파일명 입력]")
    print(f"Base URL: {base_url}")
    print("형식: 파일명,카테고리,이름")
    print("예: mountain.mp4,nature,산 풍경")
    print("입력 완료 시 빈 줄 입력\n")

    clips_to_add = []
    while True:
        line = input("입력: ").strip()
        if not line:
            break

        parts = line.split(",")
        if len(parts) >= 3:
            filename, category, name = parts[0].strip(), parts[1].strip(), parts[2].strip()
            full_url = f"{base_url}/{filename}"
            clips_to_add.append({
                "url": full_url,
                "category": category,
                "name": name
            })
            print(f"  추가됨: {name} -> {full_url}")

    if not clips_to_add:
        print("추가할 클립이 없습니다.")
        return

    # 클립 DB 삽입
    for i, clip in enumerate(clips_to_add):
        clip_id = f"clip-nature-{100 + i}"
        data = {
            "id": clip_id,
            "pack_id": "nature-1",
            "name": clip["name"],
            "category": clip["category"],
            "file_path": clip["url"],
            "duration": 30,
            "is_active": True,
            "used_count": 0
        }

        try:
            client.table("clips").insert(data).execute()
            print(f"[OK] {clip_id} 추가됨")
        except Exception as e:
            print(f"[FAIL] {clip_id}: {e}")


def add_dummy_clips(client, existing_clips):
    """테스트용: 기존 클립 URL을 복제해서 클립 추가"""
    if not existing_clips:
        print("[FAIL] 기존 클립이 없어서 복제할 수 없습니다.")
        return

    print(f"\n[테스트용 더미 클립 추가]")
    print(f"기존 {len(existing_clips)}개 클립 URL을 재사용하여 추가합니다.")

    count = input("추가할 클립 수 (기본: 5): ").strip()
    count = int(count) if count.isdigit() else 5

    added = 0
    for i in range(count):
        source_clip = existing_clips[i % len(existing_clips)]
        clip_id = f"clip-nature-{200 + i}"

        data = {
            "id": clip_id,
            "pack_id": "nature-1",
            "name": f"테스트 클립 {i+1}",
            "category": source_clip.get("category", "nature"),
            "file_path": source_clip["file_path"],  # 기존 URL 재사용
            "duration": 30,
            "is_active": True,
            "used_count": 0
        }

        try:
            client.table("clips").insert(data).execute()
            print(f"[OK] {clip_id} 추가됨 (원본: {source_clip['id']})")
            added += 1
        except Exception as e:
            print(f"[FAIL] {clip_id}: {e}")

    print(f"\n총 {added}개 클립 추가됨")
    print(f"현재 nature-1 팩 총 클립 수: {len(existing_clips) + added}개")


if __name__ == "__main__":
    main()
