#!/bin/bash
# PIL 텍스트 렌더링 적용 스크립트
# 영상 생성 완료 후 실행

echo "======================================"
echo "PIL 텍스트 렌더링 적용 시작"
echo "======================================"

# Step 1: PIL 코드가 포함된 브랜치로 전환 또는 파일 복원
echo ""
echo "[1/4] PIL 코드 적용 중..."

# thumbnail.py에 PIL import 추가
sed -i 's/from typing import Any$/from typing import Any, List, Tuple\nfrom PIL import Image, ImageDraw, ImageFont, ImageFilter/' backend/app/services/thumbnail.py

echo "✓ PIL import 추가 완료"

# Step 2: 컨테이너 중지 및 삭제
echo ""
echo "[2/4] 기존 컨테이너 중지 및 삭제 중..."
docker compose down

echo "✓ 컨테이너 삭제 완료"

# Step 3: 이미지 재빌드
echo ""
echo "[3/4] Docker 이미지 빌드 중 (Pillow 설치)..."
docker compose build api worker

echo "✓ 이미지 빌드 완료"

# Step 4: 컨테이너 시작
echo ""
echo "[4/4] 새 컨테이너 시작 중..."
docker compose up -d

echo "✓ 컨테이너 시작 완료"

# Step 5: 로그 확인
echo ""
echo "======================================"
echo "적용 완료!"
echo "======================================"
echo ""
echo "API 서버 로그 확인 중..."
sleep 5
docker compose logs api --tail 20

echo ""
echo "PIL이 정상적으로 로드되었는지 확인하세요."
echo "ModuleNotFoundError가 없으면 성공입니다!"
