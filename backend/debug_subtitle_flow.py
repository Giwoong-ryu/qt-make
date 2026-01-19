#!/usr/bin/env python3
"""
자막 줄바꿈 데이터 흐름 추적 도구

사용법:
    python debug_subtitle_flow.py [srt_file_path]

출력:
    - 각 단계별 텍스트 상태
    - 줄바꿈 위치 변경 추적
    - 예상 vs 실제 비교
"""
import sys
from pathlib import Path


def parse_srt(srt_path: str):
    """SRT 파일 파싱 및 분석"""
    print(f"\n{'='*80}")
    print(f"[SRT 파일 분석] {srt_path}")
    print(f"{'='*80}\n")

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 자막 블록 분리
    blocks = content.strip().split('\n\n')

    for i, block in enumerate(blocks[:5], 1):  # 처음 5개만
        lines = block.split('\n')
        if len(lines) < 3:
            continue

        index = lines[0]
        timestamp = lines[1]
        text_lines = lines[2:]

        print(f"[자막 {index}] {timestamp}")
        print(f"줄 개수: {len(text_lines)}")

        for j, line in enumerate(text_lines, 1):
            print(f"  줄 {j}: '{line}' ({len(line)}자)")

        # 줄바꿈 규칙 검증
        if len(text_lines) == 2:
            line1_len = len(text_lines[0])
            line2_len = len(text_lines[1])

            if line1_len > 16 or line2_len > 16:
                print(f"  [WARN] Netflix rule violation: over 16 chars/line (line1: {line1_len}, line2: {line2_len})")

            # Check sentence ending
            if text_lines[0].endswith(('니다', '해요', '어요', '아요', '요', '네', '죠')):
                print(f"  [OK] Line break at sentence ending: '{text_lines[0][-2:]}'")
            else:
                print(f"  [WARN] Not sentence ending: '{text_lines[0][-2:]}'")

        print()


def trace_stt_logic():
    """stt.py의 줄바꿈 로직 분석"""
    print(f"\n{'='*80}")
    print("[STT 줄바꿈 로직 분석]")
    print(f"{'='*80}\n")

    stt_path = Path(__file__).parent / "app" / "services" / "stt.py"

    with open(stt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # _group_words_into_subtitles 메서드 찾기
    in_method = False
    method_lines = []

    for i, line in enumerate(lines, 1):
        if 'def _group_words_into_subtitles' in line:
            in_method = True

        if in_method:
            method_lines.append((i, line.rstrip()))

            # 메서드 끝 감지
            if line.strip() and not line.startswith(' ') and i > method_lines[0][0]:
                break

    print("[_group_words_into_subtitles 메서드]")
    print(f"위치: stt.py:{method_lines[0][0]}-{method_lines[-1][0]}\n")

    # 줄바꿈 관련 코드만 추출
    print("[줄바꿈 로직]")
    for line_num, code in method_lines:
        if any(keyword in code for keyword in ['split', 'line', 'char', '16', 'netflix', '종결']):
            print(f"  Line {line_num}: {code}")

    print()


def compare_expected_vs_actual(srt_path: str):
    """예상 vs 실제 비교"""
    print(f"\n{'='*80}")
    print("[예상 vs 실제 비교]")
    print(f"{'='*80}\n")

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.strip().split('\n\n')
    first_block = blocks[0] if blocks else ""

    print("[실제 출력 (첫 번째 자막)]")
    print(first_block)
    print()

    print("[예상 출력 (사용자 요구)]")
    print("1")
    print("00:00:00,000 --> 00:00:03,500")
    print("하늘나라는")
    print("겨자씨 한 알과 같으니")
    print()

    # 차이점 분석
    actual_lines = first_block.split('\n')[2:]  # 텍스트 부분만
    expected_lines = ["하늘나라는", "겨자씨 한 알과 같으니"]

    print("[차이점 분석]")
    for i in range(max(len(actual_lines), len(expected_lines))):
        actual = actual_lines[i] if i < len(actual_lines) else "(없음)"
        expected = expected_lines[i] if i < len(expected_lines) else "(없음)"

        if actual == expected:
            print(f"  Line {i+1}: [OK] Match - '{actual}'")
        else:
            print(f"  Line {i+1}: [FAIL] Mismatch")
            print(f"    Actual  : '{actual}'")
            print(f"    Expected: '{expected}'")

    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        srt_file = sys.argv[1]
    else:
        # 최근 생성된 SRT 파일 자동 탐색
        storage_path = Path(__file__).parent / "storage"
        srt_files = list(storage_path.glob("**/*.srt"))

        if not srt_files:
            print("[ERROR] SRT file not found")
            print(f"Path: {storage_path}")
            sys.exit(1)

        # 최근 파일
        srt_file = str(max(srt_files, key=lambda p: p.stat().st_mtime))

    print(f"분석 대상: {srt_file}\n")

    # 1. SRT 파일 분석
    parse_srt(srt_file)

    # 2. STT 로직 분석
    trace_stt_logic()

    # 3. 예상 vs 실제 비교
    compare_expected_vs_actual(srt_file)

    print(f"\n{'='*80}")
    print("[분석 완료]")
    print(f"{'='*80}\n")
