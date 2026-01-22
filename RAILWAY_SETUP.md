# Railway 배포 가이드 (2-Service 아키텍처)

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│ Railway Project: qt-video-saas                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────┐      ┌──────────────────────┐  │
│  │ qt-make-api         │      │ qt-make-worker       │  │
│  │ (Uvicorn)           │      │ (Celery Worker)      │  │
│  │                     │      │                      │  │
│  │ - FastAPI 서버      │◄─────┤ - 영상 생성 처리     │  │
│  │ - 인증/업로드       │ Redis│ - 비동기 작업        │  │
│  │ - 작업 등록         │      │                      │  │
│  └─────────────────────┘      └──────────────────────┘  │
│           │                            │                 │
│           └────────────┬───────────────┘                 │
│                        │                                 │
│                   ┌────▼────┐                            │
│                   │ Redis   │                            │
│                   │ (Queue) │                            │
│                   └─────────┘                            │
│                                                           │
│                   ┌─────────┐                            │
│                   │Supabase │                            │
│                   │  (DB)   │                            │
│                   └─────────┘                            │
└─────────────────────────────────────────────────────────┘
```

## 1단계: Redis 서비스 추가

Railway 프로젝트에서:

1. **"New" → "Database" → "Add Redis"** 클릭
2. Redis 서비스 생성됨
3. Variables 탭에서 `REDIS_URL` 확인:
   ```
   redis://default:password@region.railway.app:port
   ```

## 2단계: API 서비스 설정 (기존 qt-make-production)

### 2-1. Settings 탭

- **Service Name**: `qt-make-api`로 변경
- **Root Directory**: `/backend`
- **Custom Start Command**: **비워두기** (Dockerfile CMD 사용)

### 2-2. Variables 탭

**필수 환경변수**:

```bash
# API 서버
PORT=8000

# CORS
CORS_ORIGINS=https://www.qt-make.com,https://qt-make.com,http://localhost:3000

# Redis (Railway Redis 연결)
REDIS_URL=${{Redis.REDIS_URL}}

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# R2 Storage
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=qt-video-storage
R2_PUBLIC_URL=https://your-bucket.r2.cloudflarestorage.com

# Pexels
PEXELS_API_KEY=your_pexels_key

# Gemini
GEMINI_API_KEY=your_gemini_key

# 환경
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# PortOne (결제)
PORTONE_API_SECRET=your_portone_secret
PORTONE_STORE_ID=your_store_id
PORTONE_CHANNEL_KEY=your_channel_key
```

**Reference Variables** (Redis 연결):
- `REDIS_URL`: `${{Redis.REDIS_URL}}` 선택

### 2-3. 도메인 연결

- **Domains** 탭 → `qt-make-production.up.railway.app` 확인

## 3단계: Worker 서비스 생성 (신규)

### 3-1. 새 서비스 생성

1. **"New" → "GitHub Repo"** 클릭
2. **같은 레포지토리** 선택: `qt-video-saas`
3. 자동 배포 시작됨

### 3-2. Settings 탭

- **Service Name**: `qt-make-worker`
- **Root Directory**: `/backend`
- **Custom Start Command**:
  ```bash
  celery -A app.celery_app worker --loglevel=info --pool=solo
  ```

### 3-3. Variables 탭

**API와 동일한 환경변수 복사** (CORS 제외):

```bash
# Redis (Railway Redis 연결)
REDIS_URL=${{Redis.REDIS_URL}}

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# R2 Storage
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=qt-video-storage
R2_PUBLIC_URL=https://your-bucket.r2.cloudflarestorage.com

# Pexels
PEXELS_API_KEY=your_pexels_key

# Gemini
GEMINI_API_KEY=your_gemini_key

# 환경
ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

**Reference Variables** (Redis 연결):
- `REDIS_URL`: `${{Redis.REDIS_URL}}` 선택

### 3-4. 도메인 불필요

Worker는 외부 접근 불필요 → Domains 설정 안 함

## 4단계: 배포

### 4-1. Git Push

```bash
git add .
git commit -m "fix(railway): 2-service architecture with separate API and Worker"
git push origin main
```

### 4-2. 배포 확인

Railway 대시보드에서:

1. **qt-make-api**:
   - Logs에서 `Application startup complete` 확인
   - Health check: `curl https://qt-make-production.up.railway.app/health`

2. **qt-make-worker**:
   - Logs에서 `celery@xxx ready` 확인

3. **Redis**:
   - Status: Running 확인

## 5단계: 테스트

### 5-1. CORS 테스트

```bash
curl -I -X OPTIONS https://qt-make-production.up.railway.app/api/auth/churches \
  -H "Origin: https://www.qt-make.com" \
  -H "Access-Control-Request-Method: GET"
```

**기대 결과**:
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://www.qt-make.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: *
```

### 5-2. 영상 생성 테스트

1. `https://www.qt-make.com` 로그인
2. 오디오 파일 업로드
3. Worker 로그에서 처리 확인:
   ```
   [2026-01-23 19:30:00] Task process_video_task[xxx] received
   [2026-01-23 19:30:05] [Step 1/7] STT 처리 중...
   ...
   [2026-01-23 19:35:30] Task process_video_task[xxx] succeeded
   ```
4. 프론트엔드에서 영상 URL 확인

## 트러블슈팅

### CORS 에러 발생 시

1. API 서비스 Variables에서 `CORS_ORIGINS` 확인
2. API 로그에서 실제 CORS 설정 확인:
   ```bash
   railway logs -s qt-make-api | grep CORS
   ```
3. 브라우저 개발자 도구 Network 탭에서 OPTIONS 요청 확인

### Worker 작업 안 될 때

1. Worker 로그 확인:
   ```bash
   railway logs -s qt-make-worker
   ```
2. Redis 연결 확인:
   - Worker 로그에서 `Connected to redis://...` 확인
3. API 로그에서 작업 등록 확인:
   ```bash
   railway logs -s qt-make-api | grep "Task sent"
   ```

### Redis 연결 실패 시

1. Redis 서비스 상태 확인 (Running?)
2. API/Worker Variables에서 `REDIS_URL` 참조 확인:
   - `${{Redis.REDIS_URL}}` 형식
3. Railway Redis는 Private Network로 연결됨 (외부 접근 불가)

## 비용 최적화

Railway 무료 플랜:
- 3 서비스 (API + Worker + Redis)
- 각 서비스당 $5 크레딧/월 = 총 $15/월
- 실제 사용량에 따라 과금

**예상 비용** (저사용량):
- API: $2-3/월
- Worker: $1-2/월 (idle 시간 많음)
- Redis: $1/월

**비용 절감**:
- Worker는 작업 있을 때만 활성화 (Railway auto-sleep)
- Redis는 작은 인스턴스 사용

## 롤백 가이드

문제 발생 시 이전 커밋으로 롤백:

```bash
# 이전 커밋 확인
git log --oneline -5

# 롤백
git reset --hard <commit-hash>
git push -f origin main
```

Railway에서 자동 재배포됨.
