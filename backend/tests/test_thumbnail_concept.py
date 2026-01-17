"""
썸네일 컨셉 시스템 테스트
"""
from unittest.mock import Mock, patch

import pytest


class TestThumbnailCategoryAPI:
    """썸네일 카테고리 API 테스트"""

    def test_list_categories_returns_sorted_list(self, client, mock_supabase):
        """카테고리 목록이 정렬순으로 반환되는지 확인"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[
                {"id": "nature", "name": "자연/평화", "description": "평화로운 자연 풍경", "icon": "Mountain", "sort_order": 1},
                {"id": "scripture", "name": "말씀/성경", "description": "신앙 이미지", "icon": "BookOpen", "sort_order": 2},
            ]
        )

        # When
        response = client.get("/api/thumbnail/categories")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 2
        assert data["categories"][0]["id"] == "nature"

    def test_list_categories_empty(self, client, mock_supabase):
        """카테고리가 없는 경우 빈 리스트 반환"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[]
        )

        # When
        response = client.get("/api/thumbnail/categories")

        # Then
        assert response.status_code == 200
        assert response.json()["categories"] == []


class TestThumbnailTemplateAPI:
    """썸네일 템플릿 API 테스트"""

    def test_list_templates_all(self, client, mock_supabase):
        """전체 템플릿 목록 조회"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[
                {"id": "nature-001", "category_id": "nature", "name": "평화로운 호수", "image_url": "templates/nature/lake.jpg", "used_count": 10},
                {"id": "scripture-001", "category_id": "scripture", "name": "열린 성경책", "image_url": "templates/scripture/bible.jpg", "used_count": 5},
            ]
        )

        # When
        response = client.get("/api/thumbnail/templates")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 2

    def test_list_templates_by_category(self, client, mock_supabase):
        """카테고리별 템플릿 필터링"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[
                {"id": "nature-001", "category_id": "nature", "name": "평화로운 호수", "image_url": "templates/nature/lake.jpg", "used_count": 10},
            ]
        )

        # When
        response = client.get("/api/thumbnail/templates?category_id=nature")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) == 1
        assert data["templates"][0]["category_id"] == "nature"

    def test_get_template_detail(self, client, mock_supabase):
        """템플릿 상세 조회"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                "id": "nature-001",
                "category_id": "nature",
                "name": "평화로운 호수",
                "image_url": "templates/nature/lake.jpg",
                "text_color": "#FFFFFF",
                "text_position": "center",
                "overlay_opacity": 0.3,
                "used_count": 10
            }]
        )

        # When
        response = client.get("/api/thumbnail/templates/nature-001")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "nature-001"
        assert data["text_color"] == "#FFFFFF"

    def test_get_template_not_found(self, client, mock_supabase):
        """존재하지 않는 템플릿 조회"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )

        # When
        response = client.get("/api/thumbnail/templates/nonexistent")

        # Then
        assert response.status_code == 404


class TestThumbnailGenerateFromTemplate:
    """템플릿 기반 썸네일 생성 테스트"""

    def test_generate_thumbnail_success(self, client, mock_supabase, mock_r2, mock_thumbnail_generator):
        """템플릿 기반 썸네일 생성 성공"""
        # Given
        video_id = "test-video-123"
        church_id = "test-church-456"
        template_id = "nature-001"
        title = "오늘의 묵상"

        # Mock video exists
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            Mock(data=[{"id": video_id, "church_id": church_id}]),  # video query
            Mock(data=[{  # template query
                "id": template_id,
                "category_id": "nature",
                "name": "평화로운 호수",
                "image_url": "templates/nature/lake.jpg",
                "text_color": "#FFFFFF",
                "text_position": "center",
                "overlay_opacity": 0.3,
                "used_count": 5
            }]),
            Mock(data=[]),  # church_settings query
        ]

        mock_thumbnail_generator.generate_from_template.return_value = "/tmp/thumb_123.jpg"
        mock_r2.upload_file.return_value = "https://r2.example.com/thumbnails/test.jpg"

        # When
        response = client.post(
            f"/api/videos/{video_id}/thumbnail/generate-from-template",
            data={
                "template_id": template_id,
                "title": title,
                "church_id": church_id
            }
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "thumbnail_url" in data
        assert data["template_id"] == template_id
        assert data["title"] == title

    def test_generate_thumbnail_video_not_found(self, client, mock_supabase):
        """존재하지 않는 영상에 썸네일 생성 시도"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )

        # When
        response = client.post(
            "/api/videos/nonexistent/thumbnail/generate-from-template",
            data={
                "template_id": "nature-001",
                "title": "테스트",
                "church_id": "church-123"
            }
        )

        # Then
        assert response.status_code == 404

    def test_generate_thumbnail_unauthorized(self, client, mock_supabase):
        """권한 없는 교회의 영상에 썸네일 생성 시도"""
        # Given
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "video-123", "church_id": "other-church"}]
        )

        # When
        response = client.post(
            "/api/videos/video-123/thumbnail/generate-from-template",
            data={
                "template_id": "nature-001",
                "title": "테스트",
                "church_id": "my-church"
            }
        )

        # Then
        assert response.status_code == 403


class TestChurchThumbnailSettings:
    """교회 썸네일 설정 테스트"""

    def test_get_settings_existing(self, client, mock_supabase):
        """기존 설정이 있는 교회 설정 조회"""
        # Given
        church_id = "church-123"
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                "church_id": church_id,
                "default_category_id": "nature",
                "custom_text_color": "#FFD700",
                "logo_url": "https://r2.example.com/logos/church-123.png",
                "logo_position": "bottom-right"
            }]
        )

        # When
        response = client.get(f"/api/churches/{church_id}/thumbnail-settings")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["church_id"] == church_id
        assert data["default_category_id"] == "nature"
        assert data["custom_text_color"] == "#FFD700"

    def test_get_settings_default(self, client, mock_supabase):
        """설정이 없는 교회는 기본값 반환"""
        # Given
        church_id = "new-church"
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )

        # When
        response = client.get(f"/api/churches/{church_id}/thumbnail-settings")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["church_id"] == church_id
        assert data["default_category_id"] is None
        assert data["logo_position"] == "bottom-right"

    def test_update_settings(self, client, mock_supabase):
        """교회 설정 업데이트"""
        # Given
        church_id = "church-123"
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(
            data=[{
                "church_id": church_id,
                "default_category_id": "scripture",
                "custom_text_color": "#FFFFFF",
                "logo_position": "top-left"
            }]
        )

        # When
        response = client.put(
            f"/api/churches/{church_id}/thumbnail-settings",
            data={
                "default_category_id": "scripture",
                "custom_text_color": "#FFFFFF",
                "logo_position": "top-left"
            }
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["default_category_id"] == "scripture"


class TestThumbnailGeneratorService:
    """ThumbnailGenerator 서비스 단위 테스트"""

    def test_format_title_short(self):
        """짧은 제목은 그대로 반환"""
        from app.services.thumbnail import ThumbnailGenerator
        generator = ThumbnailGenerator()

        result = generator._format_title("오늘의 말씀")
        assert result == "오늘의 말씀"
        assert "\n" not in result

    def test_format_title_long_single_word(self):
        """긴 단일 단어는 중간에서 줄바꿈"""
        from app.services.thumbnail import ThumbnailGenerator
        generator = ThumbnailGenerator()

        result = generator._format_title("가나다라마바사아자차카타파하")
        assert "\n" in result

    def test_format_title_long_multiple_words(self):
        """긴 여러 단어는 균등하게 2줄로 분배"""
        from app.services.thumbnail import ThumbnailGenerator
        generator = ThumbnailGenerator()

        result = generator._format_title("오늘의 묵상 말씀을 함께 나눕니다")
        assert "\n" in result
        lines = result.split("\n")
        assert len(lines) == 2

    def test_escape_text_special_chars(self):
        """FFmpeg 특수문자 이스케이프"""
        from app.services.thumbnail import ThumbnailGenerator
        generator = ThumbnailGenerator()

        result = generator._escape_text("말씀: 100%의 진리")
        assert "\\:" in result
        assert "\\%" in result

    def test_build_filter_complex(self):
        """FFmpeg filter 문자열 생성"""
        from app.services.thumbnail import ThumbnailGenerator
        generator = ThumbnailGenerator()

        result = generator._build_filter_complex(
            title="테스트 제목",
            text_color="#FFFFFF",
            text_position="center",
            overlay_opacity=0.3,
            logo_path=None,
            logo_position="bottom-right"
        )

        assert "scale=1280:720" in result
        assert "drawtext" in result
        assert "fontcolor=0xFFFFFF" in result


# Fixtures
@pytest.fixture
def client():
    """FastAPI TestClient"""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Supabase 클라이언트 모킹"""
    with patch("app.main.supabase") as mock:
        yield mock


@pytest.fixture
def mock_r2():
    """R2 스토리지 모킹"""
    with patch("app.main.r2") as mock:
        yield mock


@pytest.fixture
def mock_thumbnail_generator():
    """ThumbnailGenerator 모킹"""
    with patch("app.main.thumbnail_generator") as mock:
        yield mock
