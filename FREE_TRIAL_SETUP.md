# 무료 체험 플랜 설정 가이드

> 주간 10개 영상 생성 제한 무료 플랜

---

## 📋 무료 플랜 정책

| 항목 | 값 |
|------|-----|
| **주간 제공 크레딧** | 10개 (매주 월요일 0시 리셋) |
| **영상 1개당 비용** | 1 크레딧 |
| **최대 생성 가능** | 주당 10개 영상 |
| **추가 구매** | 결제 시스템 연동 필요 (추후) |
| **플랜 이름** | `free` |

---

## 🔧 구현 방법

### 방법 1: Supabase 테이블 구조 수정 (권장)

#### 1. users 테이블에 플랜 정보 추가

```sql
-- Supabase SQL Editor에서 실행

-- 1. subscription_plan 컬럼 추가
ALTER TABLE users
ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT 'free';

-- 2. weekly_credits 컬럼 추가 (주간 크레딧)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS weekly_credits INTEGER DEFAULT 10;

-- 3. weekly_credits_reset_at 컬럼 추가 (마지막 리셋 시간)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS weekly_credits_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 4. 기존 사용자 마이그레이션
UPDATE users
SET
    subscription_plan = 'free',
    weekly_credits = 10,
    weekly_credits_reset_at = NOW()
WHERE subscription_plan IS NULL;
```

#### 2. 주간 크레딧 자동 리셋 함수 생성

```sql
-- 주간 크레딧 리셋 함수
CREATE OR REPLACE FUNCTION reset_weekly_credits()
RETURNS void AS $$
BEGIN
    -- 마지막 리셋으로부터 7일 이상 지난 사용자 리셋
    UPDATE users
    SET
        weekly_credits = CASE
            WHEN subscription_plan = 'free' THEN 10
            WHEN subscription_plan = 'basic' THEN 50
            WHEN subscription_plan = 'pro' THEN 200
            ELSE 10
        END,
        weekly_credits_reset_at = NOW()
    WHERE weekly_credits_reset_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Supabase Cron Job 설정 (매일 0시 실행)
-- Dashboard > Database > Cron Jobs 에서 추가:
-- Function: reset_weekly_credits()
-- Schedule: 0 0 * * * (매일 0시)
```

#### 3. Backend 코드 수정

**`backend/app/routers/video.py` 수정**:

```python
# 크레딧 차감 로직 수정 (주간 크레딧 사용)
async def upload_audio(
    ...
):
    # 사용자 조회
    user_result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    user = user_result.data

    # 주간 크레딧 체크 (무료 플랜)
    if user["subscription_plan"] == "free":
        if user["weekly_credits"] <= 0:
            raise HTTPException(
                status_code=402,
                detail="주간 무료 크레딧을 모두 사용했습니다. 다음 주 월요일에 10개가 충전됩니다."
            )

        # 주간 크레딧 차감
        supabase.table("users").update({
            "weekly_credits": user["weekly_credits"] - 1
        }).eq("id", user_id).execute()

    # 유료 플랜은 credits 사용
    elif user["subscription_plan"] in ["basic", "pro"]:
        if user["credits"] < CREDIT_COST:
            raise HTTPException(status_code=402, detail="크레딧이 부족합니다")

        supabase.table("users").update({
            "credits": user["credits"] - CREDIT_COST
        }).eq("id", user_id).execute()

    ...
```

---

### 방법 2: 간단한 테스트용 (즉시 적용)

Supabase에서 동생 계정만 특별 설정:

```sql
-- 동생 이메일로 무료 크레딧 설정
UPDATE users
SET
    credits = 10,  -- 기존 credits 사용
    subscription_plan = 'free_trial'
WHERE email = 'your-brother@example.com';

-- 크레딧 사용 후 재충전 (수동)
UPDATE users
SET credits = 10
WHERE email = 'your-brother@example.com';
```

**주의**: 방법 2는 자동 리셋이 없으므로 매주 수동으로 크레딧 충전 필요

---

## 🎯 동생 테스트 계정 생성

### 1. 회원가입

```bash
# 1. 동생 계정 회원가입
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-brother@example.com",
    "password": "Test1234!",
    "name": "테스트 사용자"
  }'
```

### 2. 무료 플랜 설정

```sql
-- Supabase SQL Editor에서 실행
UPDATE users
SET
    subscription_plan = 'free',
    weekly_credits = 10,
    weekly_credits_reset_at = NOW()
WHERE email = 'test-brother@example.com';
```

### 3. 크레딧 확인

```bash
# 로그인
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-brother@example.com",
    "password": "Test1234!"
  }' | jq -r .access_token)

# 크레딧 확인
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/auth/me | jq '{email, weekly_credits, subscription_plan}'
```

---

## 📊 플랜별 크레딧 정책

| 플랜 | 주간 크레딧 | 월 비용 | 비고 |
|------|-------------|---------|------|
| **Free** | 10개 | 무료 | 매주 리셋, 이월 불가 |
| **Basic** | 50개 | ₩9,900 | 주간 리셋, 추가 구매 가능 |
| **Pro** | 200개 | ₩29,900 | 주간 리셋, 추가 구매 가능 |
| **Enterprise** | 무제한 | 문의 | 리셋 없음 |

---

## 🔔 사용자 알림 메시지

### Frontend 표시 예시

```tsx
// 대시보드 상단 크레딧 표시
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <p className="text-sm text-blue-800">
    무료 플랜: 이번 주 <strong>{weeklyCredits}개</strong> 남음
  </p>
  <p className="text-xs text-blue-600 mt-1">
    매주 월요일 0시에 10개로 충전됩니다
  </p>
  {weeklyCredits === 0 && (
    <p className="text-xs text-red-600 mt-2">
      크레딧을 모두 사용했습니다. 유료 플랜으로 업그레이드하시겠습니까?
    </p>
  )}
</div>
```

### 크레딧 소진 시 에러 메시지

```json
{
  "detail": "주간 무료 크레딧을 모두 사용했습니다. 다음 주 월요일에 10개가 충전됩니다.",
  "next_reset": "2026-01-27T00:00:00Z",
  "plan": "free",
  "upgrade_url": "/pricing"
}
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 정상 사용 (1-10개)

```bash
# 1. 영상 1개 생성
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.mp3"

# 2. 크레딧 확인 (10 → 9)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/auth/me | jq .weekly_credits
```

### 시나리오 2: 크레딧 소진 (11개 시도)

```bash
# 10개 생성 후 11번째 시도
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.mp3"

# 예상 응답: 402 Payment Required
{
  "detail": "주간 무료 크레딧을 모두 사용했습니다..."
}
```

### 시나리오 3: 주간 리셋 테스트

```sql
-- 강제로 7일 전으로 설정
UPDATE users
SET weekly_credits_reset_at = NOW() - INTERVAL '8 days'
WHERE email = 'test-brother@example.com';

-- 리셋 함수 수동 실행
SELECT reset_weekly_credits();

-- 확인 (10으로 복구됨)
SELECT email, weekly_credits, weekly_credits_reset_at
FROM users
WHERE email = 'test-brother@example.com';
```

---

## 🚀 배포 체크리스트

### Supabase 설정

- [ ] users 테이블에 `subscription_plan` 컬럼 추가
- [ ] users 테이블에 `weekly_credits` 컬럼 추가
- [ ] users 테이블에 `weekly_credits_reset_at` 컬럼 추가
- [ ] `reset_weekly_credits()` 함수 생성
- [ ] Cron Job 설정 (매일 0시 실행)
- [ ] 기존 사용자 마이그레이션

### Backend 코드

- [ ] `video.py`에 주간 크레딧 로직 추가
- [ ] 에러 메시지 업데이트
- [ ] 플랜별 크레딧 정책 적용

### Frontend 표시

- [ ] 대시보드에 주간 크레딧 표시
- [ ] 크레딧 소진 시 알림
- [ ] 다음 리셋 시간 표시
- [ ] 업그레이드 버튼 (추후)

---

## 💡 추가 고려사항

### 1. 크레딧 이월 금지

무료 플랜은 매주 리셋되며 이월되지 않음:

```sql
-- 리셋 시 무조건 10으로 고정
UPDATE users
SET weekly_credits = 10
WHERE subscription_plan = 'free'
  AND weekly_credits_reset_at < NOW() - INTERVAL '7 days';
```

### 2. 유료 플랜 전환 시 처리

```sql
-- Free → Basic 업그레이드
UPDATE users
SET
    subscription_plan = 'basic',
    weekly_credits = 50,  -- Basic 플랜 크레딧
    credits = 0,  -- 기존 credits 초기화
    weekly_credits_reset_at = NOW()
WHERE id = 'user-id';
```

### 3. 관리자 계정 (무제한)

```sql
-- 관리자 계정 생성
INSERT INTO users (email, name, subscription_plan, weekly_credits, role)
VALUES ('admin@internal.com', 'Admin', 'enterprise', 999999, 'admin');
```

---

## 📞 문의

- 크레딧 정책 관련: [이메일]
- 버그 제보: [GitHub Issues]
