"""
blacklist_clips 테이블 생성 및 초기 데이터 삽입
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import get_supabase

def main():
    sb = get_supabase()

    sql = """
-- 얼굴 포함 클립 영구 블랙리스트 테이블
CREATE TABLE IF NOT EXISTS blacklist_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id INTEGER NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_blacklist_clips_id
ON blacklist_clips(clip_id);
"""

    print("[1/2] blacklist_clips 테이블 생성 중...")
    try:
        # Supabase SQL 실행은 REST API로 직접 불가능하므로
        # Supabase Dashboard → SQL Editor에서 실행하거나
        # 직접 INSERT로 시작

        # 블랙리스트 추가
        print("[2/2] 블랙리스트 클립 추가 중...")

        blacklist_clips = [
            {
                "clip_id": 8719740,
                "reason": "nun with face visible (Gemini Vision false positive)"
            }
        ]

        response = sb.table("blacklist_clips").upsert(
            blacklist_clips,
            on_conflict="clip_id"
        ).execute()

        print(f"\n✅ 블랙리스트 추가 완료!")
        print(f"   - Pexels ID: 8719740 (수녀님 얼굴 보임)")
        print(f"\n📌 이제 이 클립은 영상 생성 시 자동으로 필터링됩니다.")

    except Exception as e:
        if "relation \"blacklist_clips\" does not exist" in str(e):
            print("\n❌ blacklist_clips 테이블이 존재하지 않습니다.")
            print("\n📌 Supabase Dashboard → SQL Editor에서 다음 SQL을 실행하세요:")
            print("\n" + sql)
            print("\n실행 후 이 스크립트를 다시 실행하세요.")
        else:
            print(f"\n❌ 에러: {e}")

if __name__ == "__main__":
    main()
