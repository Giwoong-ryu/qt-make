-- 겨자씨 구문 교정 추가 (재확인)
-- 실행: Supabase Dashboard > SQL Editor

-- 1. 기존 데이터 확인
SELECT * FROM global_dictionary WHERE original LIKE '%겨자씨%';

-- 2. 전체 데이터 개수 확인
SELECT COUNT(*) as total_count FROM global_dictionary WHERE is_active = true;

-- 3. 겨자씨 데이터 삭제 후 재추가 (혹시 중복 방지)
DELETE FROM global_dictionary WHERE original = '겨자씨 하나로';

-- 4. 다시 추가
INSERT INTO global_dictionary (original, replacement, category, priority, is_active)
VALUES ('겨자씨 하나로', '겨자씨 한 알이', 'bible', 100, true);

-- 5. 최종 확인
SELECT original, replacement, category, priority, is_active
FROM global_dictionary
WHERE is_active = true
ORDER BY priority DESC, category;
