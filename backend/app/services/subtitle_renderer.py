"""
PIL 기반 자막 렌더링 서비스

FFmpeg subtitles 필터 대신 PIL로 자막 이미지를 생성하여
더 정확한 한글 렌더링과 스타일 제어를 제공합니다.
"""
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 폰트 디렉토리
FONTS_DIR = Path(__file__).parent.parent / "fonts"


@dataclass
class SubtitleEntry:
    """SRT 자막 엔트리"""
    index: int
    start: float      # 초 단위
    end: float        # 초 단위
    text: str         # 2줄 포함 가능 (\n)


@dataclass
class SubtitleStyle:
    """자막 스타일 설정"""
    font_path: str = ""
    font_size: int = 96           # 픽셀 (1080p 기준, 매우 큰 가독성)
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 255)  # RGBA 흰색
    outline_color: Tuple[int, int, int, int] = (0, 0, 0, 200)      # 반투명 검정 외곽선
    outline_width: int = 6         # 외곽선 두께 (폰트 증가에 맞춰 조정)
    bg_color: Tuple[int, int, int, int] = (0, 0, 0, 128)           # 50% 투명 배경
    bg_padding: int = 24           # 배경 패딩 (폰트 증가에 맞춰 조정)
    bg_radius: int = 12            # 배경 모서리 둥글기
    margin_bottom: int = 150       # 하단 여백 (화면 하단 - 약 14% 위치)
    margin_horizontal: int = 100   # 좌우 여백
    line_spacing: int = 12         # 줄 간격 (폰트 증가에 맞춰 조정)
    video_width: int = 1920
    video_height: int = 1080

    def __post_init__(self):
        # 기본 폰트 경로 설정
        if not self.font_path:
            default_font = FONTS_DIR / "NotoSansKR-Regular.ttf"
            if default_font.exists():
                self.font_path = str(default_font)


class SubtitleRenderer:
    """PIL 기반 자막 렌더링 서비스"""

    def __init__(self, style: SubtitleStyle = None):
        self.style = style or SubtitleStyle()
        self.temp_dir = Path(tempfile.gettempdir()) / "qt-subtitles"
        self.temp_dir.mkdir(exist_ok=True)
        self._font = None

    def _get_font(self) -> ImageFont.FreeTypeFont:
        """폰트 로드 (캐싱)"""
        if self._font is None:
            try:
                self._font = ImageFont.truetype(
                    self.style.font_path,
                    self.style.font_size
                )
            except OSError as e:
                logger.warning(f"Font load failed: {e}, using default")
                self._font = ImageFont.load_default()
        return self._font

    def parse_srt(self, srt_path: str) -> List[SubtitleEntry]:
        """
        SRT 파일 파싱 -> SubtitleEntry 리스트

        Args:
            srt_path: SRT 파일 경로

        Returns:
            자막 엔트리 리스트
        """
        entries = []

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 빈 줄로 블록 분리
        blocks = content.strip().split('\n\n')

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    index = int(lines[0])
                    start, end = self._parse_timestamp_line(lines[1])
                    text = '\n'.join(lines[2:])
                    entries.append(SubtitleEntry(index, start, end, text))
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse subtitle block: {e}")
                    continue

        logger.info(f"Parsed {len(entries)} subtitles from {srt_path}")
        return entries

    def _parse_timestamp_line(self, line: str) -> Tuple[float, float]:
        """
        '00:00:03,500 --> 00:00:07,200' -> (3.5, 7.2)
        """
        parts = line.split(' --> ')
        if len(parts) != 2:
            raise ValueError(f"Invalid timestamp line: {line}")
        return (
            self._timestamp_to_seconds(parts[0].strip()),
            self._timestamp_to_seconds(parts[1].strip())
        )

    def _timestamp_to_seconds(self, ts: str) -> float:
        """
        '00:00:03,500' -> 3.5
        """
        # 콤마 또는 점 처리
        ts = ts.replace(',', '.')

        time_parts = ts.split(':')
        if len(time_parts) != 3:
            raise ValueError(f"Invalid timestamp: {ts}")

        h, m, s_ms = time_parts
        s_parts = s_ms.split('.')
        s = int(s_parts[0])
        ms = int(s_parts[1]) if len(s_parts) > 1 else 0

        return int(h) * 3600 + int(m) * 60 + s + ms / 1000

    def render_subtitle_image(self, text: str, output_path: str) -> str:
        """
        단일 자막 텍스트 -> 투명 배경 PNG 이미지

        자막은 화면 하단 중앙에 배치됩니다.

        Args:
            text: 자막 텍스트 (줄바꿈 포함 가능)
            output_path: 출력 PNG 경로

        Returns:
            출력 PNG 경로
        """
        style = self.style
        font = self._get_font()

        # 투명 배경 캔버스
        img = Image.new('RGBA', (style.video_width, style.video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 텍스트 크기 계산 (멀티라인 지원)
        lines = text.split('\n')
        line_bboxes = []
        total_height = 0
        max_width = 0
        first_bbox_top = None  # 첫 번째 bbox의 상단 오프셋 저장

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]

            # 첫 번째 줄의 bbox 상단 오프셋 저장 (베이스라인 보정용)
            if first_bbox_top is None:
                first_bbox_top = bbox[1]  # bbox의 y1 값

            line_bboxes.append((line_width, line_height, bbox[1]))  # y1도 저장
            max_width = max(max_width, line_width)
            total_height += line_height

        # 텍스트 실제 높이 (줄 간격 포함)
        text_height_with_spacing = total_height + style.line_spacing * (len(lines) - 1) if len(lines) > 1 else total_height

        # 배경 박스 높이 계산 (텍스트 + 위아래 패딩)
        # bg_padding이 외곽선 공간도 포함 (24px는 충분함)
        box_height = text_height_with_spacing + style.bg_padding * 2

        # 배경 박스 좌표 계산 (하단 중앙)
        bg_x1 = (style.video_width - max_width) // 2 - style.bg_padding
        bg_y1 = style.video_height - style.margin_bottom - box_height
        bg_x2 = (style.video_width + max_width) // 2 + style.bg_padding
        bg_y2 = style.video_height - style.margin_bottom

        # 배경 박스 그리기 (라운드 코너)
        self._draw_rounded_rectangle(
            draw,
            (bg_x1, bg_y1, bg_x2, bg_y2),
            radius=style.bg_radius,
            fill=style.bg_color
        )

        # 텍스트 수직 중앙 정렬
        # 박스 높이에서 텍스트 높이를 빼고 절반 = 상하 여백
        vertical_padding = (box_height - text_height_with_spacing) // 2
        # bbox의 상단 오프셋(first_bbox_top)을 빼서 베이스라인 기준으로 보정
        text_start_y = bg_y1 + vertical_padding - first_bbox_top

        # 텍스트 그리기 (외곽선 + 본문)
        current_y = text_start_y
        for i, line in enumerate(lines):
            line_width, line_height, bbox_y1 = line_bboxes[i]
            x = (style.video_width - line_width) // 2

            # 외곽선 (8방향으로 그려서 두꺼운 효과)
            self._draw_text_with_outline(
                draw, (x, current_y), line, font,
                style.text_color, style.outline_color, style.outline_width
            )

            # 마지막 줄이 아닐 때만 spacing 추가 (오버플로우 방지)
            current_y += line_height
            if i < len(lines) - 1:
                current_y += style.line_spacing

        # PNG 저장
        img.save(output_path, 'PNG')
        return output_path

    def _draw_text_with_outline(
        self,
        draw: ImageDraw.ImageDraw,
        position: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: Tuple[int, int, int, int],
        outline_color: Tuple[int, int, int, int],
        outline_width: int
    ):
        """
        외곽선이 있는 텍스트 그리기

        8방향으로 외곽선을 그려서 두꺼운 효과를 만듭니다.
        """
        x, y = position

        # 외곽선 (8방향 + 추가 각도)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                # 원형 마스크로 더 부드러운 외곽선
                if dx * dx + dy * dy <= outline_width * outline_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

        # 본문 텍스트
        draw.text((x, y), text, font=font, fill=text_color)

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        coords: Tuple[int, int, int, int],
        radius: int,
        fill: Tuple[int, int, int, int]
    ):
        """
        라운드 코너 사각형 그리기

        Args:
            draw: ImageDraw 객체
            coords: (x1, y1, x2, y2)
            radius: 코너 반지름
            fill: RGBA 색상
        """
        x1, y1, x2, y2 = coords

        # Pillow 8.2.0+ 에서는 rounded_rectangle 사용 가능
        # 하위 호환을 위해 수동 구현
        try:
            draw.rounded_rectangle(coords, radius=radius, fill=fill)
        except AttributeError:
            # 이전 버전 Pillow 호환
            # 메인 사각형
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

            # 코너 원
            draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
            draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
            draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
            draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)

    def render_all_subtitles(self, srt_path: str) -> List[Tuple[str, float, float]]:
        """
        전체 SRT -> PNG 리스트 생성

        Args:
            srt_path: SRT 파일 경로

        Returns:
            [(png_path, start_time, end_time), ...]
        """
        entries = self.parse_srt(srt_path)
        results = []

        for entry in entries:
            png_path = str(self.temp_dir / f"sub_{uuid4().hex[:8]}_{entry.index:04d}.png")
            self.render_subtitle_image(entry.text, png_path)
            results.append((png_path, entry.start, entry.end))

        logger.info(f"Rendered {len(results)} subtitle images")
        return results

    def cleanup(self, png_paths: List[str]) -> None:
        """
        임시 PNG 파일 정리

        Args:
            png_paths: 삭제할 PNG 경로 리스트
        """
        cleaned = 0
        for path in png_paths:
            try:
                p = Path(path)
                if p.exists():
                    p.unlink()
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")

        logger.debug(f"Cleaned up {cleaned}/{len(png_paths)} subtitle images")


# 싱글톤
_subtitle_renderer: SubtitleRenderer | None = None


def get_subtitle_renderer(style: SubtitleStyle = None) -> SubtitleRenderer:
    """SubtitleRenderer 싱글톤"""
    global _subtitle_renderer
    if _subtitle_renderer is None or style is not None:
        _subtitle_renderer = SubtitleRenderer(style)
    return _subtitle_renderer
