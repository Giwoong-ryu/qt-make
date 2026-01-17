"""
AI 자막 교정 실제 테스트
"""
import asyncio
from app.services.stt_correction import get_correction_service

async def test_ai_correction():
    """Gemini API로 실제 자막 교정 테스트"""
    service = get_correction_service()

    # 테스트 자막 (일반적인 STT 오류 포함)
    test_subtitles = [
        {"index": 1, "start": 0.0, "end": 3.5, "text": "오늘 묵상 시간에 말씀을 나누겠습니다"},
        {"index": 2, "start": 3.5, "end": 7.0, "text": "하나님께서 우리에게 은혜를 주셨습니다"},
        {"index": 3, "start": 7.0, "end": 11.0, "text": "에수님의 사랑을 느끼며 기도합시다"},  # 오타: 에수님 -> 예수님
        {"index": 4, "start": 11.0, "end": 15.0, "text": "성령의 인도하심을 따라 살아갑시다"},
        {"index": 5, "start": 15.0, "end": 19.0, "text": "오늘 말씀 본문은 요한 복은 3장입니다"},  # 오타: 복은 -> 복음
    ]

    # 교회 사전 (추가 컨텍스트)
    church_dict = [
        {"wrong_text": "묵상", "correct_text": "QT"},
    ]

    context_words = ["담임목사", "테스트교회"]

    print("=" * 60)
    print("AI 자막 교정 테스트 (Gemini 2.5 Flash)")
    print("=" * 60)

    print("\n[입력 자막]")
    for s in test_subtitles:
        print(f"  {s['index']:2}. {s['text']}")

    print("\n[AI 교정 중...]")

    try:
        result = await service.correct_subtitles(
            subtitles=test_subtitles,
            church_dictionary=church_dict,
            context_words=context_words,
            quality_mode=False  # Flash 모델 사용
        )

        print("\n[교정 결과]")
        corrections_count = 0
        for s in result:
            if s.get("correction"):
                corrections_count += 1
                c = s["correction"]
                print(f"  {s['index']:2}. [교정됨]")
                print(f"      원본: {c['original']}")
                print(f"      수정: {c['corrected']}")
                if c.get('reason'):
                    print(f"      이유: {c['reason']}")
            else:
                print(f"  {s['index']:2}. {s['text']}")

        print(f"\n[요약] 총 {len(test_subtitles)}개 중 {corrections_count}개 교정됨")
        print("[OK] AI 교정 테스트 성공!")

    except Exception as e:
        print(f"\n[FAIL] AI 교정 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_correction())
