"""
Edit Pack Generator - CapCut 편집용 패키지 생성

CapCut에서 사용자가 미세 조정할 수 있도록:
1. SRT 파일 (자막)
2. 씬별 클립 파일 (각 컷에 해당하는 영상)
3. manifest.json (메타데이터)

를 ZIP으로 패키징합니다.

Usage:
    generator = EditPackGenerator()
    result = generator.generate_edit_pack(
        video_id="xxx",
        cuts=cuts,
        clip_data=subtitle_clips,
        srt_path="/path/to/subtitle.srt",
        audio_path="/path/to/audio.mp3"
    )
    print(result.zip_path)  # /tmp/edit_pack_xxx.zip
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class EditPackResult:
    """Edit Pack 생성 결과"""
    zip_path: str                    # ZIP 파일 경로
    manifest: Dict[str, Any]         # manifest.json 내용
    clips_count: int                 # 포함된 클립 수
    total_duration: float            # 전체 길이 (초)
    temp_files: List[str] = field(default_factory=list)  # 정리할 임시 파일들


@dataclass
class ClipInfo:
    """클립 정보 (manifest용)"""
    index: int
    filename: str
    start_time: float
    end_time: float
    duration: float
    visual_query: str
    pexels_id: Optional[int] = None
    subtitle_texts: List[str] = field(default_factory=list)


class EditPackGenerator:
    """
    CapCut Edit Pack Generator

    생성 결과물:
    edit_pack_{video_id}/
    ├── manifest.json       # 메타데이터
    ├── audio.mp3           # 원본 오디오
    ├── subtitles.srt       # 자막 파일
    └── clips/
        ├── clip_001.mp4    # 컷 1 영상
        ├── clip_002.mp4    # 컷 2 영상
        └── ...

    manifest.json 구조:
    {
        "version": "1.0",
        "video_id": "xxx",
        "created_at": "2026-01-23T12:00:00Z",
        "total_duration": 136.5,
        "clips_count": 11,
        "clips": [
            {
                "index": 1,
                "filename": "clips/clip_001.mp4",
                "start_time": 0.0,
                "end_time": 12.5,
                "duration": 12.5,
                "visual_query": "sunrise peaceful nature",
                "subtitle_texts": ["아침 기도로", "하루를 시작합니다"]
            },
            ...
        ],
        "audio": {
            "filename": "audio.mp3",
            "duration": 136.5
        },
        "subtitles": {
            "filename": "subtitles.srt",
            "count": 33
        }
    }
    """

    def __init__(self, download_timeout: float = 120.0):
        """
        Initialize EditPackGenerator

        Args:
            download_timeout: HTTP 다운로드 타임아웃 (초)
        """
        self.download_timeout = download_timeout
        self.http_client = httpx.Client(timeout=download_timeout)

    def __del__(self):
        """Cleanup HTTP client"""
        try:
            if hasattr(self, 'http_client') and self.http_client is not None:
                self.http_client.close()
        except Exception:
            pass  # Ignore errors during interpreter shutdown

    def generate_edit_pack(
        self,
        video_id: str,
        cuts: List[Any],                # SubtitleCut 리스트
        clip_data: List[Dict[str, Any]], # subtitle_clips (cut, description, video)
        srt_path: str,
        audio_path: str,
        audio_duration: float,
        output_dir: Optional[str] = None
    ) -> EditPackResult:
        """
        Edit Pack ZIP 생성

        Args:
            video_id: 영상 UUID
            cuts: SubtitleCut 리스트
            clip_data: Pexels 영상 데이터 리스트
            srt_path: SRT 파일 경로
            audio_path: 오디오 파일 경로
            audio_duration: 오디오 길이 (초)
            output_dir: 출력 디렉토리 (기본: 시스템 temp)

        Returns:
            EditPackResult
        """
        logger.info(f"[EditPackGenerator] Generating edit pack for video {video_id}")

        # 작업 디렉토리 생성
        if output_dir:
            work_dir = Path(output_dir) / f"edit_pack_{video_id}"
        else:
            work_dir = Path(tempfile.mkdtemp(prefix=f"edit_pack_{video_id}_"))

        clips_dir = work_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)

        temp_files = []
        clips_info = []

        try:
            # 1. 클립 다운로드 및 트림
            logger.info(f"[EditPackGenerator] Downloading and trimming {len(clip_data)} clips...")

            for idx, data in enumerate(clip_data):
                cut = data['cut']
                description = data['description']
                video = data['video']

                clip_filename = f"clip_{idx+1:03d}.mp4"
                clip_output_path = clips_dir / clip_filename

                # Pexels에서 클립 다운로드
                downloaded_path = self._download_clip(video.file_path, work_dir, idx)
                temp_files.append(downloaded_path)

                # 컷 길이에 맞게 트림
                self._trim_clip(
                    input_path=downloaded_path,
                    output_path=str(clip_output_path),
                    duration=cut.duration
                )

                # 클립 정보 기록
                clips_info.append(ClipInfo(
                    index=idx + 1,
                    filename=f"clips/{clip_filename}",
                    start_time=cut.start_time,
                    end_time=cut.end_time,
                    duration=cut.duration,
                    visual_query=description.visual_query,
                    pexels_id=video.id if hasattr(video, 'id') else None,
                    subtitle_texts=cut.subtitle_texts
                ))

                logger.info(
                    f"  Clip {idx+1}: {cut.duration:.2f}s - {description.visual_query[:40]}..."
                )

            # 2. 오디오 파일 복사
            audio_dest = work_dir / "audio.mp3"
            if audio_path.endswith('.m4a'):
                # M4A인 경우 MP3로 변환
                self._convert_to_mp3(audio_path, str(audio_dest))
            else:
                shutil.copy2(audio_path, audio_dest)

            # 3. SRT 파일 복사
            srt_dest = work_dir / "subtitles.srt"
            shutil.copy2(srt_path, srt_dest)

            # SRT 자막 수 카운트
            subtitle_count = self._count_srt_entries(srt_path)

            # 4. manifest.json 생성
            manifest = {
                "version": "1.0",
                "video_id": video_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "total_duration": audio_duration,
                "clips_count": len(clips_info),
                "clips": [
                    {
                        "index": clip.index,
                        "filename": clip.filename,
                        "start_time": round(clip.start_time, 2),
                        "end_time": round(clip.end_time, 2),
                        "duration": round(clip.duration, 2),
                        "visual_query": clip.visual_query,
                        "pexels_id": clip.pexels_id,
                        "subtitle_texts": clip.subtitle_texts
                    }
                    for clip in clips_info
                ],
                "audio": {
                    "filename": "audio.mp3",
                    "duration": round(audio_duration, 2)
                },
                "subtitles": {
                    "filename": "subtitles.srt",
                    "count": subtitle_count
                },
                "capcut_import_guide": {
                    "step1": "Import audio.mp3 to timeline",
                    "step2": "Import clips in order (clip_001.mp4, clip_002.mp4, ...)",
                    "step3": "Match clip start times with manifest.json",
                    "step4": "Import subtitles.srt for captions",
                    "step5": "Adjust transitions and effects as needed"
                }
            }

            manifest_path = work_dir / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            # 5. ZIP 파일 생성
            zip_filename = f"edit_pack_{video_id}.zip"
            zip_path = work_dir.parent / zip_filename

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # manifest.json
                zf.write(manifest_path, "manifest.json")
                # audio
                zf.write(audio_dest, "audio.mp3")
                # subtitles
                zf.write(srt_dest, "subtitles.srt")
                # clips
                for clip_file in sorted(clips_dir.iterdir()):
                    zf.write(clip_file, f"clips/{clip_file.name}")

            logger.info(f"[EditPackGenerator] ZIP created: {zip_path}")

            # 작업 디렉토리 정리 (ZIP은 유지)
            temp_files.append(str(work_dir))

            return EditPackResult(
                zip_path=str(zip_path),
                manifest=manifest,
                clips_count=len(clips_info),
                total_duration=audio_duration,
                temp_files=temp_files
            )

        except Exception as e:
            logger.exception(f"[EditPackGenerator] Failed to generate edit pack: {e}")
            # 정리
            for temp_file in temp_files:
                self._safe_delete(temp_file)
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
            raise

    def _download_clip(self, url: str, work_dir: Path, index: int) -> str:
        """
        Pexels에서 클립 다운로드

        Args:
            url: Pexels 다운로드 URL
            work_dir: 작업 디렉토리
            index: 클립 인덱스

        Returns:
            다운로드된 파일 경로
        """
        output_path = work_dir / f"raw_clip_{index:03d}.mp4"

        logger.debug(f"[EditPackGenerator] Downloading clip {index} from {url[:80]}...")

        response = self.http_client.get(url)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return str(output_path)

    def _trim_clip(self, input_path: str, output_path: str, duration: float) -> None:
        """
        클립을 지정된 길이로 트림

        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로
            duration: 목표 길이 (초)
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            logger.error(f"[EditPackGenerator] FFmpeg trim failed: {result.stderr}")
            raise RuntimeError(f"FFmpeg trim failed: {result.stderr[:200]}")

    def _convert_to_mp3(self, input_path: str, output_path: str) -> None:
        """
        오디오를 MP3로 변환

        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # 변환 실패 시 원본 복사 시도
            logger.warning(f"[EditPackGenerator] MP3 conversion failed, copying original")
            shutil.copy2(input_path, output_path)

    def _count_srt_entries(self, srt_path: str) -> int:
        """
        SRT 파일의 자막 개수 카운트

        Args:
            srt_path: SRT 파일 경로

        Returns:
            자막 개수
        """
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # SRT 형식: 번호\n시작 --> 끝\n텍스트\n\n
            import re
            matches = re.findall(r'^\d+$', content, re.MULTILINE)
            return len(matches)
        except Exception as e:
            logger.warning(f"[EditPackGenerator] Failed to count SRT entries: {e}")
            return 0

    def _safe_delete(self, path: str) -> None:
        """안전하게 파일/디렉토리 삭제"""
        try:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            logger.warning(f"[EditPackGenerator] Failed to delete {path}: {e}")


# Singleton
_generator: Optional[EditPackGenerator] = None


def get_edit_pack_generator() -> EditPackGenerator:
    """EditPackGenerator 싱글톤 반환"""
    global _generator
    if _generator is None:
        _generator = EditPackGenerator()
    return _generator
