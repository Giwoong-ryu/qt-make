-- 008: clips_metadata 컬럼 추가 (Pexels URL 저장용)
-- 재생성 시 Pexels API 클립을 다시 사용하기 위해 URL과 메타데이터를 저장

-- 1. base_video_path: 합성된 베이스 영상 URL (인트로/아웃트로 없이 합성된 영상)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS base_video_path TEXT;

-- 2. clips_metadata: Pexels 클립 메타데이터 배열
-- 구조: [{"id": "pexels_123", "url": "https://...", "duration": 30, "trim_duration": 15, "start_time": 0, "end_time": 15}, ...]
ALTER TABLE videos ADD COLUMN IF NOT EXISTS clips_metadata JSONB DEFAULT '[]';

-- 인덱스 (필요시)
-- CREATE INDEX idx_videos_clips_metadata ON videos USING GIN (clips_metadata);

COMMENT ON COLUMN videos.base_video_path IS '합성된 베이스 영상 R2 URL (인트로/아웃트로 추가 전)';
COMMENT ON COLUMN videos.clips_metadata IS 'Pexels 클립 메타데이터 배열 (재생성 시 URL 재사용)';
