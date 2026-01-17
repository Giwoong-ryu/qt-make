"""
DB 마이그레이션 테스트 스크립트
Supabase에 테이블이 정상적으로 생성되었는지 확인
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("[FAIL] SUPABASE_URL 또는 SUPABASE_KEY 환경변수가 설정되지 않았습니다.")
        print("       .env 파일을 확인하거나 환경변수를 설정하세요.")
        return None

    return create_client(url, key)


def test_tables_exist(client):
    """테이블 존재 확인"""
    print("\n[테이블 존재 확인]")

    tables = ["churches", "packs", "clips", "videos", "bgms"]
    results = {}

    for table in tables:
        try:
            response = client.table(table).select("*").limit(1).execute()
            results[table] = "[OK]"
            print(f"  {table}: [OK] (조회 성공)")
        except Exception as e:
            results[table] = "[FAIL]"
            error_msg = str(e)
            if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
                print(f"  {table}: [FAIL] (테이블 없음)")
            else:
                print(f"  {table}: [FAIL] ({error_msg[:50]})")

    return results


def test_videos_columns(client):
    """videos 테이블 새 컬럼 확인"""
    print("\n[videos 테이블 새 컬럼 확인]")

    try:
        # 새 컬럼들을 포함한 조회
        response = client.table("videos").select(
            "id, title, bgm_id, bgm_volume, thumbnail_url"
        ).limit(1).execute()

        print("  bgm_id: [OK]")
        print("  bgm_volume: [OK]")
        print("  thumbnail_url: [OK]")
        return True
    except Exception as e:
        error_msg = str(e)
        if "bgm_id" in error_msg:
            print("  bgm_id: [FAIL] (컬럼 없음)")
        if "bgm_volume" in error_msg:
            print("  bgm_volume: [FAIL] (컬럼 없음)")
        if "thumbnail_url" in error_msg:
            print("  thumbnail_url: [FAIL] (컬럼 없음)")
        return False


def test_bgms_data(client):
    """BGM 데이터 확인"""
    print("\n[BGM 데이터 확인]")

    try:
        response = client.table("bgms").select("*").execute()
        count = len(response.data)

        if count > 0:
            print(f"  BGM 데이터: [OK] ({count}개)")
            categories = set(bgm["category"] for bgm in response.data)
            print(f"  카테고리: {', '.join(categories)}")
            return True
        else:
            print("  BGM 데이터: [WARN] (0개 - 시드 데이터 필요)")
            return False
    except Exception as e:
        print(f"  BGM 데이터: [FAIL] ({str(e)[:50]})")
        return False


def test_packs_data(client):
    """배경팩 데이터 확인"""
    print("\n[배경팩 데이터 확인]")

    try:
        response = client.table("packs").select("*").execute()
        count = len(response.data)

        if count > 0:
            print(f"  배경팩: [OK] ({count}개)")
            for pack in response.data:
                print(f"    - {pack['id']}: {pack['name']}")
            return True
        else:
            print("  배경팩: [WARN] (0개)")
            return False
    except Exception as e:
        print(f"  배경팩: [FAIL] ({str(e)[:50]})")
        return False


def test_clips_data(client):
    """클립 데이터 확인"""
    print("\n[클립 데이터 확인]")

    try:
        response = client.table("clips").select("*").limit(5).execute()
        count = len(response.data)

        if count > 0:
            print(f"  클립: [OK] ({count}개 샘플)")
            categories = set(clip["category"] for clip in response.data if clip.get("category"))
            if categories:
                print(f"  카테고리: {', '.join(categories)}")
            return True
        else:
            print("  클립: [WARN] (0개)")
            return False
    except Exception as e:
        print(f"  클립: [FAIL] ({str(e)[:50]})")
        return False


def test_demo_church(client):
    """데모 교회 확인"""
    print("\n[데모 교회 확인]")

    try:
        response = client.table("churches").select("*").eq(
            "id", "00000000-0000-0000-0000-000000000001"
        ).execute()

        if response.data:
            church = response.data[0]
            print(f"  데모 교회: [OK]")
            print(f"    - ID: {church['id']}")
            print(f"    - 이름: {church['name']}")
            print(f"    - 팩: {church['pack_id']}")
            return True
        else:
            print("  데모 교회: [WARN] (없음 - 생성 필요)")
            return False
    except Exception as e:
        print(f"  데모 교회: [FAIL] ({str(e)[:50]})")
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 50)
    print("QT Video SaaS - DB 마이그레이션 테스트")
    print("=" * 50)

    client = get_supabase_client()
    if not client:
        return False

    results = {
        "tables": test_tables_exist(client),
        "videos_columns": test_videos_columns(client),
        "bgms": test_bgms_data(client),
        "packs": test_packs_data(client),
        "clips": test_clips_data(client),
        "demo_church": test_demo_church(client),
    }

    print("\n" + "=" * 50)
    print("[최종 결과]")

    # 필수 테이블 확인
    required_tables = ["churches", "packs", "clips", "videos", "bgms"]
    all_tables_ok = all(results["tables"].get(t) == "[OK]" for t in required_tables)

    if all_tables_ok:
        print("  기본 테이블: [OK]")
    else:
        missing = [t for t in required_tables if results["tables"].get(t) != "[OK]"]
        print(f"  기본 테이블: [FAIL] (누락: {', '.join(missing)})")

    if results["videos_columns"]:
        print("  videos 확장 컬럼: [OK]")
    else:
        print("  videos 확장 컬럼: [FAIL] (마이그레이션 필요)")

    if results["bgms"]:
        print("  BGM 데이터: [OK]")
    else:
        print("  BGM 데이터: [WARN] (시드 필요)")

    print("=" * 50)

    return all_tables_ok


if __name__ == "__main__":
    # .env 파일 로드 시도
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[INFO] .env 파일 로드: {env_path}")
    except ImportError:
        print("[WARN] python-dotenv가 설치되지 않았습니다.")

    success = run_all_tests()
    sys.exit(0 if success else 1)
