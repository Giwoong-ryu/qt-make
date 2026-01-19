-- 겨자씨 구문 교정 추가
-- 실행: Supabase Dashboard > SQL Editor에 복사 후 실행

INSERT INTO global_dictionary (original, replacement, category, priority, is_active)
VALUES ('겨자씨 하나로', '겨자씨 한 알이', 'bible', 100, true)
ON CONFLICT (original) DO UPDATE SET
    replacement = EXCLUDED.replacement,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active;

-- 확인 쿼리
SELECT * FROM global_dictionary WHERE original LIKE '%겨자씨%';
