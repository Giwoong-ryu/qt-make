#!/usr/bin/env python3
"""
클립 사전 정규화 스크립트 (Pre-encoding)

빌드 시점에 모든 로컬 클립을 동일 포맷으로 변환하여
런타임에 concat demuxer로 무손실/초고속 연결 가능하게 함

목표 포맷:
- 해상도: 1920x1080
- FPS: 30
- 코덱: libx264
- 픽셀 포맷: yuv420p
- CRF: 23
- 프리셋: faster

효과:
- 런타임 인코딩 제거 (N개 클립 = 0번 인코딩)
- concat demuxer 사용 가능 (무손실 연결)
- 영상 생성 시간 50-70% 단축
"""
import argparse
import logging
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 목표 포맷 설정
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30
TARGET_CRF = 23
TARGET_PRESET = "faster"
TARGET_PIXEL_FORMAT = "yuv420p"

# 밝기 통일 설정 (video.py와 동일)
BRIGHTNESS = 0.05
CONTRAST = 1.0
SATURATION = 0.9
GAMMA = 1.1


def get_video_info(input_path: Path) -> dict:
    """FFprobe로 비디오 정보 조회"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,pix_fmt,codec_name",
        "-of", "json",
        str(input_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            if data.get("streams"):
                stream = data["streams"][0]
                # r_frame_rate 파싱 (예: "30/1")
                fps_str = stream.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = int(num) / int(den) if int(den) > 0 else 30
                else:
                    fps = float(fps_str)
                return {
                    "width": stream.get("width", 0),
                    "height": stream.get("height", 0),
                    "fps": fps,
                    "pix_fmt": stream.get("pix_fmt", "unknown"),
                    "codec": stream.get("codec_name", "unknown")
                }
    except Exception as e:
        logger.warning(f"FFprobe failed for {input_path}: {e}")
    return {}


def is_already_normalized(info: dict) -> bool:
    """이미 정규화된 포맷인지 확인"""
    if not info:
        return False

    return (
        info.get("width") == TARGET_WIDTH and
        info.get("height") == TARGET_HEIGHT and
        abs(info.get("fps", 0) - TARGET_FPS) < 1 and
        info.get("pix_fmt") == TARGET_PIXEL_FORMAT and
        info.get("codec") == "h264"
    )


def normalize_clip(input_path: Path, output_path: Path, force: bool = False) -> bool:
    """단일 클립 정규화"""
    try:
        # 이미 정규화된 파일이 있으면 스킵
        if output_path.exists() and not force:
            logger.info(f"[SKIP] Already exists: {output_path.name}")
            return True

        # 입력 파일 정보 확인
        info = get_video_info(input_path)

        # 이미 정규화된 포맷이면 복사만
        if is_already_normalized(info) and not force:
            logger.info(f"[COPY] Already normalized: {input_path.name}")
            import shutil
            shutil.copy2(input_path, output_path)
            return True

        # 밝기 통일 필터
        color_filter = (
            f"eq=brightness={BRIGHTNESS}:contrast={CONTRAST}:"
            f"saturation={SATURATION}:gamma={GAMMA}"
        )

        # 정규화 명령
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", (
                f"fps={TARGET_FPS},"
                f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
                f"{color_filter},"
                f"format={TARGET_PIXEL_FORMAT}"
            ),
            "-c:v", "libx264",
            "-preset", TARGET_PRESET,
            "-crf", str(TARGET_CRF),
            "-an",  # 오디오 제거 (배경 클립에는 불필요)
            "-movflags", "+faststart",
            str(output_path)
        ]

        logger.info(f"[NORMALIZE] {input_path.name} -> {output_path.name}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg failed for {input_path.name}: {result.stderr}")
            return False

        # 결과 확인
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"[OK] {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f}MB)")
            return True
        else:
            logger.error(f"Output file missing or empty: {output_path}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout normalizing {input_path.name}")
        return False
    except Exception as e:
        logger.error(f"Error normalizing {input_path.name}: {e}")
        return False


def normalize_clip_wrapper(args):
    """ProcessPoolExecutor용 래퍼"""
    input_path, output_path, force = args
    return normalize_clip(input_path, output_path, force)


def main():
    parser = argparse.ArgumentParser(
        description="클립 사전 정규화 (Pre-encoding for fast concat)"
    )
    parser.add_argument(
        "--input", "-i",
        default="/app/background_clips/local",
        help="입력 클립 폴더 (default: /app/background_clips/local)"
    )
    parser.add_argument(
        "--output", "-o",
        default="/app/background_clips/normalized",
        help="출력 폴더 (default: /app/background_clips/normalized)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=2,
        help="병렬 처리 워커 수 (default: 2)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="이미 존재하는 파일도 다시 처리"
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    # 입력 폴더 확인
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    # 출력 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # MP4 파일 찾기
    input_files = list(input_dir.glob("*.mp4"))
    if not input_files:
        logger.warning(f"No MP4 files found in {input_dir}")
        sys.exit(0)

    logger.info(f"Found {len(input_files)} clips to normalize")
    logger.info(f"Target format: {TARGET_WIDTH}x{TARGET_HEIGHT} @ {TARGET_FPS}fps, {TARGET_PIXEL_FORMAT}")

    # 작업 목록 생성
    tasks = []
    for input_path in input_files:
        output_path = output_dir / f"norm_{input_path.name}"
        tasks.append((input_path, output_path, args.force))

    # 병렬 처리
    success_count = 0
    fail_count = 0

    if args.workers > 1:
        # 멀티프로세스
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(normalize_clip_wrapper, task): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    fail_count += 1
    else:
        # 순차 처리
        for task in tasks:
            if normalize_clip(*task):
                success_count += 1
            else:
                fail_count += 1

    # 결과 요약
    logger.info("=" * 50)
    logger.info(f"Normalization complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info(f"  Total: {len(tasks)}")
    logger.info(f"  Output: {output_dir}")
    logger.info("=" * 50)

    # 정규화된 파일 목록 저장 (런타임 참조용)
    manifest_path = output_dir / "manifest.txt"
    with open(manifest_path, "w") as f:
        for output_path in output_dir.glob("norm_*.mp4"):
            f.write(f"{output_path.name}\n")
    logger.info(f"Manifest saved: {manifest_path}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
