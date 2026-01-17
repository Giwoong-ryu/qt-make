-- ============================================
-- QT Video SaaS - 클립/BGM 스키마 (Week 2)
-- ============================================

-- 배경팩 테이블
CREATE TABLE IF NOT EXISTS clip_packs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    clip_count INTEGER DEFAULT 0,
    is_free BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 배경 클립 테이블
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES clip_packs(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'nature', 'city', 'abstract', 'church' 등
    thumbnail_url TEXT,
    file_path TEXT NOT NULL,  -- R2 경로
    duration INTEGER NOT NULL,  -- 초 단위
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- BGM 테이블
CREATE TABLE IF NOT EXISTS bgms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'calm', 'worship', 'piano', 'acoustic' 등
    file_path TEXT NOT NULL,  -- R2 경로
    duration INTEGER NOT NULL,  -- 초 단위
    preview_url TEXT,  -- 미리듣기용 짧은 버전
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- videos 테이블 확장 (기존 테이블에 컬럼 추가)
ALTER TABLE videos
ADD COLUMN IF NOT EXISTS clips_used JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS bgm_id TEXT,
ADD COLUMN IF NOT EXISTS bgm_volume REAL DEFAULT 0.12,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_clips_pack_id ON clips(pack_id);
CREATE INDEX IF NOT EXISTS idx_clips_category ON clips(category);
CREATE INDEX IF NOT EXISTS idx_bgms_category ON bgms(category);
CREATE INDEX IF NOT EXISTS idx_videos_church_id ON videos(church_id);

-- RLS 정책 (Row Level Security)
ALTER TABLE clip_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE bgms ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 클립/BGM 조회 가능 (읽기 전용)
CREATE POLICY "Anyone can view clip_packs" ON clip_packs FOR SELECT USING (is_active = true);
CREATE POLICY "Anyone can view clips" ON clips FOR SELECT USING (is_active = true);
CREATE POLICY "Anyone can view bgms" ON bgms FOR SELECT USING (is_active = true);
