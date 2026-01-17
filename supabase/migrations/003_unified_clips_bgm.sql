-- ============================================
-- QT Video SaaS - 통합 클립/BGM 스키마 (충돌 해결)
-- ============================================
-- 기존 schema.sql의 packs/clips 구조와 002의 clip_packs/clips/bgms 통합

-- 1. BGM 테이블 생성 (신규)
CREATE TABLE IF NOT EXISTS bgms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'calm', 'worship', 'piano', 'acoustic'
    file_path TEXT NOT NULL,
    duration INTEGER NOT NULL,
    preview_url TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 기존 packs 테이블에 누락된 컬럼 추가
ALTER TABLE packs
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
ADD COLUMN IF NOT EXISTS is_free BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;

-- 3. 기존 clips 테이블에 누락된 컬럼 추가
ALTER TABLE clips
ADD COLUMN IF NOT EXISTS name TEXT,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;

-- 4. videos 테이블 확장
ALTER TABLE videos
ADD COLUMN IF NOT EXISTS bgm_id TEXT,
ADD COLUMN IF NOT EXISTS bgm_volume REAL DEFAULT 0.12,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;

-- clips_used가 UUID[]인 경우 JSONB로 변환할 필요 없음 (기존 유지)

-- 5. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_bgms_category ON bgms(category);
CREATE INDEX IF NOT EXISTS idx_packs_is_active ON packs(is_active) WHERE is_active = true;

-- 6. RLS 정책
ALTER TABLE bgms ENABLE ROW LEVEL SECURITY;

-- BGM 읽기 정책 (모든 사용자 조회 가능)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'Anyone can view bgms'
    ) THEN
        CREATE POLICY "Anyone can view bgms" ON bgms FOR SELECT USING (is_active = true);
    END IF;
END $$;

-- 7. 기존 pack-free 업데이트
UPDATE packs SET
    is_free = true,
    is_active = true,
    sort_order = 1
WHERE id = 'pack-free';
