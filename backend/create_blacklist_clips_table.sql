-- 얼굴 포함 클립 영구 블랙리스트 테이블
-- Gemini Vision이 ACCEPT했지만 실제로 얼굴이 있는 클립 차단

CREATE TABLE IF NOT EXISTS blacklist_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id INTEGER NOT NULL UNIQUE,  -- Pexels video ID
    reason TEXT NOT NULL,              -- 차단 이유 (예: "nun face visible")
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스: clip_id 기준 빠른 조회
CREATE INDEX IF NOT EXISTS idx_blacklist_clips_id
ON blacklist_clips(clip_id);

COMMENT ON TABLE blacklist_clips IS '얼굴 포함 클립 영구 블랙리스트 (Gemini Vision 우회용)';
COMMENT ON COLUMN blacklist_clips.clip_id IS 'Pexels video ID (integer) - 영구 차단';
COMMENT ON COLUMN blacklist_clips.reason IS '차단 이유 (디버깅용)';

-- 초기 블랙리스트 추가
INSERT INTO blacklist_clips (clip_id, reason)
VALUES
    (8719740, 'nun with face visible (Gemini Vision false positive)')
ON CONFLICT (clip_id) DO NOTHING;
