-- 구독 관련 테이블 추가
-- 실행: Supabase SQL Editor에서 실행

-- 구독 테이블
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID REFERENCES churches(id) ON DELETE CASCADE,
    billing_key TEXT,
    tier TEXT DEFAULT 'free',
    status TEXT DEFAULT 'active',  -- active, cancelled, expired
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(church_id)
);

-- 월간 사용량 테이블
CREATE TABLE IF NOT EXISTS monthly_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID REFERENCES churches(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL,  -- '2026-01'
    video_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(church_id, year_month)
);

-- 결제 내역 테이블
CREATE TABLE IF NOT EXISTS payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID REFERENCES churches(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,  -- paid, failed, refunded
    portone_payment_id TEXT,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_subscriptions_church_id ON subscriptions(church_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_monthly_usage_church_id ON monthly_usage(church_id);
CREATE INDEX IF NOT EXISTS idx_monthly_usage_year_month ON monthly_usage(year_month);
CREATE INDEX IF NOT EXISTS idx_payment_history_church_id ON payment_history(church_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(status);

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_monthly_usage_updated_at
    BEFORE UPDATE ON monthly_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS 정책 (Row Level Security)
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_history ENABLE ROW LEVEL SECURITY;

-- 서비스 역할은 모든 접근 허용
CREATE POLICY "Service role has full access to subscriptions"
    ON subscriptions FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to monthly_usage"
    ON monthly_usage FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to payment_history"
    ON payment_history FOR ALL
    USING (true)
    WITH CHECK (true);
