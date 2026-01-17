"""
E2E 테스트: 영상 생성 전체 플로우
Week 2 기능 포함: BGM 선택, 클립 선택, 자막 편집, 썸네일
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


def test_e2e_video_creation_flow():
    """E2E: 영상 생성 플로우 테스트"""
    print("\n[E2E 테스트: 영상 생성 플로우]")
    client = get_client()

    test_video_id = "e2e-test-video-001"
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        # Step 1: BGM 목록 조회
        print("\n  [Step 1] BGM 목록 조회")
        bgms = client.table("bgms").select("*").eq("is_active", True).limit(3).execute()
        if bgms.data:
            selected_bgm = bgms.data[0]
            print(f"    선택된 BGM: {selected_bgm['name']} ({selected_bgm['category']})")
        else:
            print("    [WARN] BGM 데이터 없음")
            selected_bgm = None

        # Step 2: 클립팩 조회
        print("\n  [Step 2] 클립팩 조회")
        packs = client.table("packs").select("*").execute()
        if packs.data:
            selected_pack = packs.data[0]
            print(f"    선택된 팩: {selected_pack['name']}")
        else:
            print("    [WARN] 팩 데이터 없음")
            selected_pack = {"id": "pack-free"}

        # Step 3: 클립 조회 (팩별)
        print("\n  [Step 3] 클립 조회")
        clips = client.table("clips").select("*").eq("pack_id", selected_pack["id"]).limit(3).execute()
        if clips.data:
            selected_clips = [c["id"] for c in clips.data[:2]]
            print(f"    선택된 클립: {len(selected_clips)}개")
        else:
            print("    [WARN] 클립 데이터 없음")
            selected_clips = []

        # Step 4: 영상 레코드 생성 (with Week 2 fields)
        print("\n  [Step 4] 영상 레코드 생성")
        video_data = {
            "id": test_video_id,
            "church_id": church_id,
            "title": "E2E 테스트 영상",
            "status": "pending",
            "audio_file_path": "test/e2e_audio.mp3",
            "bgm_id": selected_bgm["id"] if selected_bgm else None,
            "bgm_volume": 0.15,
            "thumbnail_url": None,
            "clips_used": selected_clips if selected_clips else None
        }

        result = client.table("videos").upsert(video_data).execute()
        print(f"    영상 생성: [OK] (ID: {test_video_id})")

        # Step 5: 영상 상태 업데이트 (processing -> completed)
        print("\n  [Step 5] 영상 상태 업데이트")
        client.table("videos").update({
            "status": "processing"
        }).eq("id", test_video_id).execute()
        print("    status: pending -> processing [OK]")

        # Step 6: 썸네일 URL 추가
        print("\n  [Step 6] 썸네일 URL 추가")
        client.table("videos").update({
            "thumbnail_url": "https://example.com/thumbnails/test.jpg",
            "status": "completed",
            "video_file_path": "videos/e2e_test_output.mp4"
        }).eq("id", test_video_id).execute()
        print("    thumbnail_url: [OK]")
        print("    status: processing -> completed [OK]")

        # Step 7: 최종 조회 확인
        print("\n  [Step 7] 최종 데이터 확인")
        final = client.table("videos").select("*").eq("id", test_video_id).execute()
        if final.data:
            video = final.data[0]
            print(f"    - title: {video['title']}")
            print(f"    - status: {video['status']}")
            print(f"    - bgm_id: {video.get('bgm_id', 'N/A')}")
            print(f"    - bgm_volume: {video.get('bgm_volume', 'N/A')}")
            print(f"    - thumbnail_url: {'[SET]' if video.get('thumbnail_url') else '[EMPTY]'}")
            print(f"    - clips_used: {video.get('clips_used', 'N/A')}")

        # Cleanup
        print("\n  [Cleanup] 테스트 데이터 삭제")
        client.table("videos").delete().eq("id", test_video_id).execute()
        print("    삭제 완료: [OK]")

        return True

    except Exception as e:
        print(f"\n  [FAIL] {e}")
        # Cleanup on error
        try:
            client.table("videos").delete().eq("id", test_video_id).execute()
        except:
            pass
        return False


def test_e2e_subtitle_flow():
    """E2E: 자막 편집 플로우 테스트"""
    print("\n[E2E 테스트: 자막 편집 플로우]")
    client = get_client()

    test_video_id = "e2e-test-subtitle-001"
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        # Step 1: 영상 레코드 생성
        print("\n  [Step 1] 영상 레코드 생성")
        video_data = {
            "id": test_video_id,
            "church_id": church_id,
            "title": "자막 테스트 영상",
            "status": "completed",
            "audio_file_path": "test/subtitle_audio.mp3",
            "video_file_path": "test/subtitle_video.mp4",
            "srt_file_path": None
        }
        client.table("videos").upsert(video_data).execute()
        print("    영상 생성: [OK]")

        # Step 2: SRT 파일 경로 추가
        print("\n  [Step 2] SRT 파일 경로 추가")
        client.table("videos").update({
            "srt_file_path": "subtitles/e2e_test.srt"
        }).eq("id", test_video_id).execute()
        print("    srt_file_path: [OK]")

        # Step 3: 조회 확인
        print("\n  [Step 3] 최종 확인")
        result = client.table("videos").select("id, title, srt_file_path").eq("id", test_video_id).execute()
        if result.data:
            video = result.data[0]
            print(f"    - srt_file_path: {video.get('srt_file_path', 'N/A')}")

        # Cleanup
        print("\n  [Cleanup] 테스트 데이터 삭제")
        client.table("videos").delete().eq("id", test_video_id).execute()
        print("    삭제 완료: [OK]")

        return True

    except Exception as e:
        print(f"\n  [FAIL] {e}")
        try:
            client.table("videos").delete().eq("id", test_video_id).execute()
        except:
            pass
        return False


def test_e2e_thumbnail_flow():
    """E2E: 썸네일 생성/업로드 플로우 테스트"""
    print("\n[E2E 테스트: 썸네일 플로우]")
    client = get_client()

    test_video_id = "e2e-test-thumbnail-001"
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        # Step 1: 영상 레코드 생성 (썸네일 없음)
        print("\n  [Step 1] 영상 레코드 생성 (썸네일 없음)")
        video_data = {
            "id": test_video_id,
            "church_id": church_id,
            "title": "썸네일 테스트 영상",
            "status": "completed",
            "audio_file_path": "test/thumb_audio.mp3",
            "video_file_path": "test/thumb_video.mp4",
            "thumbnail_url": None
        }
        client.table("videos").upsert(video_data).execute()
        print("    영상 생성: [OK]")
        print("    thumbnail_url: [EMPTY]")

        # Step 2: 자동 생성 썸네일 추가 (5초 지점)
        print("\n  [Step 2] 자동 생성 썸네일 추가")
        client.table("videos").update({
            "thumbnail_url": "thumbnails/e2e_auto_5s.jpg"
        }).eq("id", test_video_id).execute()
        print("    자동 생성 (5s): [OK]")

        # Step 3: 커스텀 썸네일로 교체
        print("\n  [Step 3] 커스텀 썸네일 업로드")
        client.table("videos").update({
            "thumbnail_url": "thumbnails/e2e_custom_upload.jpg"
        }).eq("id", test_video_id).execute()
        print("    커스텀 업로드: [OK]")

        # Step 4: 최종 확인
        print("\n  [Step 4] 최종 확인")
        result = client.table("videos").select("id, title, thumbnail_url").eq("id", test_video_id).execute()
        if result.data:
            video = result.data[0]
            print(f"    - thumbnail_url: {video.get('thumbnail_url', 'N/A')}")

        # Cleanup
        print("\n  [Cleanup] 테스트 데이터 삭제")
        client.table("videos").delete().eq("id", test_video_id).execute()
        print("    삭제 완료: [OK]")

        return True

    except Exception as e:
        print(f"\n  [FAIL] {e}")
        try:
            client.table("videos").delete().eq("id", test_video_id).execute()
        except:
            pass
        return False


def test_e2e_regenerate_flow():
    """E2E: 영상 재생성 플로우 테스트"""
    print("\n[E2E 테스트: 영상 재생성 플로우]")
    client = get_client()

    test_video_id = "e2e-test-regenerate-001"
    church_id = "00000000-0000-0000-0000-000000000001"

    try:
        # Step 1: 초기 영상 생성
        print("\n  [Step 1] 초기 영상 생성")
        video_data = {
            "id": test_video_id,
            "church_id": church_id,
            "title": "재생성 테스트 영상",
            "status": "completed",
            "audio_file_path": "test/regen_audio.mp3",
            "video_file_path": "test/regen_video_v1.mp4",
            "bgm_id": "bgm-001",
            "bgm_volume": 0.10
        }
        client.table("videos").upsert(video_data).execute()
        print("    초기 영상: [OK]")
        print("    bgm_volume: 0.10")

        # Step 2: 옵션 변경하여 재생성 요청
        print("\n  [Step 2] 재생성 요청 (옵션 변경)")
        client.table("videos").update({
            "status": "processing",
            "bgm_id": "bgm-002",
            "bgm_volume": 0.20
        }).eq("id", test_video_id).execute()
        print("    status: completed -> processing")
        print("    bgm_id: bgm-001 -> bgm-002")
        print("    bgm_volume: 0.10 -> 0.20")

        # Step 3: 재생성 완료
        print("\n  [Step 3] 재생성 완료")
        client.table("videos").update({
            "status": "completed",
            "video_file_path": "test/regen_video_v2.mp4"
        }).eq("id", test_video_id).execute()
        print("    status: processing -> completed")
        print("    새 영상 파일: [OK]")

        # Step 4: 최종 확인
        print("\n  [Step 4] 최종 확인")
        result = client.table("videos").select("*").eq("id", test_video_id).execute()
        if result.data:
            video = result.data[0]
            print(f"    - bgm_id: {video.get('bgm_id')}")
            print(f"    - bgm_volume: {video.get('bgm_volume')}")
            print(f"    - video_file_path: {video.get('video_file_path')}")

        # Cleanup
        print("\n  [Cleanup] 테스트 데이터 삭제")
        client.table("videos").delete().eq("id", test_video_id).execute()
        print("    삭제 완료: [OK]")

        return True

    except Exception as e:
        print(f"\n  [FAIL] {e}")
        try:
            client.table("videos").delete().eq("id", test_video_id).execute()
        except:
            pass
        return False


def run_all_e2e_tests():
    """모든 E2E 테스트 실행"""
    print("=" * 60)
    print("QT Video SaaS - E2E 테스트 (영상 생성 플로우)")
    print("=" * 60)

    results = {
        "video_creation": test_e2e_video_creation_flow(),
        "subtitle_edit": test_e2e_subtitle_flow(),
        "thumbnail": test_e2e_thumbnail_flow(),
        "regenerate": test_e2e_regenerate_flow(),
    }

    print("\n" + "=" * 60)
    print("[E2E 테스트 결과 요약]")
    print("-" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"  {name}: {status}")

    print("-" * 60)
    print(f"  통과: {passed}/{total}")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_all_e2e_tests()
    sys.exit(0 if success else 1)
