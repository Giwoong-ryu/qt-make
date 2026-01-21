"""
최근 영상의 사용된 클립 ID와 URL 조회
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

    # 1. 가장 최근 영상 조회 (created_at 기준)
    recent_video = (
        sb.table("videos")
        .select("id, created_at, status")
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not recent_video.data:
        print("완료된 영상이 없습니다.")
        return

    video = recent_video.data[0]
    video_id = video["id"]
    created_at = video["created_at"]

    print(f"\n[가장 최근 영상]")
    print(f"  ID: {video_id}")
    print(f"  생성 시간: {created_at}")
    print(f"  상태: {video['status']}")

    # 2. 해당 영상에서 사용된 클립 조회
    used_clips = (
        sb.table("used_clips")
        .select("clip_id, clip_url")
        .eq("video_id", video_id)
        .order("created_at", desc=False)
        .execute()
    )

    if not used_clips.data:
        print("\n사용된 클립이 없습니다.")
        return

    print(f"\n[사용된 클립: {len(used_clips.data)}개]")
    for idx, clip in enumerate(used_clips.data, 1):
        clip_id = clip["clip_id"]
        clip_url = clip["clip_url"]

        # Pexels 썸네일 URL 생성
        thumbnail_url = f"https://www.pexels.com/video/{clip_id}/"

        print(f"\n{idx}. Pexels ID: {clip_id}")
        print(f"   Video URL: {clip_url}")
        print(f"   Thumbnail: {thumbnail_url}")

if __name__ == "__main__":
    main()
