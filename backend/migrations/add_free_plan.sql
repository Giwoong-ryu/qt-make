-- ===================================
-- 무료 플랜 시스템 마이그레이션
-- ===================================
-- 실행: Supabase SQL Editor에서 전체 복사/붙여넣기

-- 1. users 테이블에 플랜 관련 컬럼 추가
-- ===================================

-- subscription_plan 컬럼 추가 (free, basic, pro, enterprise)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT 'free'
CHECK (subscription_plan IN ('free', 'basic', 'pro', 'enterprise'));

-- weekly_credits 컬럼 추가 (주간 무료 크레딧)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS weekly_credits INTEGER DEFAULT 10;

-- weekly_credits_reset_at 컬럼 추가 (마지막 리셋 시간)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS weekly_credits_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 2. 기존 사용자 마이그레이션
-- ===================================

-- 모든 기존 사용자를 무료 플랜으로 설정
UPDATE users
SET
    subscription_plan = 'free',
    weekly_credits = 10,
    weekly_credits_reset_at = NOW()
WHERE subscription_plan IS NULL;

-- 3. 주간 크레딧 자동 리셋 함수
-- ===================================

CREATE OR REPLACE FUNCTION reset_weekly_credits()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- 마지막 리셋으로부터 7일 이상 지난 사용자 리셋
    UPDATE users
    SET
        weekly_credits = CASE
            WHEN subscription_plan = 'free' THEN 10
            WHEN subscription_plan = 'basic' THEN 50
            WHEN subscription_plan = 'pro' THEN 200
            WHEN subscription_plan = 'enterprise' THEN 999999
            ELSE 10
        END,
        weekly_credits_reset_at = NOW()
    WHERE weekly_credits_reset_at < NOW() - INTERVAL '7 days';

    -- 로그 출력 (Supabase Logs에서 확인 가능)
    RAISE NOTICE 'Weekly credits reset completed at %', NOW();
END;
$$;

-- 4. Cron Job 설정 (pg_cron 확장 필요)
-- ===================================

-- pg_cron 확장 활성화 (Supabase Pro 이상에서만 가능)
-- Dashboard > Database > Extensions > pg_cron 활성화

-- Cron Job 등록 (매일 0시 실행)
-- 방법 1: SQL로 직접 등록 (pg_cron 사용)
SELECT cron.schedule(
    'reset-weekly-credits',              -- Job 이름
    '0 0 * * *',                         -- 매일 0시 (UTC)
    $$SELECT reset_weekly_credits()$$    -- 실행할 함수
);

-- 방법 2: Supabase Dashboard에서 등록 (권장)
-- Dashboard > Database > Cron Jobs > New Cron Job
-- Name: reset-weekly-credits
-- Schedule: 0 0 * * * (매일 0시)
-- Function: reset_weekly_credits()

-- 5. 인덱스 추가 (성능 최적화)
-- ===================================

-- subscription_plan으로 조회 최적화
CREATE INDEX IF NOT EXISTS idx_users_subscription_plan
ON users(subscription_plan);

-- weekly_credits_reset_at으로 리셋 대상 조회 최적화
CREATE INDEX IF NOT EXISTS idx_users_weekly_credits_reset
ON users(weekly_credits_reset_at)
WHERE subscription_plan IN ('free', 'basic', 'pro');

-- 6. 뷰 생성 (관리자용 대시보드)
-- ===================================

CREATE OR REPLACE VIEW user_plan_stats AS
SELECT
    subscription_plan,
    COUNT(*) as user_count,
    AVG(weekly_credits) as avg_credits,
    SUM(CASE WHEN weekly_credits = 0 THEN 1 ELSE 0 END) as exhausted_credits_count
FROM users
GROUP BY subscription_plan;

-- 7. 트리거 생성 (신규 가입자 자동 설정)
-- ===================================

-- 신규 가입자에게 무료 플랜 자동 부여
CREATE OR REPLACE FUNCTION set_default_plan()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- 신규 가입자는 무조건 free 플랜
    NEW.subscription_plan = COALESCE(NEW.subscription_plan, 'free');
    NEW.weekly_credits = COALESCE(NEW.weekly_credits, 10);
    NEW.weekly_credits_reset_at = COALESCE(NEW.weekly_credits_reset_at, NOW());
    RETURN NEW;
END;
$$;

-- 트리거 등록
DROP TRIGGER IF EXISTS trigger_set_default_plan ON users;
CREATE TRIGGER trigger_set_default_plan
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_default_plan();

-- 8. 검증 쿼리
-- ===================================

-- 플랜별 사용자 수 확인
SELECT subscription_plan, COUNT(*) as user_count
FROM users
GROUP BY subscription_plan;

-- 크레딧 소진 사용자 확인
SELECT email, weekly_credits, weekly_credits_reset_at
FROM users
WHERE weekly_credits <= 0
ORDER BY weekly_credits_reset_at DESC;

-- 리셋 대상 사용자 확인 (7일 이상 지난 사용자)
SELECT email, weekly_credits, weekly_credits_reset_at
FROM users
WHERE weekly_credits_reset_at < NOW() - INTERVAL '7 days'
ORDER BY weekly_credits_reset_at;

-- 9. 테스트 데이터
-- ===================================

-- 테스트 사용자 생성 (이미 회원가입한 경우 스킵)
-- INSERT INTO users (email, name, subscription_plan, weekly_credits)
-- VALUES ('test@example.com', '테스트 사용자', 'free', 10);

-- 10. 롤백 스크립트 (문제 발생 시)
-- ===================================

/*
-- 컬럼 삭제 (주의: 데이터 손실!)
ALTER TABLE users DROP COLUMN IF EXISTS subscription_plan;
ALTER TABLE users DROP COLUMN IF EXISTS weekly_credits;
ALTER TABLE users DROP COLUMN IF EXISTS weekly_credits_reset_at;

-- 함수 삭제
DROP FUNCTION IF EXISTS reset_weekly_credits();
DROP FUNCTION IF EXISTS set_default_plan();

-- 트리거 삭제
DROP TRIGGER IF EXISTS trigger_set_default_plan ON users;

-- 인덱스 삭제
DROP INDEX IF EXISTS idx_users_subscription_plan;
DROP INDEX IF EXISTS idx_users_weekly_credits_reset;

-- 뷰 삭제
DROP VIEW IF EXISTS user_plan_stats;

-- Cron Job 삭제
SELECT cron.unschedule('reset-weekly-credits');
*/

-- ===================================
-- 마이그레이션 완료!
-- ===================================

-- 다음 단계:
-- 1. Backend 코드 수정 (video.py의 크레딧 차감 로직)
-- 2. Frontend UI 업데이트 (주간 크레딧 표시)
-- 3. 테스트 계정으로 검증

SELECT 'Migration completed successfully!' as status;
