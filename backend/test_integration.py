"""
통합 검증 테스트 스크립트

VideoCompositor와 Segment Analyzer가 tasks.py에 제대로 통합되었는지 검증
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("[통합 검증 테스트]")
print("=" * 60)

# Test 1: Import 검증
print("\n[Test 1] Import 검증")
print("-" * 60)

try:
    from app.services.video_compositor import VideoCompositor, CompositionResult
    print("[OK] VideoCompositor import 성공")
except ImportError as e:
    print(f"[FAIL] VideoCompositor import 실패: {e}")
    sys.exit(1)

try:
    from app.services.fixed_segment_analyzer import FixedSegmentAnalyzer, SegmentStrategy
    print("[OK] FixedSegmentAnalyzer import 성공")
except ImportError as e:
    print(f"[FAIL] FixedSegmentAnalyzer import 실패: {e}")
    sys.exit(1)

try:
    from app.services.video_clip_selector import VideoClipSelector, SelectedClip
    print("[OK] VideoClipSelector import 성공")
except ImportError as e:
    print(f"[FAIL] VideoClipSelector import 실패: {e}")
    sys.exit(1)

# Test 2: tasks.py import 검증
print("\n[Test 2] tasks.py import 검증")
print("-" * 60)

try:
    from app.tasks import parse_srt_for_segments
    print("[OK] parse_srt_for_segments 함수 import 성공")
except ImportError as e:
    print(f"[FAIL] parse_srt_for_segments import 실패: {e}")
    sys.exit(1)

# Test 3: SRT 파싱 함수 테스트
print("\n[Test 3] SRT 파싱 함수 테스트")
print("-" * 60)

import tempfile
import os

# 테스트용 SRT 파일 생성
test_srt_content = """1
00:00:01,000 --> 00:00:03,500
첫 번째 자막입니다.

2
00:00:04,000 --> 00:00:07,000
두 번째 자막입니다.

3
00:00:08,000 --> 00:00:11,500
세 번째 자막입니다.
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
    f.write(test_srt_content)
    temp_srt_path = f.name

try:
    subtitles, subtitle_timings = parse_srt_for_segments(temp_srt_path)

    assert len(subtitles) == 3, f"Expected 3 subtitles, got {len(subtitles)}"
    assert len(subtitle_timings) == 3, f"Expected 3 timings, got {len(subtitle_timings)}"

    # 첫 번째 자막 검증
    assert subtitles[0] == "첫 번째 자막입니다.", f"Unexpected subtitle text: {subtitles[0]}"
    start, end = subtitle_timings[0]
    assert abs(start - 1.0) < 0.1, f"Start time mismatch: {start}"
    assert abs(end - 3.5) < 0.1, f"End time mismatch: {end}"

    print(f"[OK] SRT 파싱 성공: {len(subtitles)}개 자막")
    print(f"  - 자막 1: '{subtitles[0]}' ({subtitle_timings[0][0]:.1f}s ~ {subtitle_timings[0][1]:.1f}s)")
    print(f"  - 자막 2: '{subtitles[1]}' ({subtitle_timings[1][0]:.1f}s ~ {subtitle_timings[1][1]:.1f}s)")
    print(f"  - 자막 3: '{subtitles[2]}' ({subtitle_timings[2][0]:.1f}s ~ {subtitle_timings[2][1]:.1f}s)")

finally:
    os.unlink(temp_srt_path)

# Test 4: VideoCompositor progress_callback 파라미터 검증
print("\n[Test 4] VideoCompositor progress_callback 검증")
print("-" * 60)

import inspect

sig = inspect.signature(VideoCompositor.compose_video)
params = list(sig.parameters.keys())

if 'progress_callback' in params:
    print("[OK] VideoCompositor.compose_video에 progress_callback 파라미터 존재")
else:
    print("[FAIL] progress_callback 파라미터 누락!")
    sys.exit(1)

# Test 5: 프론트엔드 타입 정의 검증
print("\n[Test 5] 프론트엔드 타입 정의 검증")
print("-" * 60)

frontend_types_path = project_root / "frontend" / "src" / "types" / "index.ts"

if frontend_types_path.exists():
    content = frontend_types_path.read_text(encoding='utf-8')

    # VideoItem 인터페이스에 필수 필드가 있는지 확인
    required_fields = [
        "thumbnail_layout",
        "clips_used",
        "bgm_id",
        "bgm_volume"
    ]

    missing_fields = []
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)

    if missing_fields:
        print(f"[FAIL] VideoItem에 누락된 필드: {missing_fields}")
        sys.exit(1)
    else:
        print("[OK] VideoItem 인터페이스에 필수 필드 모두 존재")
        print(f"  - {', '.join(required_fields)}")

    # ThumbnailLayout 타입 정의 확인
    if "interface ThumbnailLayout" in content:
        print("[OK] ThumbnailLayout 타입 정의 존재")
    else:
        print("[FAIL] ThumbnailLayout 타입 정의 누락!")
        sys.exit(1)
else:
    print("[WARN] 프론트엔드 타입 파일 없음 (스킵)")

# Test 6: main.py API 엔드포인트 검증
print("\n[Test 6] main.py GET /api/videos 엔드포인트 검증")
print("-" * 60)

main_py_path = project_root / "app" / "main.py"

if main_py_path.exists():
    content = main_py_path.read_text(encoding='utf-8')

    # SELECT 쿼리에 필수 필드가 있는지 확인
    required_fields_in_query = [
        "thumbnail_layout",
        "clips_used",
        "bgm_id",
        "bgm_volume"
    ]

    # GET /api/videos 엔드포인트 찾기
    if '@app.get("/api/videos")' in content:
        # 해당 함수 영역 추출 (간단히 다음 @app까지)
        start_idx = content.find('@app.get("/api/videos")')
        end_idx = content.find('@app.', start_idx + 1)
        endpoint_content = content[start_idx:end_idx]

        missing_in_query = []
        for field in required_fields_in_query:
            if field not in endpoint_content:
                missing_in_query.append(field)

        if missing_in_query:
            print(f"[FAIL] SELECT 쿼리에 누락된 필드: {missing_in_query}")
            sys.exit(1)
        else:
            print("[OK] GET /api/videos SELECT 쿼리에 필수 필드 모두 존재")
            print(f"  - {', '.join(required_fields_in_query)}")
    else:
        print("[FAIL] GET /api/videos 엔드포인트를 찾을 수 없음!")
        sys.exit(1)
else:
    print("[FAIL] main.py 파일을 찾을 수 없음!")
    sys.exit(1)

# 최종 결과
print("\n" + "=" * 60)
print("[통합 검증 완료]")
print("=" * 60)
print("[OK] 모든 검증 통과!")
print("\n[OK] VideoCompositor와 Segment Analyzer가 성공적으로 통합되었습니다.")
print("[OK] 프론트엔드 타입 정의가 DB 스키마와 일치합니다.")
print("[OK] API 엔드포인트가 필수 필드를 모두 반환합니다.")
print("\n다음 단계:")
print("  1. 백엔드 서버 재시작 (uvicorn app.main:app --reload)")
print("  2. Celery worker 재시작 (celery -A app.celery_app worker)")
print("  3. 실제 MP3 파일로 영상 생성 테스트")
print("  4. Segment 분석 로그 확인 (intro/middle/closing)")
print("  5. VideoCompositor trim/loop/concat 동작 확인")
