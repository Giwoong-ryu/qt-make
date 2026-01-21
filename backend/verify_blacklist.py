"""
블랙리스트 시스템 동작 확인
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.clip_history import get_clip_history_service

def main():
    service = get_clip_history_service()

    # 테스트용 church_id (실제 데이터 있는 교회 ID 사용)
    church_id = "test_church"

    print("[블랙리스트 시스템 검증]")
    print(f"  Church ID: {church_id}")
    print()

    # 최근 사용된 클립 + 블랙리스트 가져오기
    filtered_clips = service.get_recently_used_clips(church_id, limit=10)

    print(f"[필터링 대상 클립]")
    print(f"  총 {len(filtered_clips)}개 클립이 필터링됩니다.")
    print()

    # 8719740이 포함되어 있는지 확인
    if 8719740 in filtered_clips:
        print("✅ Pexels ID 8719740 (수녀님 얼굴) → 블랙리스트에 포함됨")
        print("   → 향후 영상 생성 시 자동으로 제외됩니다!")
    else:
        print("❌ Pexels ID 8719740이 블랙리스트에 없습니다.")
        print("   → Supabase SQL 실행을 확인하세요.")

    print()
    print(f"[필터링 목록] (최대 20개만 표시)")
    for idx, clip_id in enumerate(sorted(filtered_clips)[:20], 1):
        marker = " ← 블랙리스트" if clip_id == 8719740 else ""
        print(f"  {idx}. Pexels ID: {clip_id}{marker}")

if __name__ == "__main__":
    main()
