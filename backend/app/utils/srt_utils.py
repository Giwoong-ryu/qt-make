"""
SRT 자막 파일 유틸리티
"""
import re
from io import StringIO


def parse_srt(srt_content: str) -> list[dict]:
    """
    SRT 파일 내용을 파싱하여 자막 세그먼트 리스트 반환

    Args:
        srt_content: SRT 파일 내용 (문자열)

    Returns:
        [{"id": 1, "start": 0.0, "end": 2.5, "text": "자막 내용"}, ...]
    """
    subtitles = []

    # SRT 블록 패턴: 번호, 시간, 텍스트
    pattern = re.compile(
        r'(\d+)\s*\n'  # 번호
        r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*'  # 시작 시간
        r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*\n'  # 끝 시간
        r'((?:(?!\n\n|\n\d+\n).)*)',  # 텍스트 (다음 블록 전까지)
        re.DOTALL
    )

    for match in pattern.finditer(srt_content):
        idx = int(match.group(1))

        # 시작 시간 계산 (초 단위)
        start = (
            int(match.group(2)) * 3600 +  # 시
            int(match.group(3)) * 60 +     # 분
            int(match.group(4)) +           # 초
            int(match.group(5)) / 1000      # 밀리초
        )

        # 끝 시간 계산 (초 단위)
        end = (
            int(match.group(6)) * 3600 +
            int(match.group(7)) * 60 +
            int(match.group(8)) +
            int(match.group(9)) / 1000
        )

        # 텍스트 정리 (줄바꿈 유지)
        text = match.group(10).strip()

        subtitles.append({
            "id": idx,
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text
        })

    return subtitles


def generate_srt(subtitles: list[dict]) -> str:
    """
    자막 세그먼트 리스트를 SRT 형식 문자열로 변환

    Args:
        subtitles: [{"id": 1, "start": 0.0, "end": 2.5, "text": "자막 내용"}, ...]

    Returns:
        SRT 형식 문자열
    """
    output = StringIO()

    for i, sub in enumerate(subtitles, 1):
        # 번호 (원본 id 대신 순서대로)
        output.write(f"{i}\n")

        # 시간 변환
        start_time = _seconds_to_srt_time(sub.get("start", 0))
        end_time = _seconds_to_srt_time(sub.get("end", 0))
        output.write(f"{start_time} --> {end_time}\n")

        # 텍스트
        output.write(f"{sub.get('text', '')}\n\n")

    return output.getvalue()


def _seconds_to_srt_time(seconds: float) -> str:
    """
    초 단위를 SRT 시간 형식으로 변환

    Args:
        seconds: 초 단위 시간 (예: 65.5)

    Returns:
        SRT 시간 형식 (예: "00:01:05,500")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def validate_subtitles(subtitles: list[dict]) -> tuple[bool, str]:
    """
    자막 데이터 유효성 검증

    Returns:
        (is_valid, error_message)
    """
    if not subtitles:
        return True, ""  # 빈 자막도 유효

    for i, sub in enumerate(subtitles):
        # 필수 필드 확인
        if "start" not in sub or "end" not in sub or "text" not in sub:
            return False, f"자막 {i+1}: 필수 필드 누락"

        # 시간 유효성
        if sub["start"] < 0:
            return False, f"자막 {i+1}: 시작 시간이 음수입니다"

        if sub["end"] <= sub["start"]:
            return False, f"자막 {i+1}: 끝 시간이 시작 시간보다 작거나 같습니다"

        # 텍스트 길이
        if len(sub["text"]) > 500:
            return False, f"자막 {i+1}: 텍스트가 너무 깁니다 (최대 500자)"

    # 시간 순서 확인
    for i in range(1, len(subtitles)):
        if subtitles[i]["start"] < subtitles[i-1]["end"]:
            return False, f"자막 {i+1}: 이전 자막과 시간이 겹칩니다"

    return True, ""
