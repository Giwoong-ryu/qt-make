"""clips 테이블 스키마 확인"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)

    # 기존 클립 전체 데이터 출력
    result = client.table("clips").select("*").limit(1).execute()

    if result.data:
        print("[clips 테이블 컬럼]")
        for key, value in result.data[0].items():
            print(f"  {key}: {type(value).__name__} = {value}")
    else:
        print("데이터 없음")


if __name__ == "__main__":
    main()
