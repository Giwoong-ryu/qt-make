-- ============================================
-- QT Video SaaS Week 2 - 마이그레이션 + 시드 데이터
-- Supabase SQL Editor에서 이 파일 전체를 복사/붙여넣기 후 실행
-- ============================================
-- 현재 스키마 기반 (2026-01-14 확인)
-- churches: id, name, pack_id, created_at
-- packs: id, name, description, is_free, created_at
-- clips: id, pack_id, file_path, category, duration, is_active, used_count, created_at
-- videos: id, church_id, title, status, duration, audio_file_path, video_file_path, srt_file_path, error_message, created_at, completed_at, clips_used

-- ================================================
-- PART 1: BGM 테이블 생성
-- ================================================

CREATE TABLE IF NOT EXISTS bgms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration INTEGER NOT NULL,
    preview_url TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 설정
ALTER TABLE bgms ENABLE ROW LEVEL SECURITY;

-- 읽기 정책 (인증 없이 조회 가능)
DROP POLICY IF EXISTS "Anyone can view bgms" ON bgms;
CREATE POLICY "Anyone can view bgms" ON bgms FOR SELECT USING (is_active = true);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_bgms_category ON bgms(category);

-- ================================================
-- PART 2: videos 테이블 확장
-- ================================================

ALTER TABLE videos
ADD COLUMN IF NOT EXISTS bgm_id TEXT,
ADD COLUMN IF NOT EXISTS bgm_volume REAL DEFAULT 0.12,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
ADD COLUMN IF NOT EXISTS thumbnail_layout JSONB;

-- ================================================
-- PART 3: BGM 샘플 데이터
-- ================================================

INSERT INTO bgms (id, name, category, file_path, duration, preview_url, sort_order) VALUES
('bgm-001', '평화로운 아침', 'calm', 'bgm/peaceful_morning.mp3', 180, 'bgm/preview/peaceful_morning.mp3', 1),
('bgm-002', '조용한 묵상', 'calm', 'bgm/quiet_meditation.mp3', 240, 'bgm/preview/quiet_meditation.mp3', 2),
('bgm-003', '고요한 시간', 'calm', 'bgm/still_time.mp3', 200, 'bgm/preview/still_time.mp3', 3),
('bgm-004', '부드러운 피아노', 'piano', 'bgm/soft_piano.mp3', 210, 'bgm/preview/soft_piano.mp3', 4),
('bgm-005', '은혜의 선율', 'piano', 'bgm/grace_melody.mp3', 180, 'bgm/preview/grace_melody.mp3', 5),
('bgm-006', '아침 피아노', 'piano', 'bgm/morning_piano.mp3', 190, 'bgm/preview/morning_piano.mp3', 6),
('bgm-007', '찬양 배경', 'worship', 'bgm/worship_bg.mp3', 300, 'bgm/preview/worship_bg.mp3', 7),
('bgm-008', '예배 인스트루멘탈', 'worship', 'bgm/worship_inst.mp3', 280, 'bgm/preview/worship_inst.mp3', 8),
('bgm-009', '기타 어쿠스틱', 'acoustic', 'bgm/acoustic_guitar.mp3', 220, 'bgm/preview/acoustic_guitar.mp3', 9),
('bgm-010', '자연의 소리', 'acoustic', 'bgm/nature_sounds.mp3', 300, 'bgm/preview/nature_sounds.mp3', 10)
ON CONFLICT (id) DO NOTHING;

-- ================================================
-- PART 4: 데모 교회 (기존 스키마에 맞춤)
-- ================================================

INSERT INTO churches (id, name, pack_id) VALUES
('00000000-0000-0000-0000-000000000001', '데모교회', 'pack-free')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ================================================
-- 검증 쿼리 (실행 후 결과 확인)
-- ================================================

SELECT 'bgms' as table_name, COUNT(*) as count FROM bgms
UNION ALL
SELECT 'packs', COUNT(*) FROM packs
UNION ALL
SELECT 'clips', COUNT(*) FROM clips
UNION ALL
SELECT 'churches', COUNT(*) FROM churches
UNION ALL
SELECT 'videos', COUNT(*) FROM videos;
