"""
현재 Supabase 스키마 확인
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client


def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)

    print("=== 현재 스키마 확인 ===\n")

    # 1. churches 테이블 컬럼 확인
    print("[churches 테이블]")
    try:
        result = client.table("churches").select("*").limit(1).execute()
        if result.data:
            print(f"  컬럼: {list(result.data[0].keys())}")
        else:
            # 빈 테이블이면 아무 데이터나 넣어서 스키마 확인
            print("  (데이터 없음 - 스키마 추정)")
    except Exception as e:
        print(f"  Error: {e}")

    # 2. packs 테이블
    print("\n[packs 테이블]")
    try:
        result = client.table("packs").select("*").limit(1).execute()
        if result.data:
            print(f"  컬럼: {list(result.data[0].keys())}")
    except Exception as e:
        print(f"  Error: {e}")

    # 3. clips 테이블
    print("\n[clips 테이블]")
    try:
        result = client.table("clips").select("*").limit(1).execute()
        if result.data:
            print(f"  컬럼: {list(result.data[0].keys())}")
    except Exception as e:
        print(f"  Error: {e}")

    # 4. videos 테이블
    print("\n[videos 테이블]")
    try:
        result = client.table("videos").select("*").limit(1).execute()
        if result.data:
            print(f"  컬럼: {list(result.data[0].keys())}")
        else:
            print("  (데이터 없음)")
    except Exception as e:
        print(f"  Error: {e}")

    # 5. bgms 테이블
    print("\n[bgms 테이블]")
    try:
        result = client.table("bgms").select("*").limit(1).execute()
        print(f"  [OK] 존재함")
    except Exception as e:
        if "PGRST205" in str(e):
            print("  [FAIL] 테이블 없음")
        else:
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
