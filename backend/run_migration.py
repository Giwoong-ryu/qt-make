"""
마이그레이션 실행 스크립트
Supabase에 직접 SQL 실행
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client


def get_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("[FAIL] SUPABASE_URL/KEY 환경변수 필요")
        return None
    return create_client(url, key)


def run_migration():
    client = get_client()
    if not client:
        return False

    print("=" * 50)
    print("QT Video SaaS - 마이그레이션 실행")
    print("=" * 50)

    # 1. BGM 테이블 생성 확인 (이미 있으면 스킵)
    print("\n[Step 1] BGM 테이블 확인...")
    try:
        result = client.table("bgms").select("id").limit(1).execute()
        print("  BGM 테이블: [OK] (이미 존재)")
    except Exception as e:
        if "does not exist" in str(e).lower() or "PGRST205" in str(e):
            print("  BGM 테이블: [WARN] 없음 - SQL Editor에서 수동 생성 필요")
            print("\n  === SQL 복사 후 Supabase SQL Editor에서 실행 ===")
            print("""
CREATE TABLE IF NOT EXISTS bgms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration INTEGER NOT NULL,
    preview_url TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
            """)
        else:
            print(f"  Error: {e}")

    # 2. videos 테이블 컬럼 확인
    print("\n[Step 2] videos 테이블 컬럼 확인...")
    try:
        result = client.table("videos").select("bgm_id, bgm_volume, thumbnail_url").limit(1).execute()
        print("  videos 확장 컬럼: [OK]")
    except Exception as e:
        if "bgm_id" in str(e) or "bgm_volume" in str(e) or "thumbnail_url" in str(e):
            print("  videos 확장 컬럼: [WARN] 없음 - SQL Editor에서 수동 추가 필요")
            print("\n  === SQL 복사 후 Supabase SQL Editor에서 실행 ===")
            print("""
ALTER TABLE videos
ADD COLUMN IF NOT EXISTS bgm_id TEXT,
ADD COLUMN IF NOT EXISTS bgm_volume REAL DEFAULT 0.12,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
            """)
        else:
            print(f"  Error: {e}")

    # 3. 데모 교회 확인
    print("\n[Step 3] 데모 교회 확인...")
    try:
        result = client.table("churches").select("*").eq("id", "00000000-0000-0000-0000-000000000001").execute()
        if result.data:
            print(f"  데모 교회: [OK] - {result.data[0]['name']}")
        else:
            # 데모 교회 생성 시도
            print("  데모 교회: 생성 시도...")
            insert_result = client.table("churches").upsert({
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "데모교회",
                "pack_id": "pack-free",
                "contact_email": "demo@example.com",
                "subscription_tier": "free"
            }).execute()
            print(f"  데모 교회: [OK] 생성됨")
    except Exception as e:
        print(f"  데모 교회: [FAIL] {e}")

    # 4. BGM 데이터 삽입 시도
    print("\n[Step 4] BGM 데이터 확인...")
    try:
        result = client.table("bgms").select("*").execute()
        if result.data and len(result.data) > 0:
            print(f"  BGM 데이터: [OK] ({len(result.data)}개)")
        else:
            print("  BGM 데이터: 삽입 시도...")
            bgm_data = [
                {"id": "bgm-001", "name": "평화로운 아침", "category": "calm", "file_path": "bgm/peaceful_morning.mp3", "duration": 180, "sort_order": 1},
                {"id": "bgm-002", "name": "조용한 묵상", "category": "calm", "file_path": "bgm/quiet_meditation.mp3", "duration": 240, "sort_order": 2},
                {"id": "bgm-003", "name": "고요한 시간", "category": "calm", "file_path": "bgm/still_time.mp3", "duration": 200, "sort_order": 3},
                {"id": "bgm-004", "name": "부드러운 피아노", "category": "piano", "file_path": "bgm/soft_piano.mp3", "duration": 210, "sort_order": 4},
                {"id": "bgm-005", "name": "은혜의 선율", "category": "piano", "file_path": "bgm/grace_melody.mp3", "duration": 180, "sort_order": 5},
            ]
            for bgm in bgm_data:
                try:
                    client.table("bgms").upsert(bgm).execute()
                except Exception as be:
                    print(f"    BGM {bgm['id']}: {be}")
            print(f"  BGM 데이터: [OK] 삽입됨")
    except Exception as e:
        if "does not exist" in str(e).lower() or "PGRST205" in str(e):
            print("  BGM 데이터: [SKIP] 테이블 없음")
        else:
            print(f"  BGM 데이터: [FAIL] {e}")

    print("\n" + "=" * 50)
    print("[완료]")
    print("\n만약 테이블/컬럼이 없다면:")
    print("  1. Supabase Dashboard 접속")
    print("  2. SQL Editor 열기")
    print("  3. supabase/run_migration.sql 파일 내용 복사/실행")
    print("=" * 50)

    return True


if __name__ == "__main__":
    run_migration()
