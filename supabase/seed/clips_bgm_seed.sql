-- ============================================
-- QT Video SaaS - 샘플 데이터 (클립/BGM)
-- ============================================

-- 배경팩 샘플 데이터
INSERT INTO clip_packs (id, name, description, thumbnail_url, clip_count, is_free, sort_order) VALUES
('pack-free', '기본 배경팩', '무료로 제공되는 기본 배경 영상들', '/thumbnails/packs/free.jpg', 12, true, 1),
('pack-nature', '자연 배경팩', '아름다운 자연 풍경 배경', '/thumbnails/packs/nature.jpg', 20, false, 2),
('pack-church', '교회 배경팩', '교회 및 예배 관련 배경', '/thumbnails/packs/church.jpg', 15, false, 3),
('pack-abstract', '추상 배경팩', '모던한 추상 그래픽 배경', '/thumbnails/packs/abstract.jpg', 18, false, 4)
ON CONFLICT (id) DO NOTHING;

-- 기본 배경팩 클립 데이터 (pack-free)
INSERT INTO clips (id, pack_id, name, category, thumbnail_url, file_path, duration, sort_order) VALUES
-- 자연 카테고리
('clip-free-001', 'pack-free', '잔잔한 호수', 'nature', '/thumbnails/clips/lake.jpg', 'clips/free/lake.mp4', 30, 1),
('clip-free-002', 'pack-free', '숲속 햇살', 'nature', '/thumbnails/clips/forest.jpg', 'clips/free/forest.mp4', 30, 2),
('clip-free-003', 'pack-free', '구름 타임랩스', 'nature', '/thumbnails/clips/clouds.jpg', 'clips/free/clouds.mp4', 30, 3),
('clip-free-004', 'pack-free', '산 일출', 'nature', '/thumbnails/clips/sunrise.jpg', 'clips/free/sunrise.mp4', 30, 4),

-- 추상 카테고리
('clip-free-005', 'pack-free', '부드러운 그라데이션', 'abstract', '/thumbnails/clips/gradient.jpg', 'clips/free/gradient.mp4', 30, 5),
('clip-free-006', 'pack-free', '파티클 움직임', 'abstract', '/thumbnails/clips/particles.jpg', 'clips/free/particles.mp4', 30, 6),
('clip-free-007', 'pack-free', '물결 패턴', 'abstract', '/thumbnails/clips/waves.jpg', 'clips/free/waves.mp4', 30, 7),
('clip-free-008', 'pack-free', '빛 보케', 'abstract', '/thumbnails/clips/bokeh.jpg', 'clips/free/bokeh.mp4', 30, 8),

-- 교회 카테고리
('clip-free-009', 'pack-free', '스테인드글라스', 'church', '/thumbnails/clips/stained.jpg', 'clips/free/stained.mp4', 30, 9),
('clip-free-010', 'pack-free', '촛불', 'church', '/thumbnails/clips/candle.jpg', 'clips/free/candle.mp4', 30, 10),
('clip-free-011', 'pack-free', '십자가 실루엣', 'church', '/thumbnails/clips/cross.jpg', 'clips/free/cross.mp4', 30, 11),
('clip-free-012', 'pack-free', '성경책', 'church', '/thumbnails/clips/bible.jpg', 'clips/free/bible.mp4', 30, 12)
ON CONFLICT (id) DO NOTHING;

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

-- 기본 BGM 설정 (bgm-001을 기본값으로)
-- 프론트엔드에서 selectedBGM이 null이면 bgm-001 사용
