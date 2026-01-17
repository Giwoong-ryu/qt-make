-- ============================================
-- QT Video SaaS - increment_clip_used_count 함수 수정
-- ============================================
-- 문제: schema.sql에서 UUID 타입으로 정의했지만
--       실제 clips.id는 TEXT 타입 ('clip-moody-09' 등)
-- 해결: 함수 파라미터를 TEXT로 변경

-- 기존 함수 삭제 (UUID 버전)
DROP FUNCTION IF EXISTS increment_clip_used_count(UUID);

-- 새 함수 생성 (TEXT 버전)
CREATE OR REPLACE FUNCTION increment_clip_used_count(clip_id TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE clips SET used_count = used_count + 1 WHERE id = clip_id;
END;
$$ LANGUAGE plpgsql;

-- 동작 확인용 코멘트
COMMENT ON FUNCTION increment_clip_used_count(TEXT) IS 'clips.id가 TEXT 타입이므로 TEXT 파라미터 사용';
