#!/usr/bin/env python3
"""
인기 Pexels 클립 사전 다운로드 스크립트

Docker 빌드 시 실행되어 자주 사용되는 배경 클립을 미리 다운로드합니다.

우선순위:
1. DB에서 실제 사용된 클립 (clips_metadata에서 추출)
2. 폴백: 하드코딩된 기본 클립 목록
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 🎬 폴백용 기본 클립 (DB 조회 실패 시)
FALLBACK_CLIPS = [
    # 자연/평화 테마 (Pexels에서 인기 있는 무료 영상)
    {"id": 3571264, "tags": "mountain landscape"},
    {"id": 2169880, "tags": "ocean waves"},
    {"id": 857251, "tags": "forest trees"},
    {"id": 1409899, "tags": "clouds sky"},
    {"id": 2611250, "tags": "sunset golden"},
    {"id": 3163534, "tags": "nature peaceful"},
    {"id": 5532708, "tags": "valley scenic"},
    {"id": 4509468, "tags": "sunrise morning"},
    {"id": 2491284, "tags": "water reflection"},
    {"id": 3049263, "tags": "serene calm"},
]


def fetch_popular_clips_from_db(limit: int = 50) -> list[dict]:
    """
    Supabase DB에서 실제 사용된 인기 클립 조회

    videos.clips_metadata에서 pexels_id를 추출하고 사용 빈도 계산
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            logger.warning("[DB] SUPABASE_URL or SUPABASE_KEY not set")
            return []

        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)

        # clips_metadata가 있는 완료된 영상들 조회
        result = supabase.table("videos") \
            .select("clips_metadata") \
            .eq("status", "completed") \
            .not_.is_("clips_metadata", "null") \
            .order("created_at", desc=True) \
            .limit(200) \
            .execute()

        if not result.data:
            logger.warning("[DB] No completed videos with clips_metadata found")
            return []

        # clips_metadata에서 pexels_id 추출 및 빈도 계산
        clip_counts = {}  # pexels_id -> count
        clip_urls = {}    # pexels_id -> download_url

        for video in result.data:
            clips_metadata = video.get("clips_metadata", [])
            if not clips_metadata:
                continue

            for clip in clips_metadata:
                pexels_id = clip.get("pexels_id")
                download_url = clip.get("download_url")

                if pexels_id and download_url:
                    clip_counts[pexels_id] = clip_counts.get(pexels_id, 0) + 1
                    clip_urls[pexels_id] = download_url

        if not clip_counts:
            logger.warning("[DB] No pexels_id found in clips_metadata")
            return []

        # 사용 빈도 순으로 정렬
        sorted_clips = sorted(clip_counts.items(), key=lambda x: x[1], reverse=True)

        popular_clips = []
        for pexels_id, count in sorted_clips[:limit]:
            popular_clips.append({
                "id": pexels_id,
                "url": clip_urls.get(pexels_id),
                "count": count,
                "tags": f"used_{count}x"
            })

        logger.info(f"[DB] Found {len(popular_clips)} popular clips from DB")
        return popular_clips

    except Exception as e:
        logger.error(f"[DB] Failed to fetch clips from DB: {e}")
        return []


def download_clip_direct(url: str, video_id: int, output_dir: Path, timeout: int = 120) -> bool:
    """
    직접 URL로 클립 다운로드 (DB에서 가져온 URL 사용)
    """
    output_path = output_dir / f"pexels_{video_id}.mp4"

    if output_path.exists():
        logger.info(f"[SKIP] pexels_{video_id}.mp4 already exists")
        return True

    try:
        logger.info(f"[DOWNLOAD] pexels_{video_id}.mp4...")

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"[OK] pexels_{video_id}.mp4 ({file_size_mb:.1f}MB)")
            return True

    except Exception as e:
        logger.error(f"[ERROR] Download failed for {video_id}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def download_clip_via_api(video_id: int, output_dir: Path, tags: str, timeout: int = 120) -> bool:
    """
    Pexels API로 클립 정보 조회 후 다운로드 (폴백용)
    """
    output_path = output_dir / f"pexels_{video_id}.mp4"

    if output_path.exists():
        logger.info(f"[SKIP] pexels_{video_id}.mp4 already exists")
        return True

    try:
        pexels_api_key = os.getenv("PEXELS_API_KEY")
        if not pexels_api_key:
            logger.warning(f"[SKIP] PEXELS_API_KEY not set")
            return False

        api_url = f"https://api.pexels.com/videos/videos/{video_id}"
        headers = {"Authorization": pexels_api_key}

        with httpx.Client(timeout=timeout) as client:
            # 영상 정보 조회
            response = client.get(api_url, headers=headers)
            response.raise_for_status()
            video_data = response.json()

            # HD 화질 URL 찾기
            video_files = video_data.get("video_files", [])
            download_url = None

            for vf in video_files:
                if vf.get("width") == 1920 and vf.get("height") == 1080:
                    download_url = vf.get("link")
                    break

            if not download_url and video_files:
                video_files_sorted = sorted(
                    video_files,
                    key=lambda x: x.get("width", 0) * x.get("height", 0),
                    reverse=True
                )
                download_url = video_files_sorted[0].get("link")

            if not download_url:
                logger.error(f"[ERROR] No download URL for {video_id}")
                return False

            # 다운로드
            logger.info(f"[DOWNLOAD] pexels_{video_id}.mp4 ({tags})...")
            video_response = client.get(download_url)
            video_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(video_response.content)

            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"[OK] pexels_{video_id}.mp4 ({file_size_mb:.1f}MB)")
            return True

    except Exception as e:
        logger.error(f"[ERROR] API download failed for {video_id}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Download popular Pexels clips")
    parser.add_argument("--count", type=int, default=50, help="Number of clips to download")
    parser.add_argument("--output", type=str, default="/app/background_clips", help="Output directory")
    parser.add_argument("--timeout", type=int, default=120, help="Download timeout (seconds)")
    parser.add_argument("--fallback-only", action="store_true", help="Skip DB, use fallback clips only")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"=" * 60)
    logger.info(f"Clip Caching System - Starting")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Target: {args.count} clips")
    logger.info(f"=" * 60)

    clips_to_download = []
    source = "unknown"

    # 1. DB에서 인기 클립 조회 시도
    if not args.fallback_only:
        logger.info("\n[Step 1] Fetching popular clips from DB...")
        db_clips = fetch_popular_clips_from_db(args.count)

        if db_clips:
            clips_to_download = db_clips
            source = "database"
            logger.info(f"[OK] Using {len(db_clips)} clips from DB (actual usage data)")

    # 2. DB 실패 시 폴백
    if not clips_to_download:
        logger.info("\n[Step 2] Using fallback clip list...")
        clips_to_download = FALLBACK_CLIPS[:args.count]
        source = "fallback"
        logger.info(f"[OK] Using {len(clips_to_download)} fallback clips")

    # 3. 다운로드 실행
    logger.info(f"\n[Step 3] Downloading {len(clips_to_download)} clips...")

    success_count = 0
    fail_count = 0

    for idx, clip in enumerate(clips_to_download, 1):
        video_id = clip["id"]
        logger.info(f"\n[{idx}/{len(clips_to_download)}] pexels_{video_id}...")

        # DB에서 가져온 경우 직접 URL 사용
        if source == "database" and clip.get("url"):
            success = download_clip_direct(
                clip["url"], video_id, output_dir, args.timeout
            )
        else:
            # 폴백: Pexels API 사용
            success = download_clip_via_api(
                video_id, output_dir, clip.get("tags", ""), args.timeout
            )

        if success:
            success_count += 1
        else:
            fail_count += 1

    # 4. 결과 요약
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Download Complete!")
    logger.info(f"  Source: {source}")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info(f"  Cache Hit Rate (expected): {success_count}/{args.count} = {success_count/args.count*100:.0f}%")
    logger.info(f"{'=' * 60}")

    # 5. 메타데이터 저장
    metadata = {
        "source": source,
        "clips": [
            {"id": c["id"], "count": c.get("count", 0)}
            for c in clips_to_download
        ],
        "downloaded": success_count,
        "failed": fail_count,
        "output_dir": str(output_dir)
    }

    metadata_path = output_dir / "clips_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved: {metadata_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
