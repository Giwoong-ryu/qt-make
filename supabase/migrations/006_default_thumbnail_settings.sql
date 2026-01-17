-- 006: 교회별 기본 썸네일 설정
-- 실행: Supabase Dashboard > SQL Editor

-- 1. churches 테이블에 기본 썸네일 레이아웃 컬럼 추가
ALTER TABLE churches
ADD COLUMN IF NOT EXISTS default_thumbnail_layout JSONB;

-- 2. videos 테이블에 thumbnail_layout 컬럼 추가 (없는 경우)
ALTER TABLE videos
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;

ALTER TABLE videos
ADD COLUMN IF NOT EXISTS thumbnail_layout JSONB;

-- 3. 기본 썸네일 레이아웃 저장 API용 인덱스
CREATE INDEX IF NOT EXISTS idx_churches_default_thumbnail
ON churches USING GIN (default_thumbnail_layout);

-- 4. 코멘트
COMMENT ON COLUMN churches.default_thumbnail_layout IS '교회 기본 썸네일 레이아웃 (새 영상에 자동 적용)';
COMMENT ON COLUMN videos.thumbnail_layout IS '개별 영상 썸네일 레이아웃';
COMMENT ON COLUMN videos.thumbnail_url IS '생성된 썸네일 이미지 URL';

-- 5. 확인
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'churches' AND column_name = 'default_thumbnail_layout';

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'videos' AND column_name IN ('thumbnail_url', 'thumbnail_layout');
