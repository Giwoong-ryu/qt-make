FROM python:3.11-slim

# 한글 폰트 설치
RUN apt-get update && \
    apt-get install -y fonts-noto-cjk fonts-nanum fontconfig && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# FFmpeg 설치 (네트워크 이슈 시 재시도)
RUN apt-get update && \
    (apt-get install -y ffmpeg || apt-get install -y --fix-missing ffmpeg || true) && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

# 배경 클립 사전 다운로드 (빌드 시 캐싱, 실패해도 계속 진행)
RUN mkdir -p /app/background_clips && \
    python scripts/download_popular_clips.py --count 50 --output /app/background_clips || true

# 프로젝트 폰트를 시스템 폰트 디렉토리로 복사 및 캐시 업데이트 (타임아웃 방지)
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    find /app/app/fonts -name "*.ttf" -exec cp {} /usr/share/fonts/truetype/custom/ \; || true && \
    fc-cache -f || true

# 포트 노출
EXPOSE 8000

# 기본 CMD (Railway에서 서비스별로 오버라이드)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
