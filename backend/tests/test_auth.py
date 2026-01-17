"""
인증 API 테스트
"""
import warnings
warnings.filterwarnings("ignore", message=".*gotrue.*deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAuthEndpoints:
    """인증 API 엔드포인트 테스트"""

    def test_signup_missing_fields(self):
        """필수 필드 누락 시 에러"""
        response = client.post("/api/auth/signup", json={
            "email": "test@test.com"
            # password 누락
        })
        assert response.status_code == 422

    def test_login_missing_fields(self):
        """로그인 필수 필드 누락"""
        response = client.post("/api/auth/login", json={
            "email": "test@test.com"
            # password 누락
        })
        assert response.status_code == 422

    def test_me_without_token(self):
        """/me 엔드포인트 - 토큰 없이 접근"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert "인증이 필요합니다" in response.json()["detail"]

    def test_me_invalid_token(self):
        """/me 엔드포인트 - 잘못된 토큰"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

    def test_me_malformed_header(self):
        """/me 엔드포인트 - 잘못된 Authorization 형식"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401
        assert "잘못된 인증 형식" in response.json()["detail"]

    def test_churches_list_public(self):
        """교회 목록 조회 (공개 API)"""
        response = client.get("/api/auth/churches")
        assert response.status_code == 200
        assert "churches" in response.json()


class TestProtectedEndpoints:
    """인증 필요 API 테스트"""

    def test_stt_correct_without_auth(self):
        """STT 교정 - 인증 없이"""
        response = client.post(
            "/api/videos/test-video/correct-subtitles",
            json={
                "subtitles": [{"index": 1, "start": 0.0, "end": 1.0, "text": "테스트"}],
                "quality_mode": False
            }
        )
        assert response.status_code == 401

    def test_dictionary_get_without_auth(self):
        """사전 조회 - 인증 없이"""
        response = client.get("/api/churches/test-church/dictionary")
        assert response.status_code == 401

    def test_stt_settings_without_auth(self):
        """STT 설정 조회 - 인증 없이"""
        response = client.get("/api/churches/test-church/stt-settings")
        assert response.status_code == 401


class TestHealthCheck:
    """헬스체크 테스트"""

    def test_root(self):
        """루트 엔드포인트"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health(self):
        """헬스체크 엔드포인트"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
