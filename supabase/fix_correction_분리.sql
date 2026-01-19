-- 분할 후에도 매칭되도록 개별 단어로 등록
-- 실행: Supabase Dashboard > SQL Editor

-- 기존 "겨자씨 하나로" 삭제
DELETE FROM global_dictionary WHERE original = '겨자씨 하나로';

-- 개별 단어로 등록 (분할되어도 매칭됨)
INSERT INTO global_dictionary (original, replacement, category, priority, is_active) VALUES
('하나로 같으니', '한 알이 같으니', 'bible', 100, true);

-- 확인
SELECT * FROM global_dictionary WHERE original LIKE '%하나로%' OR original LIKE '%한 알%';
