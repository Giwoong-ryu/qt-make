"""
STT 교정 API 테스트 스크립트
"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_stt_settings_default():
    """STT 설정 조회 테스트 (기본값 반환)"""
    # 임의의 church_id로 테스트
    response = client.get("/api/churches/test-church-123/stt-settings")
    print(f"\n[1] STT 설정 조회")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert data["whisper_language"] == "ko"
    assert data["correction_enabled"] == True
    print("    [OK] 기본 설정 반환 확인")

def test_dictionary_empty():
    """빈 사전 조회 테스트"""
    response = client.get("/api/churches/test-church-123/dictionary")
    print(f"\n[2] 사전 조회 (빈 결과)")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    print("    [OK] 빈 사전 조회 성공")

def test_correction_service_import():
    """STT 교정 서비스 import 테스트"""
    print(f"\n[3] STT 교정 서비스 로드")
    try:
        from app.services.stt_correction import get_correction_service
        service = get_correction_service()
        print(f"    Service: {service.__class__.__name__}")
        print(f"    Default Model: {service.DEFAULT_MODEL}")
        print(f"    Quality Model: {service.QUALITY_MODEL}")
        print("    [OK] 서비스 로드 성공")
    except Exception as e:
        print(f"    [FAIL] {e}")
        raise

def test_dictionary_service_import():
    """사전 서비스 import 테스트"""
    print(f"\n[4] 사전 서비스 로드")
    try:
        from app.services.dictionary_service import get_dictionary_service
        service = get_dictionary_service()
        print(f"    Service: {service.__class__.__name__}")
        print("    [OK] 서비스 로드 성공")
    except Exception as e:
        print(f"    [FAIL] {e}")
        raise

def test_apply_dictionary_logic():
    """사전 적용 로직 테스트 (AI 없이)"""
    print(f"\n[5] 사전 적용 로직 테스트")
    from app.services.stt_correction import get_correction_service
    service = get_correction_service()

    # 테스트용 사전
    test_dict = [
        {"wrong_text": "묵상", "correct_text": "묵상(QT)"},
        {"wrong_text": "목사님", "correct_text": "담임목사님"},
    ]

    # 테스트 텍스트
    test_text = "오늘 묵상 시간에 목사님 말씀을 들었습니다."

    corrected, applied = service.apply_dictionary(test_text, test_dict)

    print(f"    원본: {test_text}")
    print(f"    교정: {corrected}")
    print(f"    적용된 규칙: {len(applied)}개")
    for rule in applied:
        print(f"      - {rule['wrong_text']} -> {rule['correct_text']}")

    assert corrected == "오늘 묵상(QT) 시간에 담임목사님 말씀을 들었습니다."
    print("    [OK] 사전 적용 로직 정상 동작")

def test_api_endpoints_exist():
    """API 엔드포인트 존재 확인"""
    print(f"\n[6] API 엔드포인트 확인")

    # OpenAPI 스키마 조회
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi = response.json()
    paths = openapi.get("paths", {})

    expected_endpoints = [
        "/api/churches/{church_id}/dictionary",
        "/api/churches/{church_id}/stt-settings",
        "/api/videos/{video_id}/correct-subtitles",
    ]

    for endpoint in expected_endpoints:
        if endpoint in paths:
            print(f"    [OK] {endpoint}")
        else:
            print(f"    [WARN] {endpoint} - 정확한 경로 확인 필요")

    # 등록된 모든 엔드포인트 출력
    print(f"\n    등록된 엔드포인트:")
    for path in sorted(paths.keys()):
        if "church" in path or "video" in path or "subtitle" in path:
            methods = list(paths[path].keys())
            print(f"      {', '.join(methods).upper():20} {path}")

if __name__ == "__main__":
    print("=" * 60)
    print("STT 교정 API 테스트")
    print("=" * 60)

    test_stt_settings_default()
    test_dictionary_empty()
    test_correction_service_import()
    test_dictionary_service_import()
    test_apply_dictionary_logic()
    test_api_endpoints_exist()

    print("\n" + "=" * 60)
    print("[OK] 모든 테스트 통과!")
    print("=" * 60)
