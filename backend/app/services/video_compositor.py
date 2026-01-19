"""
영상 합성기 (Video Compositor)

선택된 클립들을 FFmpeg으로 하나의 영상으로 합성
"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import requests

from app.services.video_clip_selector import SelectedClip

logger = logging.getLogger(__name__)


@dataclass
class CompositionResult:
    """합성 결과"""
    output_path: Path
    total_duration: float
    segments_count: int
    temp_files: List[Path]  # 정리용


class VideoCompositor:
    """
    영상 합성기

    처리 순서:
    1. Pexels 영상 다운로드
    2. 구간별 처리 (trim/loop/concat)
    3. 모든 구간 합치기
    4. 자막 추가 (선택)
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

        logger.info(f"VideoCompositor initialized with temp_dir: {self.temp_dir}")

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
        선택된 클립들을 하나의 영상으로 합성

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
            logger.info(f"Starting video composition for {len(selected_clips)} segments")

            # Step 1: 각 구간 처리
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

                # 구간별 영상 처리
                segment_video = self._process_segment(clip, idx, temp_files)
                processed_segments.append(segment_video)
                total_duration += segment_duration

            # Step 2: 모든 구간 합치기
            logger.info("Concatenating all segments")
            final_video = self._concat_segments(processed_segments, temp_files)

            # Step 3: 오디오 + BGM 믹싱 (필수)
            if audio_path:
                logger.info("Adding audio with BGM")
                final_with_audio = self._add_audio_with_bgm(
                    final_video,
                    audio_path,
                    bgm_path,
                    audio_duration or int(total_duration),
                    bgm_volume,
                    temp_files
                )
            else:
                final_with_audio = final_video

            # Step 4: 자막 추가 (선택)
            if subtitle_path:
                logger.info("Adding subtitles")
                final_with_subs = self._add_subtitles(
                    final_with_audio,
                    subtitle_path,
                    temp_files
                )
            else:
                final_with_subs = final_with_audio

            # Step 5: 인트로 썸네일 추가 (선택)
            if thumbnail_path:
                logger.info("Adding thumbnail intro")
                final_with_intro = self._add_thumbnail_intro(
                    final_with_subs,
                    thumbnail_path,
                    thumbnail_duration,
                    fade_duration,
                    temp_files
                )
            else:
                final_with_intro = final_with_subs

            # Step 6: 아웃트로 추가 (선택)
            if outro_path:
                logger.info("Adding outro")
                final_with_outro = self._add_outro(
                    final_with_intro,
                    outro_path,
                    outro_duration,
                    fade_duration,
                    temp_files
                )
            else:
                final_with_outro = final_with_intro

            # 최종 파일을 output_path로 복사
            import shutil
            shutil.move(str(final_with_outro), str(output_path))

            logger.info(f"Video composition complete: {output_path}")

            return CompositionResult(
                output_path=output_path,
                total_duration=total_duration,
                segments_count=len(selected_clips),
                temp_files=temp_files
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

    def _download_video(self, url: str, output_path: Path) -> Path:
        """
        Pexels 영상 다운로드

        Args:
            url: 영상 URL
            output_path: 저장 경로

        Returns:
            다운로드된 파일 경로
        """
        logger.info(f"Downloading video from {url[:50]}...")

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
        self._download_video(video_url, downloaded)
        temp_files.append(downloaded)

        # Step 2: Trim
        trimmed = self.temp_dir / f"seg{segment_idx}_trimmed.mp4"
        temp_files.append(trimmed)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(downloaded),
            "-t", str(clip.trim_duration),
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
        self._download_video(video_url, downloaded)
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
            self._download_video(video_url, downloaded)
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
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질 (프리징 방지)
            "-c:a", "aac", "-b:a", "192k",  # 오디오도 고품질
            str(final_video)
        ]

        self._run_ffmpeg(cmd, "concat all segments")

        return final_video

    def _add_audio_with_bgm(
        self,
        video_path: Path,
        voice_path: str,
        bgm_path: Optional[str],
        duration: int,
        bgm_volume: float,
        temp_files: List[Path]
    ) -> Path:
        """
        음성 + BGM 믹싱

        Args:
            video_path: 입력 영상 (영상만)
            voice_path: 사용자 음성 파일
            bgm_path: BGM 파일 (선택)
            duration: 오디오 길이 (초)
            bgm_volume: BGM 볼륨 (0.0~1.0)
            temp_files: 임시 파일 리스트

        Returns:
            오디오가 추가된 영상 경로
        """
        logger.info(f"Adding audio from {voice_path} with BGM volume {bgm_volume}")

        output_path = self.temp_dir / "with_audio.mp4"
        temp_files.append(output_path)

        # BGM 있으면 믹싱, 없으면 음성만
        if bgm_path and Path(bgm_path).exists():
            # BGM + 음성 믹싱
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", voice_path,
                "-stream_loop", "-1",  # BGM 루프
                "-i", bgm_path,
                "-filter_complex",
                f"[1:a]volume=1.0[voice];"
                f"[2:a]volume={bgm_volume}[bgm];"
                f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ac", "2",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(output_path)
            ]
        else:
            # BGM 없이 음성만
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", voice_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ac", "2",
                "-shortest",
                "-movflags", "+faststart",
                str(output_path)
            ]

        self._run_ffmpeg(cmd, "add audio with BGM")

        return output_path

    def _add_subtitles(
        self,
        video_path: Path,
        subtitle_path: str,
        temp_files: List[Path]
    ) -> Path:
        """
        자막 추가

        Args:
            video_path: 입력 영상
            subtitle_path: 자막 파일 (.srt)
            temp_files: 임시 파일 리스트

        Returns:
            자막이 추가된 영상 경로
        """
        logger.info(f"Adding subtitles from {subtitle_path}")

        output_path = self.temp_dir / "with_subtitles.mp4"
        temp_files.append(output_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={subtitle_path}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # 고품질
            "-c:a", "copy",
            str(output_path)
        ]

        self._run_ffmpeg(cmd, "add subtitles")

        return output_path

    def _add_thumbnail_intro(
        self,
        video_path: Path,
        thumbnail_path: str,
        thumbnail_duration: float,
        fade_duration: float,
        temp_files: List[Path]
    ) -> Path:
        """
        영상 시작에 썸네일 이미지 삽입 + 페이드 전환

        Args:
            video_path: 원본 영상
            thumbnail_path: 썸네일 이미지 경로
            thumbnail_duration: 썸네일 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)
            temp_files: 임시 파일 리스트

        Returns:
            인트로가 추가된 영상 경로
        """
        logger.info(f"Adding thumbnail intro: {thumbnail_duration}s display + {fade_duration}s fade")

        output_path = self.temp_dir / "with_intro.mp4"
        temp_files.append(output_path)

        # 총 인트로 시간 = 썸네일 + 페이드
        intro_duration = thumbnail_duration + fade_duration

        # 오디오 딜레이 계산 (밀리초)
        delay_ms = int(thumbnail_duration * 1000)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",  # 이미지 루프
            "-t", str(intro_duration),  # 인트로 길이
            "-i", thumbnail_path,  # 썸네일 이미지
            "-i", str(video_path),  # 원본 영상
            "-filter_complex",
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[thumb];"
            f"[1:v]fps=30,format=yuv420p[main];"
            f"[thumb][main]xfade=transition=fade:duration={fade_duration}:"
            f"offset={thumbnail_duration}[v];"
            f"[1:a]adelay={delay_ms}:all=1[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ac", "2",
            "-movflags", "+faststart",
            str(output_path)
        ]

        self._run_ffmpeg(cmd, "add thumbnail intro")

        return output_path

    def _add_outro(
        self,
        video_path: Path,
        outro_path: str,
        outro_duration: float,
        fade_duration: float,
        temp_files: List[Path]
    ) -> Path:
        """
        영상 끝에 아웃트로 이미지 삽입 + 페이드 전환

        Args:
            video_path: 원본 영상
            outro_path: 아웃트로 이미지 경로
            outro_duration: 아웃트로 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)
            temp_files: 임시 파일 리스트

        Returns:
            아웃트로가 추가된 영상 경로
        """
        logger.info(f"Adding outro: {outro_duration}s display + {fade_duration}s fade")

        output_path = self.temp_dir / "with_outro.mp4"
        temp_files.append(output_path)

        # 원본 영상 길이 구하기
        cmd_probe = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd_probe, capture_output=True, text=True)
        try:
            video_duration = float(result.stdout.strip())
        except ValueError:
            video_duration = 120.0  # 기본값

        # xfade offset = 영상 끝 - 페이드 시간
        xfade_offset = video_duration - fade_duration

        # 아웃트로 총 길이 = fade + outro_duration
        outro_total = fade_duration + outro_duration

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),  # 원본 영상
            "-loop", "1",  # 이미지 루프
            "-t", str(outro_total),  # 아웃트로 길이
            "-i", outro_path,  # 아웃트로 이미지
            "-filter_complex",
            f"[0:v]fps=30,format=yuv420p[main];"
            f"[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[outro];"
            f"[main][outro]xfade=transition=fade:duration={fade_duration}:"
            f"offset={xfade_offset}[v];"
            f"[0:a]afade=t=out:st={xfade_offset}:d={fade_duration}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ac", "2",
            "-movflags", "+faststart",
            str(output_path)
        ]

        self._run_ffmpeg(cmd, "add outro")

        return output_path

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


def get_compositor(temp_dir: Optional[str] = None) -> VideoCompositor:
    """VideoCompositor 팩토리 함수"""
    return VideoCompositor(temp_dir=temp_dir)
