-- =============================================
-- 썸네일 컨셉 시스템 마이그레이션
-- 방향 3: 컨셉 선택 + 제목 오버레이
-- =============================================

-- 1. 썸네일 컨셉 카테고리 테이블
CREATE TABLE IF NOT EXISTS thumbnail_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,  -- 프론트엔드 아이콘 (lucide-react)
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 썸네일 템플릿 이미지 테이블
CREATE TABLE IF NOT EXISTS thumbnail_templates (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    category_id TEXT NOT NULL REFERENCES thumbnail_categories(id),
    name TEXT NOT NULL,
    image_url TEXT NOT NULL,  -- R2에 저장된 배경 이미지
    text_color TEXT DEFAULT '#FFFFFF',  -- 제목 텍스트 색상
    text_position TEXT DEFAULT 'center',  -- top, center, bottom
    overlay_opacity FLOAT DEFAULT 0.3,  -- 어두운 오버레이 투명도
    is_active BOOLEAN DEFAULT true,
    used_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 교회별 썸네일 설정 테이블
-- 참고: church_id는 videos 테이블의 church_id와 동일한 TEXT 타입 사용 (UUID 대신)
CREATE TABLE IF NOT EXISTS church_thumbnail_settings (
    church_id TEXT PRIMARY KEY,
    default_category_id TEXT REFERENCES thumbnail_categories(id),
    custom_font TEXT,  -- 커스텀 폰트 (NULL이면 기본 폰트)
    custom_text_color TEXT,  -- 커스텀 텍스트 색상
    logo_url TEXT,  -- 교회 로고 (옵션)
    logo_position TEXT DEFAULT 'bottom-right',  -- 로고 위치
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. videos 테이블에 컬럼 추가
ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_template_id TEXT REFERENCES thumbnail_templates(id);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_title TEXT;  -- 썸네일에 표시할 제목

-- =============================================
-- 기본 카테고리 시드 데이터
-- =============================================

INSERT INTO thumbnail_categories (id, name, description, icon, sort_order) VALUES
    ('nature', '자연/평화', '산, 호수, 숲 등 평화로운 자연 풍경', 'Mountain', 1),
    ('scripture', '말씀/성경', '성경책, 십자가, 빛 등 신앙 이미지', 'BookOpen', 2),
    ('prayer', '기도/묵상', '촛불, 새벽, 고요한 분위기', 'Heart', 3),
    ('spring', '봄', '벚꽃, 새싹, 따뜻한 봄 풍경', 'Flower2', 4),
    ('summer', '여름', '푸른 바다, 하늘, 시원한 이미지', 'Sun', 5),
    ('autumn', '가을', '단풍, 낙엽, 풍성한 수확', 'Leaf', 6),
    ('winter', '겨울', '눈, 크리스마스, 따뜻한 분위기', 'Snowflake', 7),
    ('easter', '부활절', '부활, 새 생명, 희망', 'Sunrise', 8),
    ('christmas', '성탄절', '아기 예수, 별, 성탄 분위기', 'Star', 9),
    ('thanksgiving', '추수감사절', '풍성한 수확, 감사', 'Wheat', 10)
ON CONFLICT (id) DO NOTHING;

-- =============================================
-- 기본 템플릿 시드 데이터 (예시)
-- 실제 이미지는 R2에 업로드 후 URL 업데이트 필요
-- =============================================

INSERT INTO thumbnail_templates (id, category_id, name, image_url, text_color, text_position) VALUES
    -- 자연/평화
    ('nature-001', 'nature', '평화로운 호수', 'templates/nature/lake-peaceful.jpg', '#FFFFFF', 'center'),
    ('nature-002', 'nature', '산과 구름', 'templates/nature/mountain-clouds.jpg', '#FFFFFF', 'bottom'),
    ('nature-003', 'nature', '숲속 햇살', 'templates/nature/forest-sunlight.jpg', '#FFFFFF', 'center'),

    -- 말씀/성경
    ('scripture-001', 'scripture', '열린 성경책', 'templates/scripture/open-bible.jpg', '#FFFFFF', 'top'),
    ('scripture-002', 'scripture', '십자가와 빛', 'templates/scripture/cross-light.jpg', '#FFFFFF', 'center'),
    ('scripture-003', 'scripture', '말씀 두루마리', 'templates/scripture/scroll.jpg', '#F5E6D3', 'center'),

    -- 기도/묵상
    ('prayer-001', 'prayer', '새벽 촛불', 'templates/prayer/candle-dawn.jpg', '#FFF8E7', 'center'),
    ('prayer-002', 'prayer', '기도하는 손', 'templates/prayer/praying-hands.jpg', '#FFFFFF', 'bottom'),
    ('prayer-003', 'prayer', '고요한 새벽', 'templates/prayer/quiet-dawn.jpg', '#FFFFFF', 'center'),

    -- 계절별
    ('spring-001', 'spring', '벚꽃 길', 'templates/spring/cherry-blossom.jpg', '#FFFFFF', 'center'),
    ('summer-001', 'summer', '푸른 바다', 'templates/summer/blue-ocean.jpg', '#FFFFFF', 'center'),
    ('autumn-001', 'autumn', '단풍 숲', 'templates/autumn/autumn-forest.jpg', '#FFFFFF', 'center'),
    ('winter-001', 'winter', '눈 내리는 밤', 'templates/winter/snowy-night.jpg', '#FFFFFF', 'center'),

    -- 절기별
    ('easter-001', 'easter', '부활의 아침', 'templates/easter/resurrection.jpg', '#FFFFFF', 'center'),
    ('christmas-001', 'christmas', '성탄의 별', 'templates/christmas/star.jpg', '#FFD700', 'center'),
    ('thanksgiving-001', 'thanksgiving', '풍성한 수확', 'templates/thanksgiving/harvest.jpg', '#FFFFFF', 'bottom')
ON CONFLICT (id) DO NOTHING;

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_thumbnail_templates_category ON thumbnail_templates(category_id);
CREATE INDEX IF NOT EXISTS idx_thumbnail_templates_active ON thumbnail_templates(is_active);
