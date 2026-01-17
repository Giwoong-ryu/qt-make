"""
Cloudflare R2 스토리지 서비스
"""
import logging
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.client import Config

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class R2Storage:
    """Cloudflare R2 스토리지 서비스 (S3 호환)"""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"}
            ),
            region_name="auto"  # R2는 region 불필요
        )
        self.bucket = settings.R2_BUCKET_NAME

    def upload_file(
        self,
        file_path: str,
        folder: str = "videos",
        content_type: str | None = None
    ) -> str:
        """
        파일 업로드

        Args:
            file_path: 로컬 파일 경로
            folder: R2 폴더 (videos, audio, srt)
            content_type: MIME 타입

        Returns:
            R2 URL
        """
        try:
            file_name = Path(file_path).name
            key = f"{folder}/{uuid4()}_{file_name}"

            # Content-Type 자동 감지
            if content_type is None:
                content_type = self._guess_content_type(file_path)

            logger.info(f"Uploading to R2: {key}")

            with open(file_path, "rb") as f:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=f,
                    ContentType=content_type
                )

            # Public URL 반환
            # R2_PUBLIC_URL이 설정되면 Public URL 사용, 아니면 Presigned URL 생성
            if settings.R2_PUBLIC_URL:
                url = f"{settings.R2_PUBLIC_URL}/{key}"
            else:
                # Presigned URL 사용 (7일 유효 - R2 최대)
                url = self.generate_presigned_url(key, expires_in=604800)
            logger.info(f"Upload complete: {url}")

            return url

        except Exception as e:
            logger.exception(f"R2 upload failed: {e}")
            raise

    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """
        다운로드용 Presigned URL 생성

        Args:
            key: R2 객체 키
            expires_in: 만료 시간 (초, 기본 1시간)

        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key
                },
                ExpiresIn=expires_in
            )
            return url

        except Exception as e:
            logger.exception(f"Presigned URL generation failed: {e}")
            raise

    def generate_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600
    ) -> str:
        """
        업로드용 Presigned URL 생성 (프론트엔드 직접 업로드)

        Args:
            key: R2 객체 키
            content_type: MIME 타입
            expires_in: 만료 시간 (초)

        Returns:
            Presigned PUT URL
        """
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=expires_in
            )
            return url

        except Exception as e:
            logger.exception(f"Presigned upload URL failed: {e}")
            raise

    def delete_file(self, key: str) -> None:
        """파일 삭제"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted from R2: {key}")

        except Exception as e:
            logger.warning(f"R2 delete failed: {e}")

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        바이트 데이터 직접 업로드

        Args:
            data: 바이트 데이터
            key: R2 객체 키
            content_type: MIME 타입

        Returns:
            R2 URL
        """
        try:
            logger.info(f"Uploading bytes to R2: {key}")

            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )

            # Public URL 반환
            if settings.R2_PUBLIC_URL:
                url = f"{settings.R2_PUBLIC_URL}/{key}"
            else:
                url = self.generate_presigned_url(key, expires_in=604800)

            logger.info(f"Bytes upload complete: {url}")
            return url

        except Exception as e:
            logger.exception(f"R2 bytes upload failed: {e}")
            raise

    def upload_text(
        self,
        text: str,
        key: str,
        content_type: str = "text/plain"
    ) -> str:
        """
        텍스트 데이터 업로드

        Args:
            text: 텍스트 내용
            key: R2 객체 키
            content_type: MIME 타입

        Returns:
            R2 URL
        """
        return self.upload_bytes(text.encode("utf-8"), key, content_type)

    def download_text(self, url_or_key: str) -> str | None:
        """
        R2에서 텍스트 파일 다운로드

        Args:
            url_or_key: R2 URL 또는 객체 키

        Returns:
            텍스트 내용 (실패 시 None)
        """
        try:
            # URL에서 키 추출
            key = self._extract_key_from_url(url_or_key)

            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return content

        except Exception as e:
            logger.warning(f"R2 download failed: {e}")
            return None

    def download_bytes(self, url_or_key: str) -> bytes | None:
        """
        R2에서 바이트 데이터 다운로드

        Args:
            url_or_key: R2 URL 또는 객체 키

        Returns:
            바이트 데이터 (실패 시 None)
        """
        try:
            key = self._extract_key_from_url(url_or_key)

            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read()
            return content

        except Exception as e:
            logger.warning(f"R2 download failed: {e}")
            return None

    def _extract_key_from_url(self, url_or_key: str) -> str:
        """URL에서 객체 키 추출"""
        if url_or_key.startswith("http"):
            # R2_PUBLIC_URL이 설정된 경우
            if settings.R2_PUBLIC_URL and url_or_key.startswith(settings.R2_PUBLIC_URL):
                return url_or_key.replace(f"{settings.R2_PUBLIC_URL}/", "")
            # Presigned URL인 경우 (버킷/키 부분 추출)
            # https://xxx.r2.cloudflarestorage.com/bucket/key?...
            from urllib.parse import urlparse
            parsed = urlparse(url_or_key)
            # path: /bucket/key 또는 /key
            path = parsed.path.lstrip("/")
            if path.startswith(self.bucket):
                return path.replace(f"{self.bucket}/", "", 1)
            return path
        return url_or_key

    @staticmethod
    def _guess_content_type(file_path: str) -> str:
        """파일 확장자로 Content-Type 추측"""
        ext = Path(file_path).suffix.lower()
        types = {
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".srt": "text/plain",
            ".txt": "text/plain",
            ".json": "application/json"
        }
        return types.get(ext, "application/octet-stream")


# 싱글톤
_r2_storage: R2Storage | None = None


def get_r2_storage() -> R2Storage:
    """R2Storage 싱글톤"""
    global _r2_storage
    if _r2_storage is None:
        _r2_storage = R2Storage()
    return _r2_storage
