"""
썸네일 생성 서비스
컨셉 기반 썸네일 + 제목 오버레이
"""
import logging
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 프론트엔드 폰트명 -> 백엔드 폰트 파일 매핑
# Google Fonts를 backend/app/fonts/ 에 다운로드하여 사용
FONT_MAPPING = {
    # 고딕 계열
    "Do Hyeon": "DoHyeon-Regular.ttf",
    "Noto Sans KR": "NotoSansKR-Regular.ttf",
    "Nanum Gothic": "NotoSansKR-Regular.ttf",  # 대체
    "Gothic A1": "NotoSansKR-Regular.ttf",  # 대체
    "IBM Plex Sans KR": "NotoSansKR-Regular.ttf",  # 대체
    "Jua": "NotoSansKR-Regular.ttf",  # 대체
    "Pretendard": "NotoSansKR-Regular.ttf",  # 대체
    "Spoqa Han Sans Neo": "NotoSansKR-Regular.ttf",  # 대체
    # 명조/세리프 계열 -> Noto Sans로 대체
    "Hahmlet": "NotoSansKR-Regular.ttf",
    "Nanum Myeongjo": "NotoSansKR-Regular.ttf",
    "Noto Serif KR": "NotoSansKR-Regular.ttf",
    "Gowun Batang": "NotoSansKR-Regular.ttf",
    # 손글씨/디스플레이 -> 도현 또는 Noto Sans로 대체
    "Nanum Pen Script": "DoHyeon-Regular.ttf",
    "Nanum Brush Script": "DoHyeon-Regular.ttf",
    "Gamja Flower": "DoHyeon-Regular.ttf",
    "Hi Melody": "DoHyeon-Regular.ttf",
    "Poor Story": "DoHyeon-Regular.ttf",
    "Gaegu": "DoHyeon-Regular.ttf",
    "Black Han Sans": "DoHyeon-Regular.ttf",
    "Gugi": "DoHyeon-Regular.ttf",
}

# 폰트 파일 디렉토리
FONTS_DIR = Path(__file__).parent.parent / "fonts"


def _get_font_path_for_family(font_family: str | None = None) -> str:
    """프론트엔드에서 지정한 폰트 또는 기본 폰트 경로 반환"""
    # 1. 프론트엔드 지정 폰트가 있으면 매핑에서 찾기
    if font_family and font_family in FONT_MAPPING:
        font_file = FONTS_DIR / FONT_MAPPING[font_family]
        if font_file.exists():
            return str(font_file).replace("\\", "/")

    # 2. 기본 폰트 (Noto Sans KR)
    default_font = FONTS_DIR / "NotoSansKR-Regular.ttf"
    if default_font.exists():
        return str(default_font).replace("\\", "/")

    # 3. 폴백: 시스템 폰트
    return _get_system_font_path()


def _get_system_font_path() -> str:
    """OS 시스템 폰트 경로 반환 (폴백용)"""
    system = platform.system()

    if system == "Windows":
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
        ]
    elif system == "Darwin":
        font_paths = [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/NanumGothic.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in font_paths:
        if os.path.exists(path):
            return path
    return ""


# 기존 함수 호환성 유지
def _get_font_path() -> str:
    """OS에 맞는 한글 폰트 경로 반환 (기존 호환)"""
    return _get_font_path_for_family(None)


class ThumbnailGenerator:
    """컨셉 기반 썸네일 생성 서비스"""

    # 썸네일 크기 (YouTube 권장)
    WIDTH = 1280
    HEIGHT = 720

    # 기본 폰트 설정
    DEFAULT_FONT = "NanumBarunGothic"
    FALLBACK_FONT = "NanumGothic"

    # 텍스트 위치별 Y 좌표 (h=720 기준)
    TEXT_POSITIONS = {
        "top": 120,
        "center": 360,
        "bottom": 600
    }

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "qt-thumbnails"
        self.temp_dir.mkdir(exist_ok=True)

    def generate_thumbnail(
        self,
        background_image_path: str,
        title: str,
        text_color: str = "#FFFFFF",
        text_position: str = "center",
        overlay_opacity: float = 0.3,
        logo_path: str | None = None,
        logo_position: str = "bottom-right"
    ) -> str:
        """
        배경 이미지 + 제목 텍스트로 썸네일 생성

        Args:
            background_image_path: 배경 이미지 경로 (로컬 또는 URL)
            title: 표시할 제목 텍스트
            text_color: 텍스트 색상 (#FFFFFF)
            text_position: 텍스트 위치 (top, center, bottom)
            overlay_opacity: 어두운 오버레이 투명도 (0.0-1.0)
            logo_path: 로고 이미지 경로 (옵션)
            logo_position: 로고 위치

        Returns:
            생성된 썸네일 파일 경로
        """
        text_file_path = None

        try:
            output_path = str(self.temp_dir / f"thumb_{uuid4()}.jpg")

            # 제목 줄바꿈 처리 (긴 제목은 2줄로)
            formatted_title = self._format_title(title)

            # FFmpeg 필터 구성 (textfile 방식으로 한글 지원)
            filter_complex, text_file_path = self._build_filter_complex_textfile(
                formatted_title,
                text_color,
                text_position,
                overlay_opacity,
                logo_path,
                logo_position
            )

            # FFmpeg 명령 구성
            cmd = [
                "ffmpeg", "-y",
                "-i", background_image_path,
            ]

            # 로고가 있으면 입력 추가
            if logo_path and os.path.exists(logo_path):
                cmd.extend(["-i", logo_path])

            cmd.extend([
                "-vf", filter_complex,
                "-q:v", "2",
                output_path
            ])

            logger.info(f"Generating thumbnail: {title[:30]}...")
            self._run_ffmpeg(cmd)

            if os.path.exists(output_path):
                logger.info(f"Thumbnail created: {output_path}")
                return output_path
            else:
                raise RuntimeError("Thumbnail file not created")

        except Exception as e:
            logger.exception(f"Thumbnail generation failed: {e}")
            raise

        finally:
            # 임시 텍스트 파일 정리
            if text_file_path and os.path.exists(text_file_path):
                try:
                    os.remove(text_file_path)
                except Exception:
                    pass

    def _format_title(self, title: str, max_chars_per_line: int = 15) -> str:
        """
        제목을 적절한 길이로 줄바꿈

        Args:
            title: 원본 제목
            max_chars_per_line: 줄당 최대 글자 수

        Returns:
            줄바꿈 처리된 제목
        """
        title = title.strip()

        # 사용자가 이미 줄바꿈을 입력한 경우 그대로 유지
        if "\n" in title:
            return title

        # 짧은 제목은 그대로
        if len(title) <= max_chars_per_line:
            return title

        # 공백 기준으로 분할
        words = title.split()
        if len(words) <= 1:
            # 공백 없으면 중간에서 자르기
            mid = len(title) // 2
            return title[:mid] + "\n" + title[mid:]

        # 균등하게 2줄로 분배
        lines = []
        current_line = ""

        for word in words:
            test_line = (current_line + " " + word).strip()
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # 최대 2줄
        if len(lines) > 2:
            lines = [lines[0], " ".join(lines[1:])]
            # 2번째 줄이 너무 길면 자르기
            if len(lines[1]) > max_chars_per_line + 5:
                lines[1] = lines[1][:max_chars_per_line + 2] + "..."

        return "\n".join(lines)

    def _build_filter_complex(
        self,
        title: str,
        text_color: str,
        text_position: str,
        overlay_opacity: float,
        logo_path: str | None,
        logo_position: str
    ) -> str:
        """
        FFmpeg filter_complex 문자열 생성
        """
        filters = []

        # 1. 크기 조정
        filters.append(
            f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
        )

        # 2. 어두운 오버레이 (가독성 향상)
        if overlay_opacity > 0:
            # colorkey로 검은색 오버레이 추가
            filters.append(
                f"drawbox=x=0:y=0:w={self.WIDTH}:h={self.HEIGHT}:"
                f"color=black@{overlay_opacity}:t=fill"
            )

        # 3. 제목 텍스트
        y_pos = self.TEXT_POSITIONS.get(text_position, 360)

        # 색상 변환 (#FFFFFF -> 0xFFFFFF)
        ffmpeg_color = text_color.replace("#", "0x")

        # 텍스트에서 특수문자 이스케이프
        escaped_title = self._escape_text(title)

        # drawtext 필터
        font_path = _get_font_path()
        font_setting = f"fontfile='{font_path}':" if font_path else ""

        filters.append(
            f"drawtext=text='{escaped_title}':"
            f"{font_setting}"
            f"fontsize=56:"
            f"fontcolor={ffmpeg_color}:"
            f"borderw=3:"
            f"bordercolor=black:"
            f"shadowcolor=black@0.5:"
            f"shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:"
            f"y={y_pos}-text_h/2"
        )

        return ",".join(filters)

    def _build_filter_complex_textfile(
        self,
        title: str,
        text_color: str,
        text_position: str,
        overlay_opacity: float,
        logo_path: str | None,
        logo_position: str
    ) -> tuple[str, str | None]:
        """
        FFmpeg filter_complex 문자열 생성 (textfile 방식으로 한글 지원)

        Returns:
            tuple[str, str | None]: (filter_complex 문자열, 임시 텍스트 파일 경로)
        """
        import tempfile

        filters = []
        text_file_path = None

        # 1. 크기 조정
        filters.append(
            f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
        )

        # 2. 어두운 오버레이 (가독성 향상)
        if overlay_opacity > 0:
            filters.append(
                f"drawbox=x=0:y=0:w={self.WIDTH}:h={self.HEIGHT}:"
                f"color=black@{overlay_opacity}:t=fill"
            )

        # 3. 제목 텍스트 (textfile 방식)
        y_pos = self.TEXT_POSITIONS.get(text_position, 360)

        # 색상 변환 (#FFFFFF -> 0xFFFFFF)
        ffmpeg_color = text_color.replace("#", "0x")

        # 텍스트를 UTF-8 파일로 저장 (Windows 한글 인코딩 문제 방지)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_file:
            txt_file.write(title)
            text_file_path = txt_file.name

        # Windows 경로를 FFmpeg 형식으로 변환 (백슬래시 → 포워드슬래시)
        ffmpeg_text_path = text_file_path.replace("\\", "/")

        # drawtext 필터 (textfile 사용)
        font_path = _get_font_path()
        font_setting = f"fontfile='{font_path}':" if font_path else ""

        filters.append(
            f"drawtext=textfile='{ffmpeg_text_path}':"
            f"{font_setting}"
            f"fontsize=56:"
            f"fontcolor={ffmpeg_color}:"
            f"borderw=3:"
            f"bordercolor=black:"
            f"shadowcolor=black@0.5:"
            f"shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:"
            f"y={y_pos}-text_h/2"
        )

        return ",".join(filters), text_file_path

    def _escape_text(self, text: str) -> str:
        """FFmpeg drawtext용 텍스트 이스케이프"""
        # 특수문자 이스케이프
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text

    def _run_ffmpeg(self, cmd: list) -> None:
        """FFmpeg 명령 실행 (Windows UTF-8 인코딩 지원)"""
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        try:
            # Windows에서 UTF-8 인코딩 문제 방지: text=False로 bytes 처리
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # bytes로 받아서 직접 디코딩
                timeout=60
            )

            # returncode로만 성공 여부 판단 (stderr는 정보 메시지도 포함)
            if process.returncode != 0:
                logger.error(f"FFmpeg failed with code {process.returncode}")
                # stderr를 UTF-8로 디코딩 (실패 시 대체 문자 사용)
                stderr_text = process.stderr.decode('utf-8', errors='replace') if process.stderr else ""
                # stderr에서 실제 에러 부분만 추출
                error_lines = [
                    line for line in stderr_text.split('\n')
                    if 'error' in line.lower() or 'failed' in line.lower()
                ]
                error_msg = '\n'.join(error_lines) if error_lines else "Unknown error"
                raise RuntimeError(f"FFmpeg failed: {error_msg}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg timeout")

    def generate_from_template(
        self,
        template: dict[str, Any],
        title: str,
        church_settings: dict[str, Any] | None = None
    ) -> str:
        """
        템플릿 정보로 썸네일 생성

        Args:
            template: thumbnail_templates 레코드
            title: 표시할 제목
            church_settings: 교회별 커스텀 설정 (옵션)

        Returns:
            생성된 썸네일 파일 경로
        """
        # 기본값
        text_color = template.get("text_color", "#FFFFFF")
        text_position = template.get("text_position", "center")
        overlay_opacity = template.get("overlay_opacity", 0.3)

        # 교회 설정 오버라이드
        logo_path = None
        logo_position = "bottom-right"

        if church_settings:
            if church_settings.get("custom_text_color"):
                text_color = church_settings["custom_text_color"]
            if church_settings.get("logo_url"):
                logo_path = church_settings["logo_url"]
                logo_position = church_settings.get("logo_position", "bottom-right")

        return self.generate_thumbnail(
            background_image_path=template["image_url"],
            title=title,
            text_color=text_color,
            text_position=text_position,
            overlay_opacity=overlay_opacity,
            logo_path=logo_path,
            logo_position=logo_position
        )

    def generate_thumbnail_with_textboxes(
        self,
        background_image_path: str,
        text_boxes: list[dict],
        overlay_opacity: float = 0.3,
        output_size: tuple[int, int] = (1920, 1080),
    ) -> str:
        """
        범용 텍스트박스 기반 썸네일 생성 (UTF-8 textfile 방식)

        프론트엔드에서 전달된 text_boxes 배열을 그대로 렌더링합니다.
        ID에 의존하지 않고, 각 텍스트박스의 위치/크기/색상 속성을 사용합니다.

        Args:
            background_image_path: 배경 이미지 경로
            text_boxes: 텍스트박스 배열
                [
                    {
                        "id": "main",  # 참고용 (렌더링에 사용 안 함)
                        "text": "말씀좋아",
                        "x": 50,       # % 단위 (0-100)
                        "y": 15,       # % 단위 (0-100)
                        "fontSize": 72,
                        "color": "#FFFFFF",
                        "visible": true
                    },
                    ...
                ]
            overlay_opacity: 배경 어둡게 처리 (0.0-1.0)
            output_size: 출력 크기 (width, height)

        Returns:
            생성된 썸네일 파일 경로
        """
        text_files_to_cleanup = []

        try:
            width, height = output_size
            output_path = str(self.temp_dir / f"qt_thumb_{uuid4()}.jpg")

            font_path = _get_font_path()

            filters = []

            # 1. 크기 조정
            filters.append(
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

            # 2. 어두운 오버레이
            if overlay_opacity > 0:
                filters.append(
                    f"drawbox=x=0:y=0:w={width}:h={height}:"
                    f"color=black@{overlay_opacity}:t=fill"
                )

            # 로그에 텍스트박스 정보 출력
            visible_boxes = [b for b in text_boxes if b.get("visible", True) and b.get("text")]
            logger.info(f"Generating thumbnail with {len(visible_boxes)} text boxes")

            # 3. 각 텍스트박스 렌더링 (visible=true인 것만) - textfile 방식
            import tempfile

            # FFmpeg용 경로 변환 함수 (Windows 경로 → FFmpeg 호환)
            # 백슬래시 → 포워드슬래시만 변환 (콜론은 드라이브 문자용이므로 이스케이프 불필요)
            def ffmpeg_path(path: str) -> str:
                return path.replace("\\", "/")

            for box in text_boxes:
                if not box.get("visible", True):
                    continue

                text = box.get("text", "")
                if not text:
                    continue

                # 각 텍스트박스별 폰트 가져오기
                box_font_family = box.get("fontFamily")
                box_font_path = _get_font_path_for_family(box_font_family)
                ffmpeg_font_path = ffmpeg_path(box_font_path) if box_font_path else ffmpeg_path(font_path)

                logger.info(f"  - {box.get('id', 'unknown')}: {text[:30]} (font: {box_font_family} -> {box_font_path})")

                # 텍스트를 UTF-8 파일로 저장 (Windows 한글 인코딩 문제 방지)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_file:
                    txt_file.write(text)
                    text_file_path = txt_file.name
                    text_files_to_cleanup.append(text_file_path)

                # FFmpeg용 경로 변환 (백슬래시 → 포워드슬래시)
                ffmpeg_text_path = ffmpeg_path(text_file_path)

                # 위치 (% → 픽셀 변환)
                x_percent = box.get("x", 50)
                y_percent = box.get("y", 50)

                # 폰트 크기 (프론트엔드 기준 → 실제 해상도에 맞게 스케일)
                # 프론트엔드는 600px 너비 기준, 실제는 1920px
                frontend_fontsize = box.get("fontSize", 48)
                scale_factor = width / 600  # 프론트엔드 미리보기 기준
                fontsize = int(frontend_fontsize * scale_factor * 0.5)  # 0.5 보정
                fontsize = max(fontsize, 20)  # 최소 크기

                # 색상
                color = box.get("color", "#FFFFFF")
                ffmpeg_color = color.replace("#", "0x")

                # x 위치 계산 (중앙 정렬 고려)
                # x_percent가 50이면 중앙, 그 외는 해당 위치
                if 45 <= x_percent <= 55:
                    # 중앙 정렬
                    x_expr = "(w-text_w)/2"
                else:
                    # 퍼센트 위치
                    x_expr = f"w*{x_percent/100}-text_w/2"

                # y 위치 계산 (픽셀)
                y_pos = int(height * y_percent / 100)

                # drawtext 필터 (textfile 사용으로 UTF-8 한글 지원)
                # FFmpeg 호환 경로 사용 (포워드슬래시)
                filters.append(
                    f"drawtext=textfile='{ffmpeg_text_path}':"
                    f"fontfile='{ffmpeg_font_path}':"
                    f"fontsize={fontsize}:"
                    f"fontcolor={ffmpeg_color}:"
                    f"borderw=2:bordercolor=black:"
                    f"shadowcolor=black@0.5:shadowx=2:shadowy=2:"
                    f"x={x_expr}:y={y_pos}"
                )

            # filter_complex 문자열 생성 (경로는 이미 포워드슬래시로 변환됨)
            filter_string = ",".join(filters)
            logger.info(f"FFmpeg filter: {filter_string[:200]}...")

            # FFmpeg 명령 실행 (-filter_complex 직접 사용)
            cmd = [
                "ffmpeg", "-y",
                "-i", background_image_path,
                "-vf", filter_string,
                "-q:v", "2",
                output_path
            ]

            self._run_ffmpeg(cmd)

            if os.path.exists(output_path):
                logger.info(f"Thumbnail created: {output_path}")
                return output_path
            else:
                raise RuntimeError("Thumbnail file not created")

        except Exception as e:
            logger.exception(f"Thumbnail generation with textboxes failed: {e}")
            raise

        finally:
            # 임시 텍스트 파일 정리
            for txt_path in text_files_to_cleanup:
                try:
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                except Exception:
                    pass

    def generate_qt_thumbnail(
        self,
        background_image_path: str,
        main_title: str,
        sub_title: str = "",
        date_text: str = "",
        bible_verse: str = "",
        text_color: str = "#FFFFFF",
        overlay_opacity: float = 0.3,
        output_size: tuple[int, int] = (1920, 1080),
        layout: str = "classic"
    ) -> str:
        """
        QT 영상용 썸네일 생성 (성경 구절 + 날짜 + 제목)
        
        레이아웃 프리셋:
        - classic: 상단 중앙 제목 + 우측 하단 성경구절
        - minimal: 중앙에 모든 텍스트
        - modern: 왼쪽 정렬 상단 + 우측 하단 구절
        - prayer: 중앙 큰 제목 + 하단 중앙 성경구절
        - 메인 제목: 상단 중앙 (큰 글씨)
        - 서브 제목: 메인 제목 아래
        - 날짜: 서브 제목 아래
        - 성경 구절: 우측 하단
        
        Args:
            background_image_path: 배경 이미지 경로
            main_title: 메인 제목 (예: "말씀 좋아")
            sub_title: 서브 제목 (예: "말씀으로, 좋은 아침")
            date_text: 날짜 (예: "1월 12일(월)")
            bible_verse: 성경 구절 (예: "마가복음 4장 21~34절")
            text_color: 텍스트 색상
            overlay_opacity: 배경 어둡게 처리
            output_size: 출력 크기 (1920x1080 또는 1280x720)
            
        Returns:
            생성된 썸네일 파일 경로
        """
        text_files_to_cleanup = []

        try:
            width, height = output_size
            output_path = str(self.temp_dir / f"qt_thumb_{uuid4()}.jpg")

            # FFmpeg 색상 변환
            ffmpeg_color = text_color.replace("#", "0x")
            font_path = _get_font_path()
            font_setting = f"fontfile='{font_path}':" if font_path else ""

            filters = []

            # 레이아웃별 위치 설정
            layouts = {
                "classic": {  # 상단 중앙 + 우측 하단 성경구절
                    "main": {"x": "(w-text_w)/2", "y": 0.12, "size": 1.0},
                    "sub": {"x": "(w-text_w)/2", "y": 0.26, "size": 0.7},
                    "date": {"x": "(w-text_w)/2", "y": 0.38, "size": 0.55},
                    "verse": {"x": "w*0.95-text_w", "y": 0.88, "size": 0.6},
                },
                "minimal": {  # 중앙에 모든 텍스트
                    "main": {"x": "(w-text_w)/2", "y": 0.35, "size": 1.0},
                    "sub": {"x": "(w-text_w)/2", "y": 0.50, "size": 0.65},
                    "date": {"x": "(w-text_w)/2", "y": 0.62, "size": 0.5},
                    "verse": {"x": "(w-text_w)/2", "y": 0.75, "size": 0.55},
                },
                "modern": {  # 왼쪽 정렬
                    "main": {"x": "w*0.05", "y": 0.15, "size": 1.0},
                    "sub": {"x": "w*0.05", "y": 0.30, "size": 0.65},
                    "date": {"x": "w*0.05", "y": 0.42, "size": 0.5},
                    "verse": {"x": "w*0.95-text_w", "y": 0.88, "size": 0.55},
                },
                "prayer": {  # 중앙 큰 제목
                    "main": {"x": "(w-text_w)/2", "y": 0.40, "size": 1.2},
                    "sub": {"x": "(w-text_w)/2", "y": 0.55, "size": 0.6},
                    "date": {"x": "(w-text_w)/2", "y": 0.66, "size": 0.45},
                    "verse": {"x": "(w-text_w)/2", "y": 0.85, "size": 0.5},
                },
            }
            layout_cfg = layouts.get(layout, layouts["classic"])
            base_fontsize = 72 if width == 1920 else 56

            # 1. 크기 조정
            filters.append(
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

            # 2. 어두운 오버레이
            if overlay_opacity > 0:
                filters.append(
                    f"drawbox=x=0:y=0:w={width}:h={height}:"
                    f"color=black@{overlay_opacity}:t=fill"
                )

            # 헬퍼 함수: 텍스트를 UTF-8 파일로 저장하고 drawtext 필터 생성
            def add_text_filter(text: str, cfg: dict, fontsize: int, border_width: int = 2, with_shadow: bool = False):
                if not text:
                    return

                # 텍스트를 UTF-8 파일로 저장 (Windows 한글 인코딩 문제 방지)
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_file:
                    txt_file.write(text)
                    text_file_path = txt_file.name
                    text_files_to_cleanup.append(text_file_path)

                # Windows 경로를 FFmpeg 형식으로 변환
                ffmpeg_text_path = text_file_path.replace("\\", "/").replace(":", r"\:")

                y_pos = int(height * cfg["y"])
                shadow_part = "shadowcolor=black@0.5:shadowx=2:shadowy=2:" if with_shadow else ""

                filters.append(
                    f"drawtext=textfile='{ffmpeg_text_path}':"
                    f"{font_setting}"
                    f"fontsize={fontsize}:"
                    f"fontcolor={ffmpeg_color}:"
                    f"borderw={border_width}:bordercolor=black:"
                    f"{shadow_part}"
                    f"x={cfg['x']}:y={y_pos}"
                )

            # 3. 메인 제목
            if main_title:
                cfg = layout_cfg["main"]
                fontsize = int(base_fontsize * cfg["size"])
                add_text_filter(main_title, cfg, fontsize, border_width=3, with_shadow=True)

            # 4. 서브 제목
            if sub_title:
                cfg = layout_cfg["sub"]
                fontsize = int(base_fontsize * cfg["size"])
                add_text_filter(sub_title, cfg, fontsize, border_width=2, with_shadow=True)

            # 5. 날짜
            if date_text:
                cfg = layout_cfg["date"]
                fontsize = int(base_fontsize * cfg["size"])
                add_text_filter(date_text, cfg, fontsize, border_width=2, with_shadow=False)

            # 6. 성경 구절
            if bible_verse:
                cfg = layout_cfg["verse"]
                fontsize = int(base_fontsize * cfg["size"])
                add_text_filter(bible_verse, cfg, fontsize, border_width=2, with_shadow=False)

            # FFmpeg 명령 실행
            cmd = [
                "ffmpeg", "-y",
                "-i", background_image_path,
                "-vf", ",".join(filters),
                "-q:v", "2",
                output_path
            ]

            logger.info(f"Generating QT thumbnail: {main_title}")
            self._run_ffmpeg(cmd)

            if os.path.exists(output_path):
                logger.info(f"QT Thumbnail created: {output_path}")
                return output_path
            else:
                raise RuntimeError("Thumbnail file not created")

        except Exception as e:
            logger.exception(f"QT Thumbnail generation failed: {e}")
            raise

        finally:
            # 임시 텍스트 파일 정리
            for txt_path in text_files_to_cleanup:
                try:
                    if os.path.exists(txt_path):
                        os.remove(txt_path)
                except Exception:
                    pass


    def generate_outro_image(
        self,
        background_image_path: str,
        overlay_opacity: float = 0.3,
        output_size: tuple[int, int] = (1920, 1080),
    ) -> str:
        """
        아웃트로용 이미지 생성 (텍스트 없이 배경만 + 어두운 오버레이)

        인트로 썸네일과 같은 배경을 사용하되, 텍스트 없이 깔끔하게 마무리.

        Args:
            background_image_path: 배경 이미지 경로 (썸네일과 동일)
            overlay_opacity: 배경 어둡게 처리 (0.0-1.0)
            output_size: 출력 크기 (width, height)

        Returns:
            생성된 아웃트로 이미지 파일 경로
        """
        try:
            width, height = output_size
            output_path = str(self.temp_dir / f"outro_{uuid4()}.jpg")

            filters = []

            # 1. 크기 조정
            filters.append(
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

            # 2. 어두운 오버레이 (인트로와 동일한 분위기)
            if overlay_opacity > 0:
                filters.append(
                    f"drawbox=x=0:y=0:w={width}:h={height}:"
                    f"color=black@{overlay_opacity}:t=fill"
                )

            # FFmpeg 명령 실행
            cmd = [
                "ffmpeg", "-y",
                "-i", background_image_path,
                "-vf", ",".join(filters),
                "-q:v", "2",
                output_path
            ]

            logger.info(f"Generating outro image (no text)")
            self._run_ffmpeg(cmd)

            if os.path.exists(output_path):
                logger.info(f"Outro image created: {output_path}")
                return output_path
            else:
                raise RuntimeError("Outro image file not created")

        except Exception as e:
            logger.exception(f"Outro image generation failed: {e}")
            raise


# 싱글톤
_thumbnail_generator: ThumbnailGenerator | None = None


def get_thumbnail_generator() -> ThumbnailGenerator:
    """ThumbnailGenerator 싱글톤"""
    global _thumbnail_generator
    if _thumbnail_generator is None:
        _thumbnail_generator = ThumbnailGenerator()
    return _thumbnail_generator
