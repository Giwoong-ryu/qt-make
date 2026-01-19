"""
감정 빈도 분석 테스트 스크립트

실제 QT 자막 예시로 빈도 분석 시스템 검증
"""

# 테스트용 임포트 경로 설정
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.emotion_frequency_analyzer import get_emotion_analyzer

# 테스트 케이스 1: 고통 강조 QT (인간 영상 필요)
qt_pain_heavy = [
    "오늘 우리가 함께 묵상할 말씀은",
    "고통 가운데 있는 우리에게 주시는 위로입니다",
    "힘들고 괴로운 시간들",
    "외로움과 절망 속에서",
    "우리는 종종 하나님을 잃어버립니다",
    "죄와 수치심이 우리를 짓누르고",
    "두려움과 불안이 우리를 사로잡습니다",
    "연약하고 무력한 우리",
    "하지만 하나님께서는 말씀하십니다",
    "내가 너를 버리지 아니하리라",
    "네 짐을 나에게 맡기라"
]

# 테스트 케이스 2: 희망 강조 QT (밝은 자연 영상)
qt_hope_heavy = [
    "오늘 우리가 함께 묵상할 말씀은",
    "하나님의 은혜와 사랑입니다",
    "새벽이 밝아오고",
    "빛이 어둠을 이기며",
    "평안과 안식이 우리에게 임합니다",
    "감사와 기쁨으로 가득한",
    "축복받은 하루",
    "희망과 소망이 넘치는",
    "회복과 치유의 시간",
    "주님의 위로가 우리와 함께합니다"
]

# 테스트 케이스 3: 균형잡힌 QT (차분한 자연 영상)
qt_balanced = [
    "오늘 우리가 함께 묵상할 말씀은",
    "하나님과의 관계에 대한 것입니다",
    "우리는 때때로 방황하지만",
    "주님께서는 항상 우리를 인도하십니다",
    "삶의 여정 가운데",
    "우리는 배우고 성장합니다",
    "주님의 말씀을 따라",
    "한 걸음씩 나아갑니다"
]

def test_emotion_analyzer():
    """감정 빈도 분석 테스트"""
    analyzer = get_emotion_analyzer()

    print("=" * 60)
    print("감정 빈도 분석 테스트")
    print("=" * 60)

    # 테스트 1: 고통 강조
    print("\n[테스트 1] 고통 강조 QT")
    print("-" * 60)
    frequency_pain = analyzer.analyze(qt_pain_heavy)
    strategy_pain = analyzer.get_video_strategy(frequency_pain)

    print(f"전체 단어: {frequency_pain.total_words}개")
    print(f"고통 단어: {frequency_pain.pain_count}개 ({frequency_pain.pain_ratio:.1f}%)")
    print(f"희망 단어: {frequency_pain.hope_count}개 ({frequency_pain.hope_ratio:.1f}%)")
    print(f"인간 영상 필요: {frequency_pain.needs_human_video}")
    print(f"전략: {strategy_pain}")

    expected = "human"
    result = "[OK] 통과" if strategy_pain == expected else f"[FAIL] 실패 (기대: {expected})"
    print(f"결과: {result}")

    # 테스트 2: 희망 강조
    print("\n[테스트 2] 희망 강조 QT")
    print("-" * 60)
    frequency_hope = analyzer.analyze(qt_hope_heavy)
    strategy_hope = analyzer.get_video_strategy(frequency_hope)

    print(f"전체 단어: {frequency_hope.total_words}개")
    print(f"고통 단어: {frequency_hope.pain_count}개 ({frequency_hope.pain_ratio:.1f}%)")
    print(f"희망 단어: {frequency_hope.hope_count}개 ({frequency_hope.hope_ratio:.1f}%)")
    print(f"인간 영상 필요: {frequency_hope.needs_human_video}")
    print(f"전략: {strategy_hope}")

    expected = "nature_bright"
    result = "[OK] 통과" if strategy_hope == expected else f"[FAIL] 실패 (기대: {expected})"
    print(f"결과: {result}")

    # 테스트 3: 균형잡힌
    print("\n[테스트 3] 균형잡힌 QT")
    print("-" * 60)
    frequency_balanced = analyzer.analyze(qt_balanced)
    strategy_balanced = analyzer.get_video_strategy(frequency_balanced)

    print(f"전체 단어: {frequency_balanced.total_words}개")
    print(f"고통 단어: {frequency_balanced.pain_count}개 ({frequency_balanced.pain_ratio:.1f}%)")
    print(f"희망 단어: {frequency_balanced.hope_count}개 ({frequency_balanced.hope_ratio:.1f}%)")
    print(f"인간 영상 필요: {frequency_balanced.needs_human_video}")
    print(f"전략: {strategy_balanced}")

    expected = "nature_calm"
    result = "[OK] 통과" if strategy_balanced == expected else f"[FAIL] 실패 (기대: {expected})"
    print(f"결과: {result}")

    # 임계값 검증
    print("\n[임계값 검증]")
    print("-" * 60)
    print(f"고통 임계값: {analyzer.PAIN_THRESHOLD}%")
    print(f"희망 임계값: {analyzer.HOPE_THRESHOLD}%")
    print(f"\n고통 강조 케이스: {frequency_pain.pain_ratio:.1f}% {'>' if frequency_pain.pain_ratio > analyzer.PAIN_THRESHOLD else '<='} {analyzer.PAIN_THRESHOLD}%")
    print(f"희망 강조 케이스: {frequency_hope.hope_ratio:.1f}% {'>' if frequency_hope.hope_ratio > analyzer.HOPE_THRESHOLD else '<='} {analyzer.HOPE_THRESHOLD}%")
    print(f"균형잡힌 케이스: 고통 {frequency_balanced.pain_ratio:.1f}%, 희망 {frequency_balanced.hope_ratio:.1f}%")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_emotion_analyzer()
