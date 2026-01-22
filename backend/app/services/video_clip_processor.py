"""
영상 클립 처리기 (Video Clip Processor)

선택된 클립들을 다운로드/전처리하여 베이스 영상 생성
"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import requests

from app.services.video_clip_selector import SelectedClip
from app.services.video import get_video_composer

logger = logging.getLogger(__name__)


@dataclass
class CompositionResult:
    """합성 결과"""
    output_path: Path
    total_duration: float
    segments_count: int
    temp_files: List[Path]
    base_video_path: Optional[Path] = None  # 클립만 합친 베이스 영상 (인트로/아웃트로/자막 제외)  # 정리용


class VideoClipProcessor:
    """
    영상 클립 처리기

    처리 순서:
    1. Pexels 영상 다운로드
    2. 구간별 처리 (trim/loop/concat)
    3. 모든 구간 합치기
    4. 베이스 영상 반환 (자막/BGM은 VideoComposer에서 처리)
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Args:
            temp_dir: 임시 파일 저장 디렉토리 (None이면 시스템 기본)
        """
        if temp_dir:
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            # 시스템 임시 디렉토리 사용
            self.temp_dir = Path(tempfile.gettempdir()) / "qt_video_compositor"
            self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"VideoClipProcessor initialized with temp_dir: {self.temp_dir}")

        # FFmpeg 설치 확인
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """FFmpeg 설치 확인"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("FFmpeg found")
            else:
                raise RuntimeError("FFmpeg not working")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install: "
                "https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg check timeout")

    def compose_video(
        self,
        selected_clips: List[SelectedClip],
        output_path: str,
        subtitle_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.12,
        audio_duration: Optional[int] = None,
        thumbnail_path: Optional[str] = None,
        thumbnail_duration: float = 2.0,
        fade_duration: float = 1.0,
        outro_path: Optional[str] = None,
        outro_duration: float = 3.0,
        progress_callback: Optional[callable] = None
    ) -> CompositionResult:
        """
        선택된 클립들을 다운로드/처리 후 video.py에 위임

        VideoClipProcessor의 역할:
        - 클립 다운로드 및 구간별 처리
        - 처리된 클립들을 concat

        나머지는 video.py가 담당:
        - 자막, 인트로, 아웃트로, 최종 합성

        Args:
            selected_clips: 선택된 클립 리스트 (구간 순서대로)
            output_path: 출력 영상 경로
            subtitle_path: 자막 파일 경로 (선택, .srt)
            audio_path: 사용자 음성 파일 경로 (필수)
            bgm_path: BGM 파일 경로 (선택)
            bgm_volume: BGM 볼륨 (0.0~1.0, 기본 0.12)
            audio_duration: 오디오 길이 (초, 선택)
            thumbnail_path: 인트로 썸네일 이미지 경로 (선택)
            thumbnail_duration: 썸네일 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)
            outro_path: 아웃트로 이미지 경로 (선택)
            outro_duration: 아웃트로 표시 시간 (초)
            progress_callback: 진행률 콜백 (current_segment, total_segments)

        Returns:
            합성 결과
        """
        output_path = Path(output_path)
        temp_files = []

        try:
            logger.info(f"[VideoClipProcessor] Starting clip processing for {len(selected_clips)} segments")

            # Step 1: 각 구간 처리 (VideoClipProcessor의 핵심 역할)
            processed_segments = []
            total_duration = 0.0

            for idx, clip in enumerate(selected_clips, start=1):
                segment_duration = clip.segment.end_time - clip.segment.start_time

                # Progress callback 호출
                if progress_callback:
                    progress_callback(idx, len(selected_clips))

                logger.info(
                    f"Processing segment {idx}/{len(selected_clips)}: "
                    f"{clip.segment.segment_type} ({segment_duration:.1f}s)"
                )

                # 구간별 영상 처리 (다운로드 + 트림)
                segment_video = self._process_segment(clip, idx, temp_files)
                processed_segments.append(segment_video)
                total_duration += segment_duration

            # Step 2: 모든 구간 합치기 (concat만)
            logger.info("[VideoClipProcessor] Concatenating all segments")
            base_video = self._concat_segments(processed_segments, temp_files)

            # Step 3: video.py에 나머지 작업 위임 (자막, 인트로, 아웃트로, 최종 합성)
            logger.info("[VideoClipProcessor] Delegating to video.py for final composition")
            video_composer = get_video_composer()

            # 인트로가 있으면 compose_video_with_thumbnail, 없으면 compose_video
            if thumbnail_path:
                final_output = video_composer.compose_video_with_thumbnail(
                    clip_paths=[str(base_video)],  # 이미 concat된 단일 영상
                    audio_path=audio_path,
                    srt_path=subtitle_path,
                    audio_duration=audio_duration or int(total_duration),
                    thumbnail_path=thumbnail_path,
                    thumbnail_duration=thumbnail_duration,
                    bgm_path=bgm_path,
                    clip_durations=[total_duration],  # 단일 클립의 길이
                    bgm_volume=bgm_volume,
                    outro_image_path=outro_path,
                    outro_duration=outro_duration
                )
            else:
                final_output = video_composer.compose_video(
                    clip_paths=[str(base_video)],
                    audio_path=audio_path,
                    srt_path=subtitle_path,
                    audio_duration=audio_duration or int(total_duration),
                    bgm_path=bgm_path,
                    clip_durations=[total_duration],
                    bgm_volume=bgm_volume
                )

            # 최종 파일을 output_path로 복사
            import shutil
            shutil.copy2(final_output, output_path)
            logger.info(f"[VideoClipProcessor] Final video saved to {output_path}")

            return CompositionResult(
                output_path=output_path,
                total_duration=total_duration,
                segments_count=len(selected_clips),
                temp_files=temp_files,
                base_video_path=base_video  # ✅ 베이스 영상 경로 반환 (재생성 시 재사용)
            )

        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            # 실패 시 임시 파일 정리 (output_path 포함)
            self._cleanup_temp_files(temp_files)
            raise

        # 📝 Note: 성공 시 temp_files는 CompositionResult로 반환되어
        # 호출자(tasks.py)에서 output_path를 제외하고 정리함

    def _process_segment(
        self,
        clip: SelectedClip,
        segment_idx: int,
        temp_files: List[Path]
    ) -> Path:
        """
        단일 구간 처리

        Args:
            clip: 선택된 클립
            segment_idx: 구간 번호
            temp_files: 임시 파일 리스트 (추적용)

        Returns:
            처리된 영상 경로
        """
        segment_duration = clip.segment.end_time - clip.segment.start_time

        # 케이스 1: 단일 영상 (trim 필요)
        if not clip.is_multi_video and clip.needs_trim:
            return self._process_single_trim(
                clip, segment_idx, segment_duration, temp_files
            )

        # 케이스 2: 단일 영상 (반복 재생)
        if not clip.is_multi_video and not clip.needs_trim:
            return self._process_single_loop(
                clip, segment_idx, segment_duration, temp_files
            )

        # 케이스 3: 2개 영상 조합 (human 폴백)
        if clip.is_multi_video:
            return self._process_multi_concat(
                clip, segment_idx, temp_files
            )

        raise ValueError(f"Unknown clip processing case: {clip}")

    def _download_video(self, url: str, output_path: Path, video_id: Optional[int] = None) -> Path:
        """
        Pexels 영상 다운로드 (로컬 캐시 우선 사용)

        Args:
            url: 영상 URL
            output_path: 저장 경로
            video_id: Pexels Video ID (캐시 확인용)

        Returns:
            다운로드된 파일 경로
        """
        import shutil
        import random

        cache_dir = Path("/app/background_clips")
        normalized_dir = cache_dir / "normalized"

        # Step 0: [최적화] 정규화된 클립 우선 사용 (concat demuxer 가능)
        # 정규화된 클립은 동일 코덱/해상도/FPS → 무손실 연결 가능
        if normalized_dir.exists():
            normalized_clips = list(normalized_dir.glob("norm_*.mp4"))
            if normalized_clips:
                selected_norm = random.choice(normalized_clips)
                logger.info(f"[NORMALIZED] Using pre-encoded clip: {selected_norm.name} (fast concat enabled)")
                shutil.copy(selected_norm, output_path)
                return output_path

        # Step 1: Pexels 캐시 확인 (Docker 빌드 시 사전 다운로드된 클립)
        if video_id:
            cached_file = cache_dir / f"pexels_{video_id}.mp4"
            if cached_file.exists():
                logger.info(f"[CACHE HIT] Using cached Pexels clip: pexels_{video_id}.mp4")
                shutil.copy(cached_file, output_path)
                return output_path

        # Step 2: 로컬 클립 폴백 (bible_video_samples - 56개 자연 영상)
        local_clips_dir = cache_dir / "local"
        if local_clips_dir.exists():
            local_clips = list(local_clips_dir.glob("*.mp4"))
            if local_clips:
                selected_clip = random.choice(local_clips)
                logger.info(f"[LOCAL CLIP] Using local clip: {selected_clip.name}")
                shutil.copy(selected_clip, output_path)
                return output_path

        # Step 3: 캐시 없으면 Pexels에서 다운로드
        logger.info(f"[DOWNLOAD] Downloading from Pexels: {url[:50]}...")

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded to {output_path}")
        return output_path

    def _process_single_trim(
        self,
        clip: SelectedClip,
        segment_idx: int,
        segment_duration: float,
        temp_files: List[Path]
    ) -> Path:
        """
        단일 영상 trim 처리

        사용 케이스:
        - 도입: 25초+ 영상 → 성경 구절 끝까지 trim
        - human 중간: 30초+ 영상 → 정확히 30초까지 trim
        """
        logger.info(f"Processing single video with trim: {clip.trim_duration:.1f}s")

        # Step 1: 영상 다운로드
        video_url = clip.video.file_path
        downloaded = self.temp_dir / f"seg{segment_idx}_src.mp4"
        video_id = clip.video.id if hasattr(clip.video, 'id') else None
        self._download_video(video_url, downloaded, video_id)
        temp_files.append(downloaded)

        # Step 2: Trim
        trimmed = self.temp_dir / f"seg{segment_idx}_trimmed.mp4"
        temp_files.append(trimmed)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(downloaded),
            "-t", str(clip.trim_duration),
            "-vf", "fps=30,format=yuv420p",  # ✅ 프레임레이트 통일 (프리징 방지)
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질 (23→18)
            "-c:a", "aac", "-b:a", "192k",  # 오디오 품질 향상
            str(trimmed)
        ]

        self._run_ffmpeg(cmd, f"trim segment {segment_idx}")

        return trimmed

    def _process_single_loop(
        self,
        clip: SelectedClip,
        segment_idx: int,
        segment_duration: float,
        temp_files: List[Path]
    ) -> Path:
        """
        단일 영상 반복 재생 처리

        사용 케이스:
        - nature 중간: 15-20초 영상 → 2번 반복
        - 마무리: 20-30초 영상 → 1번 재생 (자연 종료)
        """
        # 반복 횟수 계산
        video_duration = clip.video.duration
        repeat_times = max(1, int(segment_duration / video_duration) + 1)

        logger.info(
            f"Processing single video with loop: "
            f"{video_duration:.1f}s × {repeat_times} times"
        )

        # Step 1: 영상 다운로드
        video_url = clip.video.file_path
        downloaded = self.temp_dir / f"seg{segment_idx}_src.mp4"
        video_id = clip.video.id if hasattr(clip.video, 'id') else None
        self._download_video(video_url, downloaded, video_id)
        temp_files.append(downloaded)

        # Step 2: 반복 (stream_loop)
        looped = self.temp_dir / f"seg{segment_idx}_looped.mp4"
        temp_files.append(looped)

        # repeat_times - 1 (원본 1번 + 추가 반복)
        loop_count = repeat_times - 1

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_count),
            "-i", str(downloaded),
            "-vf", "fps=30,format=yuv420p",  # ✅ 프레임레이트 통일 (프리징 방지)
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질
            "-c:a", "aac", "-b:a", "192k",
            str(looped)
        ]

        self._run_ffmpeg(cmd, f"loop segment {segment_idx}")

        return looped

    def _process_multi_concat(
        self,
        clip: SelectedClip,
        segment_idx: int,
        temp_files: List[Path]
    ) -> Path:
        """
        여러 영상 순차 재생 처리 (human 폴백)

        사용 케이스:
        - human 중간: 17초 + 10초 = 27초 (반복 대신 2개 영상)
        """
        logger.info(
            f"Processing multi-video concat: "
            f"{len(clip.all_videos)} videos"
        )

        # Step 1: 모든 영상 다운로드
        downloaded_videos = []
        for vid_idx, video in enumerate(clip.all_videos):
            video_url = video.file_path
            downloaded = self.temp_dir / f"seg{segment_idx}_vid{vid_idx}.mp4"
            video_id = video.id if hasattr(video, 'id') else None
            self._download_video(video_url, downloaded, video_id)
            temp_files.append(downloaded)
            downloaded_videos.append(downloaded)

        # Step 2: concat 리스트 파일 생성
        concat_list = self.temp_dir / f"seg{segment_idx}_concat.txt"
        temp_files.append(concat_list)

        with open(concat_list, 'w', encoding='utf-8') as f:
            for video_path in downloaded_videos:
                # Windows 경로 → Unix 형식 변환
                unix_path = str(video_path).replace('\\', '/')
                f.write(f"file '{unix_path}'\n")

        # Step 3: concat
        concatenated = self.temp_dir / f"seg{segment_idx}_concat.mp4"
        temp_files.append(concatenated)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-vf", "fps=30,format=yuv420p",  # ✅ 프레임레이트 통일 (프리징 방지)
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질
            "-c:a", "aac", "-b:a", "192k",
            str(concatenated)
        ]

        self._run_ffmpeg(cmd, f"concat segment {segment_idx}")

        return concatenated

    def _concat_segments(
        self,
        segment_videos: List[Path],
        temp_files: List[Path]
    ) -> Path:
        """
        모든 구간 합치기

        Args:
            segment_videos: 처리된 구간 영상 리스트
            temp_files: 임시 파일 리스트

        Returns:
            최종 합성된 영상 경로
        """
        logger.info(f"Concatenating {len(segment_videos)} segments")

        # concat 리스트 파일 생성
        concat_list = self.temp_dir / "final_concat.txt"
        temp_files.append(concat_list)

        with open(concat_list, 'w', encoding='utf-8') as f:
            for video_path in segment_videos:
                unix_path = str(video_path).replace('\\', '/')
                f.write(f"file '{unix_path}'\n")

        # 최종 합성
        final_video = self.temp_dir / "final_video.mp4"
        temp_files.append(final_video)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-vf", "fps=30,format=yuv420p",  # ✅ 프레임레이트 통일 (프리징 방지)
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질
            "-c:a", "aac", "-b:a", "192k",
            str(final_video)
        ]

        self._run_ffmpeg(cmd, "concat all segments")

        return final_video

    # =====================================================================
    # 아래 메서드들은 video.py가 담당하므로 사용하지 않음 (레거시 코드)
    # =====================================================================

    # def _add_audio_with_bgm(...): → video.py의 compose_video가 담당
    # def _add_subtitles(...): → video.py의 _add_subtitles가 담당
    # def _add_thumbnail_intro(...): → video.py의 _add_thumbnail_intro가 담당
    # def _add_outro(...): → video.py의 _add_outro가 담당

    def _run_ffmpeg(self, cmd: List[str], operation: str):
        """
        FFmpeg 명령 실행

        Args:
            cmd: FFmpeg 명령어 리스트
            operation: 작업 설명 (로그용)
        """
        logger.info(f"Running FFmpeg: {operation}")
        logger.debug(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg stderr: {result.stderr}")
                raise RuntimeError(
                    f"FFmpeg failed for {operation}: {result.stderr[:200]}"
                )

            logger.info(f"FFmpeg success: {operation}")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FFmpeg timeout for {operation}")

    def _cleanup_temp_files(self, temp_files: List[Path]):
        """
        임시 파일 정리

        Args:
            temp_files: 정리할 파일 리스트
        """
        logger.info(f"Cleaning up {len(temp_files)} temp files")

        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Deleted: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to delete {temp_file}: {e}")

    def cleanup(self, result: CompositionResult):
        """
        합성 결과의 임시 파일 정리 (사용자 호출)

        Args:
            result: 합성 결과
        """
        self._cleanup_temp_files(result.temp_files)


def get_clip_processor(temp_dir: Optional[str] = None) -> VideoClipProcessor:
    """VideoClipProcessor 팩토리 함수"""
    return VideoClipProcessor(temp_dir=temp_dir)
