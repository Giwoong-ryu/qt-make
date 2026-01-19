"""
영상 합성기 테스트 스크립트

실제 Pexels 영상 다운로드 + FFmpeg 합성 테스트
"""
# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.video_compositor import get_compositor
from app.services.video_clip_selector import SelectedClip, PexelsVideo
from app.services.fixed_segment_analyzer import SegmentStrategy


def test_video_compositor_mock():
    """영상 합성기 Mock 테스트 (실제 API 없이)"""
    print("=" * 80)
    print("영상 합성기 Mock 테스트")
    print("=" * 80)

    print("\n[WARNING] 이 테스트는 실제 Pexels API 호출이 필요합니다")
    print("[WARNING] .env에 PEXELS_API_KEY 설정 필요")
    print("\n현재는 Mock 데이터로 구조만 검증합니다\n")

    # Mock 구간 생성
    segments = [
        # 도입 (0-20초)
        SegmentStrategy(
            start_time=0.0,
            end_time=20.0,
            strategy="nature_calm",
            segment_type="fixed_intro",
            confidence=0.95
        ),
        # 중간 1 (20-50초) - human
        SegmentStrategy(
            start_time=20.0,
            end_time=50.0,
            strategy="human",
            segment_type="flexible_middle",
            confidence=0.7
        ),
        # 중간 2 (50-80초) - nature
        SegmentStrategy(
            start_time=50.0,
            end_time=80.0,
            strategy="nature_calm",
            segment_type="flexible_middle",
            confidence=0.7
        ),
        # 마무리 (80-100초)
        SegmentStrategy(
            start_time=80.0,
            end_time=100.0,
            strategy="nature_bright",
            segment_type="fixed_closing",
            confidence=0.85
        ),
    ]

    # Mock 영상 (실제 PexelsVideo 구조)
    mock_video_30s = PexelsVideo(
        id=12345,
        url='https://www.pexels.com/video/12345/',
        image_url='https://example.com/thumb_30s.jpg',
        duration=30,
        width=1920,
        height=1080,
        file_path='https://example.com/video_30s.mp4',
        quality_score=90
    )

    mock_video_17s = PexelsVideo(
        id=12346,
        url='https://www.pexels.com/video/12346/',
        image_url='https://example.com/thumb_17s.jpg',
        duration=17,
        width=1920,
        height=1080,
        file_path='https://example.com/video_17s.mp4',
        quality_score=85
    )

    mock_video_13s = PexelsVideo(
        id=12347,
        url='https://www.pexels.com/video/12347/',
        image_url='https://example.com/thumb_13s.jpg',
        duration=13,
        width=1920,
        height=1080,
        file_path='https://example.com/video_13s.mp4',
        quality_score=80
    )

    mock_video_25s = PexelsVideo(
        id=12348,
        url='https://www.pexels.com/video/12348/',
        image_url='https://example.com/thumb_25s.jpg',
        duration=25,
        width=1920,
        height=1080,
        file_path='https://example.com/video_25s.mp4',
        quality_score=88
    )

    # Mock 선택된 클립 생성
    selected_clips = [
        # 도입: 30초 영상 → 20초까지 trim
        SelectedClip(
            video=mock_video_30s,
            segment=segments[0],
            trim_duration=20.0
        ),
        # 중간 1 (human): 17초 + 13초 = 30초 (2개 조합)
        SelectedClip(
            video=mock_video_17s,
            segment=segments[1],
            trim_duration=None,
            additional_videos=[mock_video_13s]
        ),
        # 중간 2 (nature): 17초 × 2 = 34초 (반복)
        SelectedClip(
            video=mock_video_17s,
            segment=segments[2],
            trim_duration=None
        ),
        # 마무리: 25초 영상 → 그대로 재생
        SelectedClip(
            video=mock_video_25s,
            segment=segments[3],
            trim_duration=None
        ),
    ]

    print("Mock 데이터 생성 완료")
    print(f"- 구간: {len(segments)}개")
    print(f"- 선택된 클립: {len(selected_clips)}개")

    print("\n" + "-" * 80)
    print("예상 처리 과정")
    print("-" * 80)

    for idx, clip in enumerate(selected_clips, start=1):
        duration = clip.segment.end_time - clip.segment.start_time
        print(f"\n[구간 {idx}] {clip.segment.segment_type} ({duration:.1f}초)")
        print(f"  타입: {clip.segment.strategy}")

        if clip.needs_trim:
            print(f"  처리: trim ({clip.video.duration:.1f}s → {clip.trim_duration:.1f}s)")
        elif clip.is_multi_video:
            total = sum(v.duration for v in clip.all_videos)
            print(f"  처리: concat ({len(clip.all_videos)}개 영상, 총 {total:.1f}s)")
            for vid_idx, v in enumerate(clip.all_videos, start=1):
                print(f"    - 영상 {vid_idx}: {v.duration:.1f}s")
        else:
            repeat = int(duration / clip.video.duration) + 1
            print(f"  처리: loop ({clip.video.duration:.1f}s × {repeat}번)")

    print("\n" + "=" * 80)
    print("실제 테스트 방법")
    print("=" * 80)
    print("""
1. .env 파일에 API 키 설정:
   PEXELS_API_KEY=your_key

2. 실제 영상 검색 + 선택 후 합성:
   - test_full_pipeline.py 실행
   - 또는 API 엔드포인트 호출

3. FFmpeg 설치 확인:
   ffmpeg -version

4. 출력 파일 확인:
   output/final_video.mp4
""")

    print("\n" + "=" * 80)
    print("Compositor 초기화 테스트")
    print("=" * 80)

    try:
        compositor = get_compositor()
        print("[OK] Compositor 초기화 성공")
        print(f"[OK] 임시 디렉토리: {compositor.temp_dir}")
        print("[OK] FFmpeg 확인 완료")
    except RuntimeError as e:
        print(f"[FAIL] Compositor 초기화 실패: {e}")
        return

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_video_compositor_mock()
