-- 20260117_add_bgm_info_to_videos.sql
-- videos 테이블에 배경음악 정보 저장용 컬럼 추가

ALTER TABLE videos 
ADD COLUMN IF NOT EXISTS bgm_id TEXT,
ADD COLUMN IF NOT EXISTS bgm_volume FLOAT DEFAULT 0.12;

COMMENT ON COLUMN videos.bgm_id IS '사용된 배경음악 ID';
COMMENT ON COLUMN videos.bgm_volume IS '배경음악 볼륨 (0.0 ~ 1.0)';
