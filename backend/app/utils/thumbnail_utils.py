"""
썸네일 추출 유틸리티
"""
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def extract_thumbnail_from_video(
    video_path: str,
    timestamp: float = 5.0,
    output_path: str | None = None,
    width: int = 1280,
    height: int = 720
) -> str | None:
    """
    FFmpeg를 사용하여 영상에서 썸네일 이미지 추출

    Args:
        video_path: 영상 파일 경로 (로컬 또는 URL)
        timestamp: 추출할 시간 위치 (초)
        output_path: 출력 파일 경로 (None이면 자동 생성)
        width: 썸네일 너비
        height: 썸네일 높이

    Returns:
        썸네일 파일 경로 (실패 시 None)
    """
    try:
        # 출력 경로 설정
        if output_path is None:
            output_path = os.path.join(
                tempfile.gettempdir(),
                f"thumbnail_{os.urandom(8).hex()}.jpg"
            )

        # FFmpeg 명령 구성
        cmd = [
            "ffmpeg",
            "-y",  # 덮어쓰기
            "-ss", str(timestamp),  # 시작 위치
            "-i", video_path,
            "-vframes", "1",  # 1프레임만
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2",  # 품질 (낮을수록 좋음, 2-5 권장)
            output_path
        ]

        logger.info(f"Extracting thumbnail from {video_path} at {timestamp}s")

        # 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return None

        if os.path.exists(output_path):
            logger.info(f"Thumbnail saved to {output_path}")
            return output_path
        else:
            logger.error("Thumbnail file not created")
            return None

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Thumbnail extraction failed: {e}")
        return None


def extract_thumbnail_from_url(
    video_url: str,
    timestamp: float = 5.0,
    width: int = 1280,
    height: int = 720
) -> bytes | None:
    """
    URL에서 직접 썸네일 추출 (파일 저장 없이 바이트로 반환)

    Args:
        video_url: 영상 URL
        timestamp: 추출할 시간 위치 (초)
        width: 썸네일 너비
        height: 썸네일 높이

    Returns:
        썸네일 이미지 바이트 (실패 시 None)
    """
    try:
        # FFmpeg로 stdout에 출력
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_url,
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-f", "image2",
            "-c:v", "mjpeg",
            "-q:v", "2",
            "pipe:1"  # stdout으로 출력
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and result.stdout:
            return result.stdout
        else:
            logger.error(f"FFmpeg error: {result.stderr.decode()}")
            return None

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Thumbnail extraction from URL failed: {e}")
        return None


def validate_image_file(file_content: bytes, max_size_mb: float = 5.0) -> tuple[bool, str]:
    """
    이미지 파일 유효성 검증

    Args:
        file_content: 파일 내용 (바이트)
        max_size_mb: 최대 파일 크기 (MB)

    Returns:
        (is_valid, error_message)
    """
    # 크기 확인
    size_mb = len(file_content) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"파일 크기가 너무 큽니다 (최대 {max_size_mb}MB)"

    # 매직 바이트로 이미지 형식 확인
    if file_content[:2] == b'\xff\xd8':  # JPEG
        return True, "jpeg"
    elif file_content[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
        return True, "png"
    elif file_content[:6] in (b'GIF87a', b'GIF89a'):  # GIF
        return True, "gif"
    elif file_content[:4] == b'RIFF' and file_content[8:12] == b'WEBP':  # WebP
        return True, "webp"
    else:
        return False, "지원하지 않는 이미지 형식입니다 (JPEG, PNG, GIF, WebP만 가능)"
