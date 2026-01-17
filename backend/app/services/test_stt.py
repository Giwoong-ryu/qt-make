"""
STT 서비스 테스트 (수동 실행용)
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.stt import get_whisper_service


async def test_transcribe():
    """테스트: MP3 → SRT 변환"""
    # 테스트용 MP3 파일 경로 (실제 파일로 교체 필요)
    test_audio = "/tmp/test_qt.mp3"

    if not Path(test_audio).exists():
        print(f"❌ 테스트 파일이 없습니다: {test_audio}")
        print("형님 교회 QT MP3 파일을 /tmp/test_qt.mp3로 복사해주세요.")
        return

    print(f"🎤 음성 인식 시작: {test_audio}")

    service = get_whisper_service()
    srt_path = await service.transcribe_to_srt(test_audio, language="ko")

    print(f"✅ SRT 파일 생성 완료: {srt_path}")

    # SRT 내용 출력 (처음 5줄)
    with open(srt_path, encoding="utf-8") as f:
        lines = f.readlines()
        print("\n📄 SRT 미리보기:")
        print("".join(lines[:10]))


if __name__ == "__main__":
    asyncio.run(test_transcribe())
