"""
썸네일 템플릿 이미지 R2 업로드 + DB 등록 스크립트
"""
import os
import sys
from pathlib import Path

import boto3

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from supabase import create_client

# .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

# 설정
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "qt-videos")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# R2 클라이언트
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

# Supabase 클라이언트
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 이미지 폴더 경로
IMAGE_DIR = Path(__file__).parent.parent.parent / "image"

# 파일명 prefix → 카테고리 매핑
# a = 촛불, b = 성경책, c = 밝은 자연, d = 어두운 자연
# t = 밝은 나무, h = 기도, n = 밝은 겨울
PREFIX_TO_CATEGORY = {
    "a": "prayer",      # 촛불 → 기도/묵상
    "b": "scripture",   # 성경책 → 말씀/성경
    "c": "nature",      # 밝은 자연 → 자연/평화
    "d": "nature",      # 어두운 자연 → 자연/평화
    "t": "nature",      # 밝은 나무 → 자연/평화
    "h": "prayer",      # 기도 → 기도/묵상
    "n": "winter",      # 밝은 겨울 → 겨울
}

# 템플릿 이름 매핑
PREFIX_TO_NAME = {
    "a": "촛불",
    "b": "성경책",
    "c": "밝은 자연",
    "d": "어두운 자연",
    "t": "밝은 나무",
    "h": "기도",
    "n": "밝은 겨울",
}

def guess_category(filename: str) -> tuple[str, str]:
    """파일명으로 카테고리와 이름 추측. (category, name) 반환"""
    # "a (2).jpg" → prefix = "a"
    prefix = filename.split(" ")[0].split(".")[0].lower()

    category = PREFIX_TO_CATEGORY.get(prefix, "nature")
    name = PREFIX_TO_NAME.get(prefix, "기타")

    return category, name

def upload_image(file_path: Path) -> str:
    """이미지를 R2에 업로드하고 URL 반환"""
    key = f"templates/{file_path.name}"

    content_type = "image/jpeg"
    if file_path.suffix.lower() == ".png":
        content_type = "image/png"

    with open(file_path, "rb") as f:
        s3.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=f,
            ContentType=content_type,
        )

    if R2_PUBLIC_URL:
        return f"{R2_PUBLIC_URL}/{key}"
    return key

def get_file_number(filename: str) -> int:
    """파일명에서 번호 추출. 'a (2).jpg' → 2, 'a.jpg' → 1"""
    import re
    match = re.search(r'\((\d+)\)', filename)
    if match:
        return int(match.group(1))
    return 1

def main():
    print(f"이미지 폴더: {IMAGE_DIR}")
    print(f"R2 버킷: {R2_BUCKET_NAME}")
    print(f"R2 Public URL: {R2_PUBLIC_URL}")
    print("-" * 50)

    # 이미지 파일 목록
    images = list(IMAGE_DIR.glob("*.jpg")) + list(IMAGE_DIR.glob("*.png"))
    print(f"발견된 이미지: {len(images)}개")

    if not images:
        print("이미지가 없습니다!")
        return

    # 카테고리별 카운터
    category_count = {}

    uploaded = 0
    for img_path in images:
        try:
            # 1. R2 업로드
            image_url = upload_image(img_path)

            # 2. 카테고리 + 이름 추측
            category, base_name = guess_category(img_path.name)

            # 3. 파일 번호 추출
            file_num = get_file_number(img_path.name)

            # 4. 카테고리별 카운터 (동일 카테고리 내 순번)
            count = category_count.get(category, 0) + 1
            category_count[category] = count

            # 5. 템플릿 ID (prefix + 파일번호로 유니크하게)
            prefix = img_path.name.split(" ")[0].split(".")[0].lower()
            template_id = f"{prefix}-{file_num:03d}"

            # 6. 템플릿 이름 (한글 이름 + 번호)
            template_name = f"{base_name} {file_num}"

            # 7. DB에 등록
            data = {
                "id": template_id,
                "category_id": category,
                "name": template_name,
                "image_url": image_url,
                "text_color": "#FFFFFF",
                "text_position": "center",
                "overlay_opacity": 0.3,
                "is_active": True,
            }

            supabase.table("thumbnail_templates").upsert(data).execute()

            uploaded += 1
            print(f"[{uploaded}/{len(images)}] {template_id}: {template_name} -> {category}")

        except Exception as e:
            print(f"[ERROR] {img_path.name}: {e}")

    print("-" * 50)
    print(f"업로드 완료: {uploaded}/{len(images)}개")
    print(f"카테고리별 개수: {category_count}")

if __name__ == "__main__":
    main()
