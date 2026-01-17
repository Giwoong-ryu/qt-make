-- ============================================
-- QT Video SaaS - BGM 샘플 데이터
-- ============================================

-- BGM 샘플 데이터
INSERT INTO bgms (id, name, category, file_path, duration, preview_url, sort_order) VALUES
-- 잔잔한 카테고리
('bgm-001', '평화로운 아침', 'calm', 'bgm/peaceful_morning.mp3', 180, 'bgm/preview/peaceful_morning.mp3', 1),
('bgm-002', '조용한 묵상', 'calm', 'bgm/quiet_meditation.mp3', 240, 'bgm/preview/quiet_meditation.mp3', 2),
('bgm-003', '고요한 시간', 'calm', 'bgm/still_time.mp3', 200, 'bgm/preview/still_time.mp3', 3),

-- 피아노 카테고리
('bgm-004', '부드러운 피아노', 'piano', 'bgm/soft_piano.mp3', 210, 'bgm/preview/soft_piano.mp3', 4),
('bgm-005', '은혜의 선율', 'piano', 'bgm/grace_melody.mp3', 180, 'bgm/preview/grace_melody.mp3', 5),
('bgm-006', '아침 피아노', 'piano', 'bgm/morning_piano.mp3', 190, 'bgm/preview/morning_piano.mp3', 6),

-- 워십 카테고리
('bgm-007', '찬양 배경', 'worship', 'bgm/worship_bg.mp3', 300, 'bgm/preview/worship_bg.mp3', 7),
('bgm-008', '예배 인스트루멘탈', 'worship', 'bgm/worship_inst.mp3', 280, 'bgm/preview/worship_inst.mp3', 8),

-- 어쿠스틱 카테고리
('bgm-009', '기타 어쿠스틱', 'acoustic', 'bgm/acoustic_guitar.mp3', 220, 'bgm/preview/acoustic_guitar.mp3', 9),
('bgm-010', '자연의 소리', 'acoustic', 'bgm/nature_sounds.mp3', 300, 'bgm/preview/nature_sounds.mp3', 10)
ON CONFLICT (id) DO NOTHING;

-- 기존 clips 테이블의 name 컬럼 업데이트 (있는 경우)
UPDATE clips SET name = file_name WHERE name IS NULL AND file_name IS NOT NULL;
