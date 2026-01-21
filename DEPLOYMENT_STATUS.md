# 배포 진행 상황 (2026-01-21)

## ✅ 완료된 작업

### 1. Vercel 프론트엔드 배포 ✓
- **저장소**: `Giwoong-ryu/qt-make`
- **Root Directory**: `kmong_work/qt-make/qt-video-saas/frontend`
- **도메인**: https://qt-make.com
- **DNS 설정**:
  ```
  Type: A
  Name: @
  Value: 76.76.21.21
  Status: ✓ 설정 완료
  ```
- **상태**: 배포 성공, DNS 전파 대기 중 (10-30분 소요)

### 2. Railway 백엔드 설정 진행 중 🔄

#### 2.1 Railway 프로젝트 생성 ✓
- **저장소**: `Giwoong-ryu/qt-make` ✓
- **Branch**: main ✓
- **프로젝트명**: qt-make

#### 2.2 설정 파일 생성 ✓
다음 파일들이 생성되어 GitHub `qt-make` 저장소에 존재:

**backend/railway.toml**
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**backend/nixpacks.toml**
```toml
[phases.setup]
nixPkgs = ["python311", "ffmpeg"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["echo 'Skipping tests in production build'"]

[start]
cmd = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

**backend/.railwayignore**
```
test_*.py
tests/
*.pyc
__pycache__/
.pytest_cache/
.env
.venv/
venv/
```

#### 2.3 현재 상태
- **Source Repo**: `Giwoong-ryu/qt-make` ✓
- **Root Directory**: ✅ `backend` (수정 완료)
- **배포 상태**: ✅ 성공 (ACTIVE)
- **공개 도메인**: `qt-make-production.up.railway.app` (Port 8080)
- **커스텀 도메인**: `api.qt-make.com` (Port 8080) - DNS 전파 대기 중

---

## ✅ 완료된 Railway 설정

### 1. 배포 성공
- 상태: ACTIVE
- 빌드: 성공
- 서버: Uvicorn 실행 중

### 2. 공개 도메인 생성 완료
```
https://qt-make-production.up.railway.app
Port: 8080
Status: Connected ✓
```

### 3. 커스텀 도메인 추가 완료
```
Domain: api.qt-make.com
Port: 8080
CNAME: kh1ib3tg.up.railway.app
Status: Waiting for DNS update ⏳
```

**참고**: Railway가 자동으로 DNS를 처리하므로 외부 DNS 설정 불필요

---

## ⏳ DNS 전파 대기 중 (2026-01-21)

### 현재 상황
- Railway 커스텀 도메인 추가: 완료
- DNS 전파: 진행 중
- 예상 소요 시간: 10분 ~ 2시간 (최대 72시간)

### 확인 방법

**1. Railway 대시보드**
```
Settings → Networking → api.qt-make.com
"Waiting for DNS update" → "Connected" 로 변경되면 완료
```

**2. 브라우저 테스트**
```
https://api.qt-make.com/health
```
- 성공: {"status":"ok"} 응답
- 실패: "사이트에 연결할 수 없음" (아직 전파 안됨)

---

## 🔄 다음 단계 (DNS 전파 완료 후)
1. Railway → Settings → Networking
2. Custom Domain 추가: `api.qt-make.com`
3. Railway가 제공하는 CNAME 값 확인
4. 도메인 제공업체(가비아)에서 DNS 레코드 추가:
   ```
   Type: CNAME
   Name: api
   Value: [Railway에서 제공한 값].up.railway.app
   TTL: 자동
   ```

### Step 1: Railway 환경변수 설정
Railway → Variables 탭에서 다음 환경변수 추가:

```bash
# Supabase
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=eyJ...

# Cloudflare R2
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=qt-video
R2_PUBLIC_URL=https://[r2].r2.dev

# PortOne 결제
PORTONE_API_SECRET=...
PORTONE_STORE_ID=...

# Pexels API
PEXELS_API_KEY=...
```

⚠️ **중요**: 환경변수 추가 후 Railway가 자동으로 재배포됨

### Step 2: Vercel 환경변수 업데이트
Vercel Dashboard → Settings → Environment Variables:

| Key | Value | Environment |
|-----|-------|-------------|
| NEXT_PUBLIC_API_URL | https://api.qt-make.com | Production |
| NEXT_PUBLIC_SUPABASE_URL | https://[project].supabase.co | All |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | eyJ... | All |

⚠️ **중요**: 환경변수 추가 후 Vercel 재배포 필요

---

## 📋 이후 작업 (환경변수 설정 완료 후)

### 3. Supabase 마이그레이션 실행
Supabase SQL Editor에서 순서대로 실행:

1. **무료 플랜 시스템**
   ```sql
   -- backend/migrations/add_free_plan.sql 전체 복사 실행
   ```

2. **관리자 계정 설정**
   ```sql
   -- backend/migrations/set_admin_unlimited.sql
   -- ⚠️ YOUR_EMAIL_HERE를 실제 이메일로 변경!

   UPDATE users
   SET subscription_plan = 'enterprise',
       weekly_credits = 999999,
       role = 'admin'
   WHERE email = 'your-actual@email.com';
   ```

3. **클립 메타데이터**
   ```sql
   -- supabase/migrations/008_add_clips_metadata.sql
   ```

4. **중복 방지 테이블**
   ```sql
   -- backend/create_used_clips_table.sql
   ```

### 4. 포트원 결제 설정
1. https://admin.portone.io 로그인
2. 결제 연동 > 빌링키 발급
3. Redirection URL 설정:
   - Success: `https://qt-make.com/subscription/callback`
   - Fail: `https://qt-make.com/subscription/callback`

### 5. 전체 테스트

#### API Health Check
```bash
curl https://api.qt-make.com/health
# 예상 응답: {"status":"ok"}
```

#### 프론트엔드 기능 테스트
- [ ] https://qt-make.com 접속 성공
- [ ] 회원가입 → 무료 플랜 자동 할당
- [ ] 사이드바 크레딧 표시: 10/10
- [ ] 영상 생성 → 크레딧 9/10으로 감소
- [ ] 키보드 단축키 작동 (Space, ←→, M, F)
- [ ] 관리자 계정 "∞ 무제한" 표시

---

## 🚨 문제 해결 참고

### CORS 에러 발생 시
```python
# backend/app/main.py 확인
allow_origins=["https://qt-make.com"]
```

### 환경변수 누락 시
- Railway/Vercel 대시보드에서 재확인
- 환경변수 추가 후 반드시 재배포

### 빌드 실패 시
- Railway 로그에서 정확한 에러 메시지 확인
- `nixpacks.toml`, `railway.toml` 설정 재확인

---

## 📂 관련 파일 위치

### GitHub 저장소
- **qt-make**: https://github.com/Giwoong-ryu/qt-make
  - 배포용 코드 (Vercel, Railway 연결)
- **n8n-make**: https://github.com/Giwoong-ryu/n8n-make
  - 로컬 작업 폴더 (참고용)

### 로컬 작업 경로
```
C:\Users\user\Desktop\gpt\n8n-make\kmong_work\qt-make\qt-video-saas\
├── frontend/          # Vercel 배포 대상
├── backend/           # Railway 배포 대상
└── DEPLOYMENT_STATUS.md  # 이 문서
```

### 설정 파일
- `backend/railway.toml`
- `backend/nixpacks.toml`
- `backend/.railwayignore`
- `backend/requirements.txt`

---

## 🎯 다음 세션 시작 시 확인 사항

1. **프론트엔드 DNS 전파 완료 여부**
   - https://qt-make.com 접속 확인

2. **Railway 배포 상태**
   - Railway Dashboard 확인
   - 배포 성공 여부
   - 에러 로그 확인

3. **현재 작업 단계**
   - 이 문서의 "다음 단계" 섹션부터 진행

---

## 📊 배포 진행 상황 요약

| 단계 | 상태 | 비고 |
|------|------|------|
| Vercel 프론트엔드 | ✅ 완료 | https://qt-make.com |
| Railway 백엔드 배포 | ✅ 완료 | ACTIVE 상태 |
| Railway 공개 도메인 | ✅ 완료 | qt-make-production.up.railway.app |
| Railway 커스텀 도메인 | ⏳ 대기 중 | api.qt-make.com (DNS 전파 중) |
| Railway 환경변수 | ⏸️ 대기 | DNS 전파 후 진행 |
| Vercel 환경변수 | ⏸️ 대기 | DNS 전파 후 진행 |
| Supabase 마이그레이션 | ⏸️ 대기 | 환경변수 후 진행 |
| 포트원 설정 | ⏸️ 대기 | 환경변수 후 진행 |
| 전체 테스트 | ⏸️ 대기 | 최종 단계 |

---

**마지막 업데이트**: 2026-01-21 (DNS 전파 대기 중)
**작성자**: Claude Code Session
**다음 작업**: DNS 전파 완료 확인 → Railway 환경변수 설정
