# 🚀 빠른 시작 가이드 (동생 테스트용)

> 5분 안에 배포 + 테스트 시작

---

## ✅ Step 1: Supabase 설정 (3분)

### 1-1. 무료 플랜 시스템 활성화

```bash
# Supabase Dashboard 접속
# → SQL Editor 열기
# → 아래 파일 내용 전체 복사/붙여넣기/실행

backend/migrations/add_free_plan.sql
```

**실행 완료 확인**:
```sql
-- 플랜별 사용자 수 확인
SELECT subscription_plan, COUNT(*) FROM users GROUP BY subscription_plan;

-- 예상 결과:
-- free | 0 (신규 가입자는 자동으로 free)
```

### 1-2. 관리자 계정 무제한 설정 (본인 계정)

```bash
# 1. 파일 열기
backend/migrations/set_admin_unlimited.sql

# 2. 이메일 변경
'YOUR_EMAIL_HERE@example.com' → 본인 실제 이메일

# 3. Supabase SQL Editor에서 실행
```

**확인**:
```sql
SELECT email, subscription_plan, weekly_credits
FROM users
WHERE email = '본인이메일@example.com';

-- 예상 결과:
-- subscription_plan: enterprise
-- weekly_credits: 999999
```

---

## ✅ Step 2: Backend 재시작 (1분)

### Docker 재시작

```bash
cd qt-video-saas

# 1. 재시작 (환경변수 + 코드 반영)
docker-compose restart api worker

# 2. 로그 확인
docker-compose logs -f api

# 3. 헬스 체크
curl http://localhost:8000/health
```

**정상 응답**:
```json
{
  "status": "healthy",
  "env": "production",
  "checks": {
    "redis": "ok",
    "supabase": "ok"
  }
}
```

---

## ✅ Step 3: 테스트 (1분)

### 3-1. 동생 계정 생성

```
URL: http://localhost:3000/signup
(또는 배포된 도메인)

입력:
- 이메일: brother@example.com
- 비밀번호: Test1234!
- 이름: 동생
```

**자동 부여**: 주간 10개 무료 크레딧

### 3-2. 로그인 후 확인

```
대시보드 상단에 표시됨:

┌─────────────────────────────────────────┐
│ 무료 플랜: 이번 주 10개 남음             │
│ 매주 월요일 0시에 10개로 충전됩니다      │
└─────────────────────────────────────────┘
```

### 3-3. 영상 1개 생성

```
1. 파일 업로드 (MP3/WAV/M4A)
2. 템플릿 선택
3. "영상 생성" 클릭
4. 크레딧 확인 (10 → 9)
```

---

## 🎯 완료!

### 계정별 플랜 확인

| 계정 | 플랜 | 주간 크레딧 | 상태 |
|------|------|-------------|------|
| **본인** | enterprise | 999999 | 무제한 (크레딧 표시 안 됨) |
| **동생** | free | 10 → 9 → ... → 0 | 주간 10개 제한 |

---

## 🔧 트러블슈팅

### 문제 1: 크레딧 표시 안 됨

**원인**: Frontend 캐시 or Backend 재시작 안 함

**해결**:
```bash
# 1. 브라우저 강력 새로고침 (Ctrl+Shift+R)
# 2. 로그아웃 → 로그인
# 3. Backend 로그 확인
docker-compose logs api | grep -i credit
```

### 문제 2: 크레딧 차감 안 됨

**원인**: Authorization 헤더 누락

**해결**:
```bash
# 브라우저 개발자 도구 (F12) → Network 탭
# /api/videos/upload 요청 확인
# Headers에 "Authorization: Bearer ..." 있는지 확인
```

### 문제 3: 11개째 업로드 시도 시 에러 없음

**원인**: 크레딧 체크 로직 미작동

**해결**:
```bash
# Backend 로그 확인
docker-compose logs api | grep -i "Credits deducted"

# 예상 로그:
# Credits deducted: user=xxx, used=1, remaining=9
```

---

## 📋 다음 단계

### 1주일 후 크레딧 자동 리셋 테스트

```sql
-- 강제로 7일 전으로 설정
UPDATE users
SET weekly_credits_reset_at = NOW() - INTERVAL '8 days'
WHERE email = 'brother@example.com';

-- 리셋 함수 수동 실행
SELECT reset_weekly_credits();

-- 확인 (10으로 복구됨)
SELECT email, weekly_credits FROM users WHERE email = 'brother@example.com';
```

### Cron Job 확인 (자동 리셋)

```
Supabase Dashboard > Database > Cron Jobs
→ "reset-weekly-credits" 작업 확인
→ Schedule: 0 0 * * * (매일 0시 UTC)
```

---

## 💡 추가 기능 (추후)

- [ ] 크레딧 소진 시 이메일 알림
- [ ] 유료 플랜 업그레이드 페이지
- [ ] 크레딧 사용 내역 로그
- [ ] 관리자 대시보드 (전체 사용자 크레딧 현황)
- [ ] 프로모션 코드 (추가 크레딧 지급)
