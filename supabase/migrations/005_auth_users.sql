-- 사용자 인증 스키마
-- 실행: Supabase Dashboard > SQL Editor

-- ============================================
-- 1. users 테이블 (Supabase Auth 연동)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,  -- Supabase Auth user id와 동일
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    church_id TEXT REFERENCES churches(id) ON DELETE SET NULL,
    role TEXT DEFAULT 'member',  -- 'admin', 'member'
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_church_id ON users(church_id);

-- 업데이트 트리거
DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

COMMENT ON TABLE users IS '사용자 정보 (Supabase Auth 연동)';
COMMENT ON COLUMN users.id IS 'Supabase Auth user id';
COMMENT ON COLUMN users.role IS 'admin: 교회 관리자, member: 일반 회원';


-- ============================================
-- 2. Supabase Auth 트리거 (자동 사용자 생성)
-- ============================================
-- 새 사용자 가입 시 users 테이블에 자동 추가
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- auth.users 테이블에 트리거 연결
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();


-- ============================================
-- 3. RLS (Row Level Security) 정책
-- ============================================
-- users 테이블 RLS 활성화
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 본인 정보만 조회 가능
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

-- 본인 정보만 수정 가능
CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- videos 테이블 RLS (같은 교회만)
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own church videos"
    ON videos FOR SELECT
    USING (
        church_id IN (
            SELECT church_id FROM users WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own church videos"
    ON videos FOR INSERT
    WITH CHECK (
        church_id IN (
            SELECT church_id FROM users WHERE id = auth.uid()
        )
    );

-- church_dictionary 테이블 RLS
ALTER TABLE church_dictionary ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own church dictionary"
    ON church_dictionary FOR SELECT
    USING (
        church_id IN (
            SELECT church_id FROM users WHERE id = auth.uid()
        )
    );

CREATE POLICY "Admins can manage church dictionary"
    ON church_dictionary FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND church_id = church_dictionary.church_id
            AND role = 'admin'
        )
    );
