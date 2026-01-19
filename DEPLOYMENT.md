# QT Video SaaS 배포 가이드

## 목차
1. [사전 준비](#사전-준비)
2. [환경변수 설정](#환경변수-설정)
3. [로컬 테스트](#로컬-테스트)
4. [프로덕션 배포](#프로덕션-배포)
5. [모니터링](#모니터링)
6. [트러블슈팅](#트러블슈팅)

---

## 사전 준비

### 필수 요구사항
- Docker 20.10+
- Docker Compose 2.0+
- Git
- 최소 2GB RAM, 2 CPU 코어

### 외부 서비스 계정
다음 서비스 계정을 준비하세요:

1. **Supabase** (데이터베이스)
   - https://supabase.com 가입
   - 새 프로젝트 생성
   - Settings → API → URL 및 anon key 복사

2. **Groq** (STT - Whisper)
   - https://console.groq.com 가입
   - API Keys → Create API Key

3. **Google Gemini** (AI)
   - https://ai.google.dev 가입
   - Get API Key

4. **Pexels** (배경 영상)
   - https://www.pexels.com/api 가입
   - API Key 발급 (무료: 200 requests/hour)

5. **Cloudflare R2** (파일 스토리지)
   - https://dash.cloudflare.com
   - R2 → Create Bucket
   - API Tokens 생성

6. **PortOne** (결제)
   - https://portone.io 가입
   - 스토어 생성
   - API Keys 발급

---

## 환경변수 설정

### 1. .env.production 파일 생성

```bash
# 예제 파일 복사
cp .env.production.example .env.production

# 실제 값으로 편집
nano .env.production
```

### 2. 필수 환경변수 확인

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_key

# AI APIs
GROQ_API_KEY=gsk_xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
GEMINI_API_KEY=AIzaSyxxxxx

# Media
PEXELS_API_KEY=xxxxx

# Storage
R2_ACCOUNT_ID=xxxxx
R2_ACCESS_KEY_ID=xxxxx
R2_SECRET_ACCESS_KEY=xxxxx
R2_BUCKET_NAME=qt-videos
R2_PUBLIC_URL=https://xxxxx.r2.cloudflarestorage.com

# Payment
PORTONE_API_KEY=store-xxxxx
PORTONE_API_SECRET=xxxxx
NEXT_PUBLIC_PORTONE_STORE_ID=store-xxxxx
NEXT_PUBLIC_PORTONE_CHANNEL_KEY=channel-xxxxx

# API URL (프로덕션 도메인)
NEXT_PUBLIC_API_URL=https://api.your-domain.com

# Security
JWT_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

---

## 로컬 테스트

### 개발 환경 실행

```bash
# 개발 모드 (hot reload)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 접속
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Flower: http://localhost:5555
```

### 프로덕션 모드 로컬 테스트

```bash
# 프로덕션 빌드 및 실행
docker-compose -f docker-compose.production.yml up -d --build

# 서비스 확인
curl http://localhost:8000/health
curl http://localhost:3000

# 로그 확인
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f frontend
```

---

## 프로덕션 배포

### 1. 코드 준비

```bash
# 최신 코드 pull
git pull origin main

# 의존성 확인
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

### 2. 환경변수 설정

```bash
# .env.production 파일 생성 (위 섹션 참조)
cp .env.production.example .env.production

# 실제 값으로 편집
nano .env.production
```

### 3. Docker 이미지 빌드

```bash
# 프로덕션 이미지 빌드
docker-compose -f docker-compose.production.yml build

# 빌드 확인
docker images | grep qt-video-saas
```

### 4. 서비스 시작

```bash
# 백그라운드 실행
docker-compose -f docker-compose.production.yml up -d

# 서비스 상태 확인
docker-compose -f docker-compose.production.yml ps

# 헬스체크 확인
curl http://localhost:8000/health
```

### 5. Nginx 리버스 프록시 설정 (선택사항)

```nginx
# /etc/nginx/sites-available/qt-video-saas

server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정 (영상 생성 시간 고려)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

### 6. SSL 인증서 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt-get install certbot python3-certbot-nginx

# 인증서 발급
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

---

## 모니터링

### 1. 로그 모니터링

```bash
# 전체 로그
docker-compose -f docker-compose.production.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f worker

# 최근 100줄
docker-compose -f docker-compose.production.yml logs --tail=100 api
```

### 2. Celery 작업 모니터링

```bash
# Flower 대시보드
# http://your-domain.com:5555

# Celery 작업 상태
docker-compose -f docker-compose.production.yml exec worker celery -A app.celery_app inspect active
```

### 3. 리소스 모니터링

```bash
# 컨테이너 리소스 사용량
docker stats

# 디스크 사용량
df -h
du -sh /var/lib/docker
```

### 4. Health Check

```bash
# API Health Check
curl http://localhost:8000/health

# Redis Health Check
docker-compose -f docker-compose.production.yml exec redis redis-cli ping
```

---

## 트러블슈팅

### 문제 1: 결제 모듈 에러 (REDIRECTION not supported)

**증상**: "PC환경에서 지원하지 않는 PG사 창 유형(REDIRECTION)입니다"

**해결**:
- PaymentButton.tsx의 windowType.pc를 "IFRAME"로 설정
- 브라우저 캐시 강력 새로고침 (Ctrl + Shift + R)

### 문제 2: API 404 에러

**증상**: /api/subscription/activate 404 Not Found

**해결**:
```bash
# 1. Backend 로그 확인
docker-compose logs api

# 2. Router 등록 확인
# backend/app/main.py에 router 등록되어 있는지 확인

# 3. Frontend API_URL 확인
# .env.production의 NEXT_PUBLIC_API_URL 확인
```

### 문제 3: PortOne 401 Unauthorized

**증상**: "Invalid API secret"

**해결**:
```bash
# 1. API Secret 재생성
# PortOne 콘솔 → API Keys → Delete → Create New

# 2. .env.production 업데이트
nano .env.production

# 3. 컨테이너 완전 재시작 (환경변수 reload)
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### 문제 4: 영상 생성 실패

**증상**: Celery worker에서 영상 합성 실패

**해결**:
```bash
# 1. Worker 로그 확인
docker-compose logs worker

# 2. FFmpeg 설치 확인
docker-compose exec worker ffmpeg -version

# 3. 임시 파일 공간 확인
df -h /tmp

# 4. Worker 재시작
docker-compose restart worker
```

### 문제 5: 메모리 부족

**증상**: Out of Memory 에러

**해결**:
```bash
# 1. 리소스 사용량 확인
docker stats

# 2. Docker Compose 리소스 제한 설정
# docker-compose.production.yml에 추가:
# services:
#   worker:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
#         reservations:
#           memory: 1G

# 3. 불필요한 컨테이너 정리
docker system prune -a
```

---

## 업데이트 및 롤백

### 업데이트

```bash
# 1. 최신 코드 pull
git pull origin main

# 2. 이미지 재빌드
docker-compose -f docker-compose.production.yml build

# 3. 무중단 배포
docker-compose -f docker-compose.production.yml up -d --no-deps --build api
docker-compose -f docker-compose.production.yml up -d --no-deps --build frontend
```

### 롤백

```bash
# 1. 이전 커밋으로 복귀
git log --oneline
git checkout [이전_커밋_해시]

# 2. 이미지 재빌드 및 재시작
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

## 백업 및 복구

### 데이터베이스 백업 (Supabase)

```bash
# Supabase는 자동 백업 제공
# 수동 백업:
# Supabase Dashboard → Database → Backups → Download
```

### Redis 백업

```bash
# RDB 스냅샷 저장
docker-compose exec redis redis-cli SAVE

# 백업 파일 복사
docker cp $(docker-compose ps -q redis):/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

---

## 보안 체크리스트

- [ ] API 키 환경변수로 관리 (하드코딩 금지)
- [ ] HTTPS 인증서 설정 완료
- [ ] CORS 설정 (허용 도메인만)
- [ ] JWT Secret 강력한 값 사용
- [ ] Flower 대시보드 인증 설정
- [ ] 방화벽 설정 (필요한 포트만 개방)
- [ ] 정기 보안 업데이트

---

## 연락처

문제 발생 시:
1. GitHub Issues: https://github.com/Giwoong-ryu/qt-make/issues
2. 로그 파일 첨부
3. 환경 정보 (Docker 버전, OS 등)

---

**마지막 업데이트**: 2026-01-20
