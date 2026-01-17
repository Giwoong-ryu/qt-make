"""
FFmpeg 영상 합성 서비스

동적 클립 duration 시스템:
- 각 클립의 실제 duration 사용 (고정 30초 X)
- 클립 선택 시 duration 정보 함께 전달
- 총 영상 길이가 오디오 길이 이상이 되도록 보장
"""
import logging
import os
import random
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoComposer:
    """FFmpeg 기반 영상 합성 서비스"""

    # 한글 자막용 폰트 (부드러운 둥근 폰트 우선)
    # fonts-nanum 패키지: NanumGothic, NanumBarunGothic 등
    KOREAN_FONT = "NanumBarunGothic"
    FALLBACK_FONT = "NanumGothic"
    FALLBACK_FONT_2 = "Noto Sans CJK KR"

    # 클립 전환 설정
    CROSSFADE_DURATION = 1.0  # 크로스페이드 1초
    DEFAULT_CLIP_DURATION = 30  # 기본값 (duration 정보 없을 때만)

    # 출력 해상도 설정 (1080p 유지)
    OUTPUT_WIDTH = 1920
    OUTPUT_HEIGHT = 1080
    OUTPUT_CRF = 23  # 압축 레벨 (18=고품질, 23=표준, 28=저품질)

    # BGM 설정
    BGM_VOLUME = 0.12  # BGM 볼륨 (12% - 말씀이 잘 들리도록)

    # 밝기 통일 설정 (묵상 영상 분위기)
    # eq 필터: brightness=0.0 (기본), contrast=1.0 (기본), gamma=1.0 (기본)
    # 밝은 분위기로 통일: 약간 밝게 + 대비 낮춤 + 감마 보정
    BRIGHTNESS = 0.05      # 밝기 (0.0 기본, -1.0~1.0)
    CONTRAST = 1.0         # 대비 (1.0 기본, 0.0~2.0)
    SATURATION = 0.9       # 채도 (1.0 기본) - 약간 낮춰서 부드럽게
    GAMMA = 1.1            # 감마 (1.0 기본) - 어두운 부분 밝게

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "qt-video"
        self.temp_dir.mkdir(exist_ok=True)
        self.bgm_dir = Path("/app/assets/bgm")  # BGM 폴더

    def compose_video(
        self,
        clip_paths: list[str],
        audio_path: str,
        srt_path: str,
        audio_duration: int,
        bgm_path: str | None = None,
        clip_durations: list[int] | None = None,
        bgm_volume: float = 0.12
    ) -> str:
        """
        배경 클립 + 오디오 + BGM + 자막 → 최종 영상

        Args:
            clip_paths: 배경 클립 URL 리스트
            audio_path: MP3 파일 경로
            srt_path: SRT 자막 파일 경로
            audio_duration: 오디오 길이 (초)
            bgm_path: BGM 파일 경로 (옵션)
            clip_durations: 각 클립의 실제 duration 리스트 (옵션)

        Returns:
            output_path: 생성된 MP4 경로
        """
        try:
            output_id = str(uuid4())
            output_path = str(self.temp_dir / f"{output_id}.mp4")

            # clip_durations가 없으면 기본값 사용
            if clip_durations is None:
                clip_durations = [self.DEFAULT_CLIP_DURATION] * len(clip_paths)

            total_clip_duration = sum(clip_durations)
            logger.info(
                f"Composing video: {len(clip_paths)} clips, "
                f"total clip duration: {total_clip_duration}s, "
                f"audio duration: {audio_duration}s"
            )

            # Step 1: 클립 연결 (크로스페이드 전환, 실제 duration 사용)
            concat_path = self._concat_clips_with_crossfade(
                clip_paths, audio_duration, clip_durations
            )

            # Step 2: 오디오 + BGM 믹싱
            with_audio_path = self._add_audio_with_bgm(
                concat_path, audio_path, bgm_path, audio_duration, bgm_volume
            )

            # Step 3: 자막 오버레이
            self._add_subtitles(with_audio_path, srt_path, output_path)

            # 임시 파일 정리
            self._cleanup_temp([concat_path, with_audio_path])

            logger.info(f"Video composed: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Video composition failed: {e}")
            raise

    def compose_video_with_thumbnail(
        self,
        clip_paths: list[str],
        audio_path: str,
        srt_path: str,
        audio_duration: int,
        thumbnail_path: str,
        bgm_path: str | None = None,
        thumbnail_duration: float = 2.0,
        fade_duration: float = 1.0,
        clip_durations: list[int] | None = None,
        bgm_volume: float = 0.12,
        outro_image_path: str | None = None,
        outro_duration: float = 3.0
    ) -> str:
        """
        썸네일 인트로 + 배경 클립 + 오디오 + BGM + 자막 + 아웃트로 → 최종 영상

        구조: [썸네일 인트로 2초] → [페이드 1초] → [본 영상] → [페이드 1초] → [아웃트로 3초]

        Args:
            clip_paths: 배경 클립 URL 리스트
            audio_path: MP3 파일 경로
            srt_path: SRT 자막 파일 경로
            audio_duration: 오디오 길이 (초)
            thumbnail_path: 인트로 썸네일 이미지 경로 (텍스트 포함)
            bgm_path: BGM 파일 경로 (옵션)
            thumbnail_duration: 썸네일 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)
            clip_durations: 각 클립의 실제 duration 리스트 (옵션)
            bgm_volume: BGM 볼륨 (0.0~1.0)
            outro_image_path: 아웃트로 이미지 경로 (텍스트 없이 배경만, 옵션)
            outro_duration: 아웃트로 표시 시간 (초)

        Returns:
            output_path: 생성된 MP4 경로
        """
        try:
            # Step 1: 기본 영상 생성 (썸네일 없이)
            main_video = self.compose_video(
                clip_paths, audio_path, srt_path, audio_duration, bgm_path, clip_durations, bgm_volume
            )

            # Step 2: 썸네일 인트로 삽입
            with_intro = self._add_thumbnail_intro(
                main_video, thumbnail_path, thumbnail_duration, fade_duration
            )

            # Step 3: 아웃트로 삽입 (있으면)
            if outro_image_path and os.path.exists(outro_image_path):
                output_path = self._add_outro(
                    with_intro, outro_image_path, outro_duration, fade_duration
                )
                self._cleanup_temp([main_video, with_intro])
            else:
                output_path = with_intro
                self._cleanup_temp([main_video])

            logger.info(f"Video with thumbnail composed: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Video composition with thumbnail failed: {e}")
            raise

    def _add_thumbnail_intro(
        self,
        video_path: str,
        thumbnail_path: str,
        thumbnail_duration: float = 2.0,
        fade_duration: float = 1.0
    ) -> str:
        """
        영상 시작에 썸네일 이미지 삽입 + 페이드 전환
        
        Args:
            video_path: 원본 영상 경로
            thumbnail_path: 썸네일 이미지 경로
            thumbnail_duration: 썸네일 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)
            
        Returns:
            output_path: 썸네일이 삽입된 영상 경로
        """
        output_path = str(self.temp_dir / f"thumb_intro_{uuid4()}.mp4")
        
        # 총 인트로 시간 = 썸네일 + 페이드
        intro_duration = thumbnail_duration + fade_duration
        
        # 오디오 딜레이 계산 (밀리초)
        delay_ms = int(thumbnail_duration * 1000)
        
        # filter_complex로 썸네일 이미지 → 영상으로 변환 후 xfade 적용
        # 오디오도 adelay 필터로 지연
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",  # 이미지 루프
            "-t", str(intro_duration),  # 인트로 길이
            "-i", thumbnail_path,  # 썸네일 이미지
            "-i", video_path,  # 원본 영상
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
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ac", "2",
            "-movflags", "+faststart",
            output_path
        ]
        
        logger.info(f"Adding thumbnail intro: {thumbnail_duration}s display + {fade_duration}s fade (Audio delay: {delay_ms}ms)")
        self._run_ffmpeg(cmd)

        return output_path

    def _add_outro(
        self,
        video_path: str,
        outro_image_path: str,
        outro_duration: float = 3.0,
        fade_duration: float = 1.0
    ) -> str:
        """
        영상 끝에 아웃트로 이미지 삽입 + 페이드 전환

        Args:
            video_path: 원본 영상 경로
            outro_image_path: 아웃트로 이미지 경로 (텍스트 없이 배경만)
            outro_duration: 아웃트로 표시 시간 (초)
            fade_duration: 페이드 전환 시간 (초)

        Returns:
            output_path: 아웃트로가 삽입된 영상 경로
        """
        output_path = str(self.temp_dir / f"with_outro_{uuid4()}.mp4")

        # 원본 영상 길이 구하기
        cmd_probe = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
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
            "-i", video_path,  # 원본 영상
            "-loop", "1",  # 이미지 루프
            "-t", str(outro_total),  # 아웃트로 길이
            "-i", outro_image_path,  # 아웃트로 이미지
            "-filter_complex",
            f"[0:v]fps=30,format=yuv420p[main];"
            f"[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[outro];"
            f"[main][outro]xfade=transition=fade:duration={fade_duration}:"
            f"offset={xfade_offset}[v];"
            # 오디오는 원본 유지 (아웃트로는 무음 또는 페이드 아웃)
            f"[0:a]afade=t=out:st={xfade_offset}:d={fade_duration}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ac", "2",
            "-movflags", "+faststart",
            output_path
        ]

        logger.info(f"Adding outro: {outro_duration}s display + {fade_duration}s fade at offset {xfade_offset}s")
        self._run_ffmpeg(cmd)

        return output_path

    def _concat_clips_with_crossfade(
        self,
        clip_paths: list[str],
        target_duration: int,
        clip_durations: list[int] | None = None
    ) -> str:
        """
        클립 연결 + 크로스페이드 전환 효과 (동적 duration 지원)

        1. 각 클립의 실제 duration 사용 (고정 30초 X)
        2. xfade 필터로 부드러운 크로스페이드
        3. 클립 부족 시 루프
        """
        if not clip_paths:
            raise ValueError("No clips provided")

        # clip_durations가 없으면 기본값 사용
        if clip_durations is None:
            clip_durations = [self.DEFAULT_CLIP_DURATION] * len(clip_paths)

        output_path = str(self.temp_dir / f"concat_{uuid4()}.mp4")

        # 밝기 통일 필터 (모든 클립에 적용)
        color_filter = (
            f"eq=brightness={self.BRIGHTNESS}:contrast={self.CONTRAST}:"
            f"saturation={self.SATURATION}:gamma={self.GAMMA}"
        )

        total_clip_duration = sum(clip_durations)
        logger.info(
            f"Concat clips: {len(clip_paths)} clips, "
            f"durations: {clip_durations}, total: {total_clip_duration}s"
        )

        # 클립이 1개면 크로스페이드 없이 처리
        if len(clip_paths) == 1:
            clip_dur = clip_durations[0]
            # 클립이 target보다 짧으면 루프
            need_loop = clip_dur < target_duration
            cmd = [
                "ffmpeg", "-y",
            ]
            if need_loop:
                cmd.extend(["-stream_loop", "-1"])
            cmd.extend([
                "-i", clip_paths[0],
                "-t", str(target_duration),
                "-vf", f"fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{color_filter},format=yuv420p",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-an",
                output_path
            ])
            self._run_ffmpeg(cmd)
            return output_path

        # Step 1: 각 클립을 정규화 (실제 duration 사용, 루프 X)
        normalized_clips = []
        for i, (clip_path, clip_dur) in enumerate(zip(clip_paths, clip_durations)):
            norm_path = str(self.temp_dir / f"norm_{uuid4()}_{i}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-t", str(clip_dur),  # 실제 duration 사용
                "-vf", f"fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{color_filter},format=yuv420p",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-an",
                norm_path
            ]
            self._run_ffmpeg(cmd)
            normalized_clips.append(norm_path)

        # 클립이 2개면 xfade로 크로스페이드
        if len(normalized_clips) == 2:
            xfade_path = str(self.temp_dir / f"xfade_{uuid4()}.mp4")
            dur1, dur2 = clip_durations[0], clip_durations[1]
            fade_offset = dur1 - self.CROSSFADE_DURATION
            xfade_total = dur1 + dur2 - self.CROSSFADE_DURATION

            cmd = [
                "ffmpeg", "-y",
                "-i", normalized_clips[0],
                "-i", normalized_clips[1],
                "-filter_complex",
                f"[0:v][1:v]xfade=transition=fade:duration={self.CROSSFADE_DURATION}:offset={fade_offset},format=yuv420p[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                xfade_path
            ]
            self._run_ffmpeg(cmd)
            self._cleanup_temp(normalized_clips)

            # 필요하면 루프
            if target_duration > xfade_total:
                looped = self._loop_video(xfade_path, target_duration)
                self._cleanup_temp([xfade_path])
                return looped

            # 타겟 길이로 트림
            if target_duration < xfade_total:
                trimmed_path = str(self.temp_dir / f"trimmed_{uuid4()}.mp4")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", xfade_path,
                    "-t", str(target_duration),
                    "-c:v", "copy",
                    trimmed_path
                ]
                self._run_ffmpeg(cmd)
                self._cleanup_temp([xfade_path])
                return trimmed_path

            return xfade_path

        # 3개 이상: concat으로 연결 후 필요하면 루프
        concat_list_path = str(self.temp_dir / f"concat_list_{uuid4()}.txt")
        with open(concat_list_path, "w") as f:
            for clip in normalized_clips:
                escaped_path = clip.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        concat_raw_path = str(self.temp_dir / f"concat_raw_{uuid4()}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            concat_raw_path
        ]
        self._run_ffmpeg(cmd)
        self._cleanup_temp(normalized_clips + [concat_list_path])

        # 타겟 길이로 트림 또는 루프 (실제 total duration 사용)
        if total_clip_duration >= target_duration:
            # 트림
            cmd = [
                "ffmpeg", "-y",
                "-i", concat_raw_path,
                "-t", str(target_duration),
                "-c:v", "copy",
                output_path
            ]
            self._run_ffmpeg(cmd)
            self._cleanup_temp([concat_raw_path])
        else:
            # 루프 (총 길이가 부족할 때만)
            looped = self._loop_video(concat_raw_path, target_duration)
            self._cleanup_temp([concat_raw_path])
            return looped

        return output_path

    def _loop_video(self, video_path: str, target_duration: int) -> str:
        """영상을 루프하여 target_duration까지 채움"""
        output_path = str(self.temp_dir / f"loop_{uuid4()}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", video_path,
            "-t", str(target_duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            output_path
        ]
        self._run_ffmpeg(cmd)
        return output_path

    def _add_audio_with_bgm(
        self,
        video_path: str,
        voice_path: str,
        bgm_path: str | None,
        duration: int,
        bgm_volume: float = 0.12
    ) -> str:
        """
        음성 + BGM 믹싱

        - 음성: 100% 볼륨
        - BGM: 12% 볼륨 (배경으로 잔잔하게)
        """
        output_path = str(self.temp_dir / f"audio_{uuid4()}.mp4")

        # BGM이 없으면 음성만 추가
        if not bgm_path or not os.path.exists(bgm_path):
            # 기본 BGM 찾기 시도
            bgm_path = self._get_default_bgm()

        if bgm_path and os.path.exists(bgm_path):
            # BGM + 음성 믹싱
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
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
                output_path
            ]
        else:
            # BGM 없이 음성만
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", voice_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ac", "2",
                "-shortest",
                "-movflags", "+faststart",
                output_path
            ]

        self._run_ffmpeg(cmd)
        return output_path

    def _get_default_bgm(self) -> str | None:
        """기본 BGM 파일 찾기 (assets/bgm 폴더에서 랜덤 선택)"""
        if not self.bgm_dir.exists():
            logger.debug(f"BGM directory not found: {self.bgm_dir}")
            return None

        bgm_files = list(self.bgm_dir.glob("*.mp3")) + list(self.bgm_dir.glob("*.m4a"))
        if not bgm_files:
            logger.debug("No BGM files found")
            return None

        selected = random.choice(bgm_files)
        logger.info(f"Selected BGM: {selected.name}")
        return str(selected)

    def _add_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str
    ) -> None:
        """
        한글 자막 오버레이 (하드섭) - YouTube 스타일

        자막 스타일:
        - 폰트: NanumBarunGothic (부드러운 둥근 폰트)
        - 크기: 28pt (가독성 향상)
        - 색상: 흰색 + 두꺼운 검은색 외곽선 + 그림자
        - 배경: 반투명 검은색 박스
        - 위치: 하단 중앙
        """
        # SRT 파일 경로 이스케이프 (Windows 경로 처리)
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        # 자막 필터 (YouTube 스타일 - 부드러운 외곽선 + 반투명 배경)
        # BorderStyle=3: 외곽선 + 배경 (사각 박스보다 부드러운 느낌)
        # 글자 크기 24pt, 좌우 마진 넓게 설정하여 가로폭 확보
        subtitle_filter = (
            f"subtitles='{srt_escaped}':charenc=UTF-8:"
            f"force_style='FontName={self.KOREAN_FONT},"
            "FontSize=24,"             # 글자 크기 (28→24)
            "PrimaryColour=&HFFFFFF,"  # 흰색 텍스트
            "OutlineColour=&H40000000,"  # 진한 반투명 검은색 외곽선
            "BackColour=&H80000000,"   # 반투명 검은 배경 (50% 투명)
            "Outline=12,"              # 외곽선 두께 (넓게 - 라운드 느낌)
            "Shadow=0,"                # 그림자 제거 (깔끔하게)
            "Bold=1,"                  # 굵게
            "Italic=0,"
            "Alignment=2,"             # 하단 중앙
            "MarginV=50,"              # 하단 여백 (40→50px)
            "MarginL=100,"             # 좌측 여백 (20→100px)
            "MarginR=100,"             # 우측 여백 (20→100px)
            "BorderStyle=3'"           # 외곽선+배경 스타일 (부드러운 느낌)
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path
        ]

        self._run_ffmpeg(cmd)

    def _run_ffmpeg(self, cmd: list[str]) -> None:
        """FFmpeg 명령 실행"""
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )

            if process.returncode != 0:
                logger.error(f"FFmpeg stderr: {process.stderr}")
                raise RuntimeError(f"FFmpeg failed: {process.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg timeout (10 minutes)")

    def _cleanup_temp(self, paths: list[str]) -> None:
        """임시 파일 삭제"""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")

    def get_audio_duration(self, audio_path: str) -> int:
        """오디오 파일 길이 조회 (초)"""
        # 방법 1: format=duration 시도
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_str = result.stdout.strip()

        # N/A이거나 빈 값이면 방법 2 시도: stream duration
        if not duration_str or duration_str == "N/A":
            cmd2 = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd2, capture_output=True, text=True)
            duration_str = result.stdout.strip()

        # 여전히 N/A면 방법 3: ffmpeg로 직접 계산
        if not duration_str or duration_str == "N/A":
            cmd3 = [
                "ffprobe",
                "-v", "error",
                "-i", audio_path,
                "-show_format",
                "-print_format", "json"
            ]
            result = subprocess.run(cmd3, capture_output=True, text=True)
            import json
            try:
                data = json.loads(result.stdout)
                duration_str = data.get("format", {}).get("duration", "0")
            except json.JSONDecodeError:
                duration_str = "0"

        try:
            duration = float(duration_str)
        except ValueError:
            # 최후의 수단: 기본값 60초
            logger.warning(f"Could not determine duration for {audio_path}, using default 60s")
            duration = 60.0

        return int(duration)


# 싱글톤
_video_composer: VideoComposer | None = None


def get_video_composer() -> VideoComposer:
    """VideoComposer 싱글톤"""
    global _video_composer
    if _video_composer is None:
        _video_composer = VideoComposer()
    return _video_composer
