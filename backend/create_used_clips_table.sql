-- 전역 클립 중복 방지 테이블
-- 최근 10개 영상에서 사용된 클립 ID 추적

CREATE TABLE IF NOT EXISTS used_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id TEXT NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    clip_id INTEGER NOT NULL,  -- Pexels video ID
    clip_url TEXT,             -- 클립 다운로드 URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 복합 유니크: 같은 영상에서 같은 클립은 여러 번 사용 가능 (루프용)
    UNIQUE(video_id, clip_id)
);

-- 인덱스: church_id 기준 최근 영상 조회 속도 향상
CREATE INDEX IF NOT EXISTS idx_used_clips_church_created
ON used_clips(church_id, created_at DESC);

-- 인덱스: clip_id 기준 중복 체크 속도 향상
CREATE INDEX IF NOT EXISTS idx_used_clips_clip_id
ON used_clips(clip_id);

COMMENT ON TABLE used_clips IS '전역 클립 중복 방지: 최근 10개 영상에서 사용된 클립 ID 추적';
COMMENT ON COLUMN used_clips.clip_id IS 'Pexels video ID (integer)';
COMMENT ON COLUMN used_clips.clip_url IS '클립 다운로드 URL (디버깅용)';
