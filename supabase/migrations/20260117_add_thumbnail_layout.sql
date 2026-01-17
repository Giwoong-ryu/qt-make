-- 20260117_add_thumbnail_layout.sql
-- videos 테이블에 썸네일 레이아웃 저장용 컬럼 추가

ALTER TABLE videos 
ADD COLUMN IF NOT EXISTS thumbnail_layout JSONB;

COMMENT ON COLUMN videos.thumbnail_layout IS '썸네일 에디터 레이아웃 설정 (텍스트 박스, 배경 등)';
