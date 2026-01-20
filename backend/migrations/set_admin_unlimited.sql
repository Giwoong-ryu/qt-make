-- ===================================
-- 관리자 계정 무제한 설정
-- ===================================
-- 실행: Supabase SQL Editor에서 실행

-- 1. 관리자 이메일로 무제한 플랜 설정
-- ===================================

-- 본인 이메일을 입력하세요!
UPDATE users
SET
    subscription_plan = 'enterprise',  -- 엔터프라이즈 = 무제한
    weekly_credits = 999999,           -- 사실상 무제한
    role = 'admin'                     -- 관리자 역할
WHERE email = 'YOUR_EMAIL_HERE@example.com';  -- ⚠️ 이메일 변경 필수!

-- 2. 확인
-- ===================================

SELECT
    email,
    subscription_plan,
    weekly_credits,
    role
FROM users
WHERE email = 'YOUR_EMAIL_HERE@example.com';

-- 예상 결과:
-- email                    | subscription_plan | weekly_credits | role
-- -------------------------|-------------------|----------------|-------
-- your@email.com           | enterprise        | 999999         | admin

-- 3. 크레딧 차감 로직 업데이트 (Backend)
-- ===================================

-- Backend 코드 (main.py:269-286)에서 이미 처리됨:
-- if plan == "free":
--     크레딧 체크 + 차감
-- elif plan in ["basic", "pro", "enterprise"]:
--     무제한 (체크 안 함)

-- 4. 동생 계정은 무료 플랜 유지
-- ===================================

SELECT
    email,
    subscription_plan,
    weekly_credits
FROM users
WHERE subscription_plan = 'free'
ORDER BY created_at DESC;

-- ===================================
-- 완료!
-- ===================================

-- 다음 단계:
-- 1. 위 SQL에서 'YOUR_EMAIL_HERE@example.com'을 본인 이메일로 변경
-- 2. Supabase SQL Editor에서 실행
-- 3. 로그인 후 대시보드 확인 (크레딧 표시 안 됨)
