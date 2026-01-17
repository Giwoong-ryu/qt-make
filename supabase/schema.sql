-- QT Video SaaS Supabase Schema
-- 실행: Supabase Dashboard > SQL Editor

-- 1. Churches (교회 테이블)
CREATE TABLE IF NOT EXISTS churches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    pack_id TEXT NOT NULL DEFAULT 'pack-free',
    subscription_tier TEXT DEFAULT 'free',  -- free, basic, premium
    monthly_price INTEGER DEFAULT 30000,
    contact_email TEXT,
    contact_phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_churches_pack_id ON churches(pack_id);

-- 2. Packs (배경팩 테이블)
CREATE TABLE IF NOT EXISTS packs (
    id TEXT PRIMARY KEY,  -- 'pack-free', 'pack-nature-1', etc
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,  -- nature, abstract, church, etc
    clip_count INTEGER DEFAULT 0,
    is_premium BOOLEAN DEFAULT FALSE,
    assigned_church_id UUID REFERENCES churches(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 무료 팩 삽입
INSERT INTO packs (id, name, description, category, is_premium) VALUES
    ('pack-free', '무료 기본팩', '50개 기본 배경 클립', 'mixed', FALSE)
ON CONFLICT (id) DO NOTHING;

-- 3. Clips (배경 클립 테이블)
-- 주의: id는 TEXT 타입 ('clip-nature-100' 등 문자열 ID 사용)
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,  -- TEXT ID (예: 'clip-nature-100', 'clip-moody-09')
    pack_id TEXT NOT NULL REFERENCES packs(id),
    file_path TEXT NOT NULL,  -- R2 URL
    file_name TEXT,  -- 선택적
    name TEXT,  -- 클립 이름
    category TEXT NOT NULL,  -- nature, sky, bible, abstract, etc
    duration INTEGER DEFAULT 30,  -- 초
    resolution TEXT DEFAULT '4K',
    source TEXT,  -- pexels, pixabay, mazwai
    source_url TEXT,  -- 원본 URL (라이선스 확인용)
    thumbnail_url TEXT,
    tags TEXT[],
    used_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_clips_pack_id ON clips(pack_id);
CREATE INDEX idx_clips_category ON clips(category);
CREATE INDEX idx_clips_used_count ON clips(used_count);

-- 사용 횟수 증가 함수 (clips.id가 TEXT이므로 TEXT 파라미터)
CREATE OR REPLACE FUNCTION increment_clip_used_count(clip_id TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE clips SET used_count = used_count + 1 WHERE id = clip_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Videos (생성된 영상 테이블)
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID NOT NULL REFERENCES churches(id),
    title TEXT,
    audio_file_path TEXT NOT NULL,  -- 원본 MP3 R2 URL
    video_file_path TEXT,  -- 생성된 MP4 R2 URL
    srt_file_path TEXT,  -- SRT 자막 R2 URL
    duration INTEGER,  -- 초
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,
    clips_used JSONB DEFAULT '[]',  -- 사용된 클립 ID 배열 (TEXT 형태)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX idx_videos_church_id ON videos(church_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);

-- 5. 업데이트 트리거
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER churches_updated_at
    BEFORE UPDATE ON churches
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- 6. RLS (Row Level Security) 정책 - 필요시 활성화
-- ALTER TABLE churches ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

-- 7. 테스트 데이터 (개발용)
-- 테스트 교회
INSERT INTO churches (id, name, pack_id, contact_email) VALUES
    ('00000000-0000-0000-0000-000000000001', '테스트교회', 'pack-free', 'test@example.com')
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE churches IS '교회 정보';
COMMENT ON TABLE packs IS '배경 클립 팩 (교회별 전용)';
COMMENT ON TABLE clips IS '개별 배경 클립';
COMMENT ON TABLE videos IS '생성된 QT 영상';
