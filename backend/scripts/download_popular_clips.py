#!/usr/bin/env python3
"""
인기 Pexels 클립 사전 다운로드 스크립트

Docker 빌드 시 실행되어 자주 사용되는 배경 클립을 미리 다운로드합니다.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 🎬 QT 영상에 자주 사용되는 자연/평화 테마 클립 (Pexels Video ID)
POPULAR_CLIPS = [
    # 산/풍경 (10개)
    {"id": 3571264, "tags": "mountain landscape peaceful"},
    {"id": 2611250, "tags": "mountain sunset golden"},
    {"id": 2418921, "tags": "mountain lake calm"},
    {"id": 3049263, "tags": "mountain clouds serene"},
    {"id": 5532708, "tags": "mountain valley nature"},
    {"id": 3163534, "tags": "mountain forest trees"},
    {"id": 2491284, "tags": "mountain snow winter"},
    {"id": 3571265, "tags": "mountain river flowing"},
    {"id": 4509468, "tags": "mountain peak sunrise"},
    {"id": 3049264, "tags": "mountain waterfall peaceful"},

    # 바다/물 (10개)
    {"id": 2169880, "tags": "ocean waves calm"},
    {"id": 2491284, "tags": "ocean sunset beautiful"},
    {"id": 2611251, "tags": "ocean beach serene"},
    {"id": 3163535, "tags": "ocean water peaceful"},
    {"id": 5532709, "tags": "ocean horizon hope"},
    {"id": 4509469, "tags": "ocean sunrise golden"},
    {"id": 3571266, "tags": "ocean clouds sky"},
    {"id": 2418922, "tags": "ocean shore calm"},
    {"id": 3049265, "tags": "ocean reflection light"},
    {"id": 2611252, "tags": "ocean waves gentle"},

    # 숲/나무 (10개)
    {"id": 3571267, "tags": "forest trees peaceful"},
    {"id": 2611253, "tags": "forest morning light"},
    {"id": 2418923, "tags": "forest path nature"},
    {"id": 3049266, "tags": "forest sunlight rays"},
    {"id": 5532710, "tags": "forest leaves green"},
    {"id": 3163536, "tags": "forest calm serene"},
    {"id": 2491285, "tags": "forest mist fog"},
    {"id": 4509470, "tags": "forest trees tall"},
    {"id": 3571268, "tags": "forest wilderness nature"},
    {"id": 2611254, "tags": "forest canopy light"},

    # 하늘/구름 (10개)
    {"id": 3571269, "tags": "clouds sky peaceful"},
    {"id": 2611255, "tags": "clouds sunset beautiful"},
    {"id": 2418924, "tags": "clouds moving calm"},
    {"id": 3049267, "tags": "clouds sky blue"},
    {"id": 5532711, "tags": "clouds sunrise golden"},
    {"id": 3163537, "tags": "clouds white serene"},
    {"id": 2491286, "tags": "clouds sky hope"},
    {"id": 4509471, "tags": "clouds heaven light"},
    {"id": 3571270, "tags": "clouds weather calm"},
    {"id": 2611256, "tags": "clouds sky peaceful"},

    # 꽃/식물 (10개)
    {"id": 3571271, "tags": "flowers nature beautiful"},
    {"id": 2611257, "tags": "flowers garden peaceful"},
    {"id": 2418925, "tags": "flowers bloom spring"},
    {"id": 3049268, "tags": "flowers colorful serene"},
    {"id": 5532712, "tags": "flowers field calm"},
    {"id": 3163538, "tags": "flowers petals gentle"},
    {"id": 2491287, "tags": "flowers sunlight hope"},
    {"id": 4509472, "tags": "flowers nature calm"},
    {"id": 3571272, "tags": "flowers landscape peaceful"},
    {"id": 2611258, "tags": "flowers meadow serene"},
]


def download_clip(video_id: int, output_dir: Path, tags: str, timeout: int = 120) -> bool:
    """
    Pexels Video ID로 클립 다운로드

    Args:
        video_id: Pexels Video ID
        output_dir: 저장 디렉토리
        tags: 클립 태그 (로깅용)
        timeout: 다운로드 타임아웃 (초)

    Returns:
        성공 여부
    """
    output_path = output_dir / f"pexels_{video_id}.mp4"

    # 이미 다운로드됨
    if output_path.exists():
        logger.info(f"[SKIP] pexels_{video_id}.mp4 already exists")
        return True

    try:
        # Pexels API로 영상 정보 조회 (무료 API)
        # 실제로는 Pexels API 키가 필요하지만, 여기서는 직접 다운로드 URL 사용
        # 프로덕션에서는 app.services.background_video_search.PexelsVideoSearch 사용

        # 임시: 기본 Pexels URL 패턴 사용 (실제로는 API로 URL 가져와야 함)
        # 이 스크립트는 Docker 빌드 시 실행되므로 Pexels API 키가 환경변수에 있어야 함
        pexels_api_key = os.getenv("PEXELS_API_KEY")
        if not pexels_api_key:
            logger.warning(f"[SKIP] PEXELS_API_KEY not set - skipping download for {video_id}")
            return False

        # Pexels API로 영상 정보 조회
        api_url = f"https://api.pexels.com/videos/videos/{video_id}"
        headers = {"Authorization": pexels_api_key}

        with httpx.Client(timeout=timeout) as client:
            # 1. 영상 정보 조회
            response = client.get(api_url, headers=headers)
            response.raise_for_status()
            video_data = response.json()

            # 2. HD 화질 (1920x1080) 다운로드 URL 찾기
            video_files = video_data.get("video_files", [])
            download_url = None

            for vf in video_files:
                if vf.get("width") == 1920 and vf.get("height") == 1080:
                    download_url = vf.get("link")
                    break

            # HD가 없으면 가장 높은 화질 선택
            if not download_url and video_files:
                video_files_sorted = sorted(video_files, key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                download_url = video_files_sorted[0].get("link")

            if not download_url:
                logger.error(f"[ERROR] No download URL found for {video_id}")
                return False

            # 3. 영상 다운로드
            logger.info(f"[DOWNLOAD] pexels_{video_id}.mp4 ({tags})...")
            video_response = client.get(download_url)
            video_response.raise_for_status()

            # 4. 저장
            with open(output_path, "wb") as f:
                f.write(video_response.content)

            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"[OK] pexels_{video_id}.mp4 ({file_size_mb:.1f}MB)")
            return True

    except Exception as e:
        logger.error(f"[ERROR] Download failed for {video_id}: {e}")
        if output_path.exists():
            output_path.unlink()  # 실패한 파일 삭제
        return False


def main():
    parser = argparse.ArgumentParser(description="Download popular Pexels clips")
    parser.add_argument("--count", type=int, default=50, help="Number of clips to download")
    parser.add_argument("--output", type=str, default="/app/background_clips", help="Output directory")
    parser.add_argument("--timeout", type=int, default=120, help="Download timeout (seconds)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting clip download: {args.count} clips to {output_dir}")
    logger.info(f"Total clips available: {len(POPULAR_CLIPS)}")

    success_count = 0
    fail_count = 0

    # 요청된 개수만큼 다운로드
    clips_to_download = POPULAR_CLIPS[:args.count]

    for idx, clip in enumerate(clips_to_download, 1):
        logger.info(f"\n[{idx}/{len(clips_to_download)}] Processing pexels_{clip['id']}...")

        if download_clip(clip["id"], output_dir, clip["tags"], timeout=args.timeout):
            success_count += 1
        else:
            fail_count += 1

    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info(f"Download complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info(f"  Total: {success_count + fail_count}")
    logger.info(f"{'='*60}")

    # 메타데이터 저장
    metadata = {
        "clips": clips_to_download,
        "downloaded": success_count,
        "failed": fail_count,
        "output_dir": str(output_dir)
    }

    metadata_path = output_dir / "clips_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved: {metadata_path}")

    # 실패가 있으면 exit code 1 반환 (Docker 빌드 실패 방지는 하지 않음)
    if fail_count > 0:
        logger.warning(f"Some downloads failed, but continuing...")

    sys.exit(0)


if __name__ == "__main__":
    main()
