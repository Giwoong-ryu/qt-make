# QT Video SaaS 배포 가이드

> 최종 업데이트: 2026-01-20

---

## 📋 목차

1. [배포 전 체크리스트](#배포-전-체크리스트)
2. [환경변수 설정](#환경변수-설정)
3. [Docker 배포](#docker-배포)
4. [테스트 가이드 (결제 없이)](#테스트-가이드-결제-없이)
5. [문제 해결](#문제-해결)

---

## 배포 전 체크리스트

### ✅ 완료된 배포 준비 작업

- [x] **CORS 설정**: 환경변수 기반 (`CORS_ORIGINS`)
- [x] **환경변수 검증**: 프로덕션 필수 변수 자동 검증
- [x] **헬스 체크**: Redis, Supabase 연결 확인
- [x] **보안 헤더**: XSS, Clickjacking 방어
- [x] **로그 레벨**: 환경변수 기반 (`LOG_LEVEL=INFO`)
- [x] **의존성 버전**: 정확한 버전 고정
- [x] **리소스 제한**: Docker 메모리/CPU 제한
- [x] **로그인 기능**: 정상 작동 확인

### ⏸️ 비활성화된 기능 (추후 활성화)

- [ ] **Rate Limiting**: Docker 재빌드 후 활성화 가능
  - 파일: `backend/app/main.py` (line 30-33, 58-59, 69-71)
  - 활성화: 주석 해제 + `docker-compose build api worker`

---

## 환경변수 설정

### 1. `.env.production` 파일 생성

```bash
# 프로덕션 환경변수 템플릿
# backend/.env.production

# App
ENV=production
DEBUG=False
LOG_LEVEL=INFO

# CORS (실제 도메인으로 변경!)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# AI APIs
GROQ_API_KEY=gsk_xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
PEXELS_API_KEY=xxxxx

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=xxxxx
R2_ACCESS_KEY_ID=xxxxx
R2_SECRET_ACCESS_KEY=xxxxx
R2_BUCKET_NAME=qt-videos
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev

# Payment (PortOne) - 테스트 시 불필요
PORTONE_API_KEY=imp_xxxxx
PORTONE_API_SECRET=xxxxx

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 2. 환경변수 검증

프로덕션 시작 시 자동으로 필수 변수 검증:

```python
# backend/app/config.py:44-64
required_vars = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY"
]
```

누락 시 서버 시작 실패 + 명확한 에러 메시지 출력

---

## Docker 배포

### 1. 프로덕션 빌드

```bash
# 1. 최신 코드 Pull
git pull origin main

# 2. Docker 이미지 빌드 (멀티스테이지)
docker-compose -f docker-compose.production.yml build

# 3. 컨테이너 시작
docker-compose -f docker-compose.production.yml up -d

# 4. 로그 확인
docker-compose -f docker-compose.production.yml logs -f api
```

### 2. 헬스 체크

```bash
# API 서버 상태 확인
curl http://localhost:8000/health

# 정상 응답 예시:
{
  "status": "healthy",
  "env": "production",
  "checks": {
    "redis": "ok",
    "supabase": "ok",
    "r2": "configured"
  }
}

# 문제 발생 시:
{
  "status": "degraded",
  "checks": {
    "redis": "failed: Connection refused",
    "supabase": "ok"
  }
}
```

### 3. 리소스 제한 (현재 설정)

| 서비스 | 메모리 제한 | CPU 제한 |
|--------|-------------|----------|
| API | 4GB | 2.0 |
| Worker | 8GB | 4.0 |
| Frontend | 1GB | 1.0 |
| Redis | 512MB | 0.5 |

---

## 테스트 가이드 (결제 없이)

### 시나리오 1: 회원가입 + 무료 크레딧

**목표**: 동생이 회원가입 후 무료 크레딧으로 영상 생성 테스트

#### 1단계: 회원가입

```
URL: https://yourdomain.com/register

입력:
- 이메일: test@example.com
- 비밀번호: Test1234!
- 이름: 테스터
```

#### 2단계: 무료 크레딧 부여 (관리자 작업)

**옵션 A: Supabase 직접 수정 (빠름)**

```sql
-- Supabase SQL Editor에서 실행
UPDATE users
SET credits = 100
WHERE email = 'test@example.com';
```

**옵션 B: 가입 시 자동 부여 (코드 수정 필요)**

```python
# backend/app/routers/auth.py:register 함수에 추가
new_user = {
    "email": user.email,
    "name": user.name,
    "credits": 100,  # ← 신규 가입자 무료 크레딧
    "created_at": datetime.utcnow().isoformat()
}
```

#### 3단계: 영상 생성 테스트

```
1. 로그인
2. 대시보드 접속
3. "파일 업로드" 클릭 또는 드래그앤드롭
4. MP3/WAV/M4A 파일 선택 (테스트 파일 제공 필요)
5. 템플릿 선택 (기본값 사용)
6. "영상 생성" 버튼 클릭
7. 실시간 진행상황 확인 (3초마다 폴링)
8. 완료 후 미리보기 + 다운로드
```

#### 4단계: 크레딧 차감 확인

```sql
-- 크레딧 사용 내역 확인
SELECT * FROM users WHERE email = 'test@example.com';
-- credits 컬럼이 100 → 99 또는 90으로 감소 (영상 1개당 차감 비용)
```

---

### 시나리오 2: 결제 우회 (개발 전용)

**목표**: 결제 없이 무제한 사용

#### 방법 1: 크레딧 검증 비활성화

```python
# backend/app/routers/video.py:upload_audio 함수 수정
# 임시로 크레딧 체크 주석 처리

# if user["credits"] < CREDIT_COST:
#     raise HTTPException(status_code=402, detail="크레딧이 부족합니다")

# 크레딧 차감도 주석 처리
# supabase.table("users").update({"credits": user["credits"] - CREDIT_COST}).eq("id", user_id).execute()
```

⚠️ **주의**: 프로덕션에서는 절대 사용 금지!

#### 방법 2: 관리자 계정 생성

```sql
-- 무제한 크레딧 계정
INSERT INTO users (email, name, credits, is_admin)
VALUES ('admin@internal.com', 'Admin', 999999, true);
```

---

### 시나리오 3: 로컬 테스트 (Docker 없이)

```bash
# 1. Backend 실행
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 환경변수 설정
uvicorn app.main:app --reload

# 2. Frontend 실행
cd frontend
npm install
npm run dev

# 3. 브라우저 접속
http://localhost:3000
```

---

## 문제 해결

### 문제 1: 로그인 실패 (ERR_EMPTY_RESPONSE)

**증상**: 브라우저에서 "ERR_EMPTY_RESPONSE" 또는 "Failed to fetch"

**원인**:
1. Backend 서버 크래시
2. CORS 설정 오류
3. 환경변수 누락

**해결**:

```bash
# 1. Docker 로그 확인
docker-compose logs api --tail=50

# 2. ModuleNotFoundError 발생 시
# → Docker 이미지 재빌드
docker-compose build api worker

# 3. CORS 오류 시
# → .env.production의 CORS_ORIGINS 확인
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**현재 상태**: Rate Limiting 비활성화 (slowapi 미설치)로 로그인 정상 작동

---

### 문제 2: 헬스 체크 실패 (503)

**증상**: `/health` 엔드포인트에서 503 status

**원인**: Redis 또는 Supabase 연결 실패

**해결**:

```bash
# Redis 확인
docker-compose ps redis
docker-compose logs redis

# Supabase 연결 테스트
curl -H "apikey: YOUR_SUPABASE_KEY" \
  https://your-project.supabase.co/rest/v1/subscriptions?limit=1

# 환경변수 재확인
docker-compose exec api env | grep SUPABASE
```

---

### 문제 3: 영상 생성 실패

**증상**: "영상 생성 중..." 무한 로딩 또는 "실패" 상태

**원인**:
1. Celery Worker 미실행
2. AI API 키 오류 (Groq, Gemini)
3. R2 Storage 권한 문제

**해결**:

```bash
# 1. Worker 로그 확인
docker-compose logs worker --tail=50

# 2. Celery 작업 큐 확인
docker-compose exec worker celery -A app.celery_app inspect active

# 3. AI API 키 테스트
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models
```

---

### 문제 4: 업로드 파일 손실

**증상**: 업로드 완료 후 "파일을 찾을 수 없습니다" 에러

**원인**: Docker Volume 마운트 문제

**해결**:

```bash
# Volume 확인
docker volume ls
docker volume inspect qt-video-saas_uploads

# 권한 확인
docker-compose exec api ls -la /app/uploads

# 권한 수정
docker-compose exec api chmod 777 /app/uploads
```

---

## 배포 체크리스트 (프로덕션)

### 배포 전

- [ ] `.env.production` 모든 필수 변수 설정
- [ ] CORS_ORIGINS에 실제 도메인 추가
- [ ] DEBUG=False 확인
- [ ] LOG_LEVEL=INFO 확인
- [ ] SSL 인증서 설정 (HTTPS)
- [ ] DNS 레코드 설정
- [ ] Supabase RLS 정책 확인

### 배포 중

- [ ] `docker-compose build` 성공
- [ ] `docker-compose up -d` 성공
- [ ] `/health` 엔드포인트 200 응답
- [ ] Redis 연결 확인
- [ ] Supabase 연결 확인

### 배포 후

- [ ] 회원가입 테스트
- [ ] 로그인 테스트
- [ ] 영상 업로드 테스트
- [ ] 영상 생성 테스트
- [ ] 다운로드 테스트
- [ ] 크레딧 차감 확인
- [ ] 에러 로그 모니터링

---

## 빠른 테스트 스크립트

```bash
#!/bin/bash
# quick-test.sh

echo "=== QT Video SaaS 배포 테스트 ==="

# 1. 헬스 체크
echo "[1/5] 헬스 체크..."
curl -s http://localhost:8000/health | jq .

# 2. 회원가입 (테스트 계정)
echo "[2/5] 회원가입..."
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!",
    "name": "테스터"
  }' | jq .

# 3. 로그인
echo "[3/5] 로그인..."
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }' | jq -r .access_token)

echo "토큰: $TOKEN"

# 4. 크레딧 확인
echo "[4/5] 크레딧 확인..."
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/auth/me | jq .credits

# 5. 영상 목록 조회
echo "[5/5] 영상 목록..."
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/videos | jq '.[] | {id, title, status}'

echo "=== 테스트 완료 ==="
```

---

## 연락처

- 개발자: [이름]
- 이메일: [이메일]
- GitHub: [레포지토리 URL]
- 문제 제보: [이슈 트래커 URL]

---

## 라이선스

[라이선스 정보]
