"""
API 통합 테스트
Week 2 기능: BGM, 클립, 자막, 썸네일 API
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client


def get_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def test_bgm_api():
    """BGM API 테스트"""
    print("\n[BGM API 테스트]")
    client = get_client()

    # 1. BGM 목록 조회
    try:
        result = client.table("bgms").select("*").eq("is_active", True).order("sort_order").execute()
        print(f"  GET /api/bgms: [OK] ({len(result.data)}개)")

        # 카테고리별 그룹핑
        categories = {}
        for bgm in result.data:
            cat = bgm["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(bgm["name"])

        for cat, names in categories.items():
            print(f"    - {cat}: {len(names)}개")

    except Exception as e:
        print(f"  GET /api/bgms: [FAIL] {e}")
        return False

    return True


def test_clips_api():
    """클립 API 테스트"""
    print("\n[클립 API 테스트]")
    client = get_client()

    # 1. 클립 목록 조회
    try:
        result = client.table("clips").select("*").eq("is_active", True).limit(10).execute()
        print(f"  GET /api/clips: [OK] ({len(result.data)}개)")

        # 카테고리 확인
        categories = set(clip["category"] for clip in result.data)
        print(f"    카테고리: {', '.join(categories)}")

    except Exception as e:
        print(f"  GET /api/clips: [FAIL] {e}")
        return False

    # 2. 팩별 클립 조회
    try:
        result = client.table("clips").select("*").eq("pack_id", "pack-free").execute()
        print(f"  GET /api/clips?pack=pack-free: [OK] ({len(result.data)}개)")
    except Exception as e:
        print(f"  GET /api/clips?pack=pack-free: [FAIL] {e}")

    return True


def test_packs_api():
    """배경팩 API 테스트"""
    print("\n[배경팩 API 테스트]")
    client = get_client()

    try:
        result = client.table("packs").select("*").execute()
        print(f"  GET /api/packs: [OK] ({len(result.data)}개)")

        for pack in result.data:
            free_tag = "[무료]" if pack.get("is_free") else "[유료]"
            print(f"    - {pack['id']}: {pack['name']} {free_tag}")

    except Exception as e:
        print(f"  GET /api/packs: [FAIL] {e}")
        return False

    return True


def test_videos_new_columns():
    """videos 테이블 새 컬럼 테스트"""
    print("\n[videos 새 컬럼 테스트]")
    client = get_client()

    # 테스트 비디오 생성
    test_video_id = "test-video-001"
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        # 1. 테스트 비디오 생성 (새 컬럼 포함)
        video_data = {
            "id": test_video_id,
            "church_id": church_id,
            "title": "테스트 영상",
            "status": "pending",
            "audio_file_path": "test/audio.mp3",
            "bgm_id": "bgm-001",
            "bgm_volume": 0.15,
            "thumbnail_url": "test/thumbnail.jpg"
        }

        result = client.table("videos").upsert(video_data).execute()
        print(f"  INSERT with new columns: [OK]")

        # 2. 조회 확인
        result = client.table("videos").select("*").eq("id", test_video_id).execute()
        if result.data:
            video = result.data[0]
            print(f"    - bgm_id: {video.get('bgm_id')}")
            print(f"    - bgm_volume: {video.get('bgm_volume')}")
            print(f"    - thumbnail_url: {video.get('thumbnail_url')}")

        # 3. 테스트 데이터 삭제
        client.table("videos").delete().eq("id", test_video_id).execute()
        print(f"  DELETE test video: [OK]")

    except Exception as e:
        print(f"  videos 테스트: [FAIL] {e}")
        # 정리 시도
        try:
            client.table("videos").delete().eq("id", test_video_id).execute()
        except:
            pass
        return False

    return True


def test_demo_church_videos():
    """데모 교회 비디오 API 테스트"""
    print("\n[데모 교회 비디오 API 테스트]")
    client = get_client()
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        result = client.table("videos").select("*").eq("church_id", church_id).execute()
        print(f"  GET /api/videos?church_id={church_id[:8]}...: [OK] ({len(result.data)}개)")
    except Exception as e:
        print(f"  GET /api/videos: [FAIL] {e}")
        return False

    return True


def run_all_tests():
    """모든 API 테스트 실행"""
    print("=" * 50)
    print("QT Video SaaS - API 통합 테스트")
    print("=" * 50)

    results = {
        "bgm": test_bgm_api(),
        "clips": test_clips_api(),
        "packs": test_packs_api(),
        "videos_columns": test_videos_new_columns(),
        "demo_church": test_demo_church_videos(),
    }

    print("\n" + "=" * 50)
    print("[테스트 결과 요약]")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"  {name}: {status}")

    print(f"\n통과: {passed}/{total}")
    print("=" * 50)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
