# QT Video SaaS 배포 가이드

## 🌐 도메인 정보
- **메인 도메인**: qt-make.com
- **프론트엔드**: https://qt-make.com
- **백엔드 API**: https://api.qt-make.com (권장)

---

## 📦 1. Vercel 프론트엔드 배포

### 1.1 Vercel 프로젝트 연결
1. https://vercel.com/dashboard 접속
2. Import Git Repository
3. GitHub에서 `Giwoong-ryu/qt-make` 선택
4. Root Directory: `kmong_work/qt-make/qt-video-saas/frontend`

### 1.2 커스텀 도메인 설정

**Vercel Dashboard > Settings > Domains:**
1. `qt-make.com` 추가
2. DNS 레코드 설정 (도메인 제공업체):

```
Type: A
Name: @
Value: 76.76.21.21

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

### 1.3 환경변수 설정

**Vercel Dashboard > Settings > Environment Variables:**

| Key | Value | Environment |
|-----|-------|-------------|
| NEXT_PUBLIC_API_URL | https://api.qt-make.com | Production |
| NEXT_PUBLIC_SUPABASE_URL | https://[project].supabase.co | All |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | eyJ... | All |

---

## 🔧 2. Railway 백엔드 배포

### 2.1 Railway 프로젝트 생성
1. https://railway.app 로그인
2. New Project > Deploy from GitHub
3. 저장소: `Giwoong-ryu/qt-make`
4. Root Directory: `kmong_work/qt-make/qt-video-saas/backend`

### 2.2 커스텀 도메인 설정

**Railway Settings > Networking:**
- Custom Domain: `api.qt-make.com`

**DNS 레코드:**
```
Type: CNAME
Name: api
Value: [your-project].up.railway.app
```

### 2.3 환경변수 설정

```bash
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=eyJ...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=qt-video
R2_PUBLIC_URL=https://[r2].r2.dev
PORTONE_API_SECRET=...
PORTONE_STORE_ID=...
PEXELS_API_KEY=...
```

### 2.4 시작 명령어

**Settings > Deploy > Start Command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 🗄️ 3. Supabase 마이그레이션

**Supabase SQL Editor에서 순서대로 실행:**

### 3.1 무료 플랜 시스템
```sql
-- backend/migrations/add_free_plan.sql 전체 복사
```

### 3.2 관리자 계정 설정
```sql
-- backend/migrations/set_admin_unlimited.sql
-- ⚠️ YOUR_EMAIL_HERE 변경 필수!

UPDATE users
SET subscription_plan = 'enterprise',
    weekly_credits = 999999,
    role = 'admin'
WHERE email = 'your-actual@email.com';
```

### 3.3 클립 메타데이터
```sql
-- supabase/migrations/008_add_clips_metadata.sql
```

### 3.4 중복 방지 테이블
```sql
-- backend/create_used_clips_table.sql
```

---

## 🔐 4. 포트원 설정

1. https://admin.portone.io 로그인
2. 결제 연동 > 빌링키 발급
3. **Redirection URL**:
   - Success: `https://qt-make.com/subscription/callback`
   - Fail: `https://qt-make.com/subscription/callback`

---

## 🧪 5. 배포 후 테스트

### 체크리스트
- [ ] https://qt-make.com 접속 성공
- [ ] 회원가입 → 무료 플랜 자동 할당
- [ ] 사이드바 크레딧 표시: 10/10
- [ ] 영상 생성 → 크레딧 9/10으로 감소
- [ ] 키보드 단축키 작동 (Space, ←→, M, F)
- [ ] 관리자 계정 "∞ 무제한" 표시

### API Health Check
```bash
curl https://api.qt-make.com/health
# 예상: {"status":"ok"}
```

---

## 🚨 문제 해결

### CORS 에러
```python
# backend/app/main.py 확인
allow_origins=["https://qt-make.com"]
```

### 환경변수 누락
- Railway/Vercel 대시보드에서 재확인

---

## ✅ 배포 완료

**최종 확인:**
- 프론트엔드: https://qt-make.com ✓
- 백엔드 API: https://api.qt-make.com ✓
- 무료 플랜 10회 제한 ✓
- 관리자 무제한 ✓
- 키보드 단축키 ✓

배포 완료! 🎉
