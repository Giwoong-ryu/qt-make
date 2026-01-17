-- ============================================
-- 통합 사전 시스템 마이그레이션
-- 2026-01-17
-- ============================================
-- 구조:
-- 1. global_dictionary - 모든 사용자가 공유하는 통합 사전 (성경 고유명사 등)
-- 2. replacement_dictionary - 기존 교회별 사전 (유지)
--
-- 적용 순서: 통합 사전 먼저 → 교회별 사전 (교회별이 우선)
-- ============================================

-- ================================================
-- PART 1: 통합 사전 테이블 생성
-- ================================================

CREATE TABLE IF NOT EXISTS global_dictionary (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL,                    -- 카테고리: 'bible_person', 'bible_place', 'christian_term', 'common'
    original TEXT NOT NULL,                    -- 잘못 인식되는 텍스트
    replacement TEXT NOT NULL,                 -- 올바른 텍스트
    description TEXT,                          -- 설명 (선택)
    priority INTEGER DEFAULT 0,                -- 우선순위 (높을수록 먼저 적용)
    is_active BOOLEAN DEFAULT true,            -- 활성화 여부
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 중복 방지
    UNIQUE(original)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_global_dictionary_category ON global_dictionary(category);
CREATE INDEX IF NOT EXISTS idx_global_dictionary_active ON global_dictionary(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_global_dictionary_original ON global_dictionary(original);

-- RLS 설정
ALTER TABLE global_dictionary ENABLE ROW LEVEL SECURITY;

-- 읽기 정책 (모든 사용자 조회 가능)
DROP POLICY IF EXISTS "Anyone can view global_dictionary" ON global_dictionary;
CREATE POLICY "Anyone can view global_dictionary" ON global_dictionary
    FOR SELECT USING (is_active = true);

-- 관리자만 수정 가능 (service_role)
DROP POLICY IF EXISTS "Service role can manage global_dictionary" ON global_dictionary;
CREATE POLICY "Service role can manage global_dictionary" ON global_dictionary
    FOR ALL USING (auth.role() = 'service_role');

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_global_dictionary_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_global_dictionary_updated_at ON global_dictionary;
CREATE TRIGGER trigger_global_dictionary_updated_at
    BEFORE UPDATE ON global_dictionary
    FOR EACH ROW
    EXECUTE FUNCTION update_global_dictionary_updated_at();

-- ================================================
-- PART 2: 성경 인명 사전 (약 100개)
-- ================================================

INSERT INTO global_dictionary (category, original, replacement, description, priority) VALUES
-- 구약 주요 인물
('bible_person', '아브라함', '아브라함', '족장 - 믿음의 조상', 100),
('bible_person', '아브라힘', '아브라함', '아브라함 오인식', 100),
('bible_person', '아부라함', '아브라함', '아브라함 오인식', 100),
('bible_person', '이삭', '이삭', '아브라함의 아들', 100),
('bible_person', '이싹', '이삭', '이삭 오인식', 100),
('bible_person', '야곱', '야곱', '이삭의 아들, 이스라엘', 100),
('bible_person', '야콥', '야곱', '야곱 오인식', 100),
('bible_person', '요셉', '요셉', '야곱의 아들', 100),
('bible_person', '요섭', '요셉', '요셉 오인식', 100),
('bible_person', '모세', '모세', '출애굽 지도자', 100),
('bible_person', '모쉐', '모세', '모세 오인식', 100),
('bible_person', '다윗', '다윗', '이스라엘 왕', 100),
('bible_person', '다비드', '다윗', '다윗 오인식', 100),
('bible_person', '데이빗', '다윗', '다윗 영어식', 100),
('bible_person', '솔로몬', '솔로몬', '다윗의 아들, 지혜의 왕', 100),
('bible_person', '솔로먼', '솔로몬', '솔로몬 오인식', 100),
('bible_person', '엘리야', '엘리야', '선지자', 100),
('bible_person', '엘리아', '엘리야', '엘리야 오인식', 100),
('bible_person', '엘리사', '엘리사', '엘리야의 제자', 100),
('bible_person', '이사야', '이사야', '대선지자', 100),
('bible_person', '이사이아', '이사야', '이사야 오인식', 100),
('bible_person', '예레미야', '예레미야', '대선지자', 100),
('bible_person', '제레미야', '예레미야', '예레미야 오인식', 100),
('bible_person', '에스겔', '에스겔', '대선지자', 100),
('bible_person', '다니엘', '다니엘', '대선지자', 100),
('bible_person', '대니얼', '다니엘', '다니엘 영어식', 100),
('bible_person', '호세아', '호세아', '소선지자', 100),
('bible_person', '요나', '요나', '소선지자', 100),
('bible_person', '느헤미야', '느헤미야', '성벽 재건자', 100),
('bible_person', '에스라', '에스라', '서기관', 100),

-- 신약 주요 인물
('bible_person', '예수', '예수', '구세주', 100),
('bible_person', '예수님', '예수님', '구세주 경칭', 100),
('bible_person', '예수 그리스도', '예수 그리스도', '그리스도', 100),
('bible_person', '예수그리스도', '예수 그리스도', '띄어쓰기', 100),
('bible_person', '베드로', '베드로', '12제자, 수제자', 100),
('bible_person', '베들로', '베드로', '베드로 오인식', 100),
('bible_person', '피터', '베드로', '베드로 영어식', 100),
('bible_person', '바울', '바울', '사도', 100),
('bible_person', '바올', '바울', '바울 오인식', 100),
('bible_person', '폴', '바울', '바울 영어식', 100),
('bible_person', '요한', '요한', '사도, 복음서 저자', 100),
('bible_person', '존', '요한', '요한 영어식', 100),
('bible_person', '마태', '마태', '세리, 복음서 저자', 100),
('bible_person', '마테오', '마태', '마태 오인식', 100),
('bible_person', '마가', '마가', '복음서 저자', 100),
('bible_person', '마르코', '마가', '마가 오인식', 100),
('bible_person', '누가', '누가', '의사, 복음서 저자', 100),
('bible_person', '루가', '누가', '누가 오인식', 100),
('bible_person', '야고보', '야고보', '12제자', 100),
('bible_person', '빌립', '빌립', '12제자', 100),
('bible_person', '필립', '빌립', '빌립 오인식', 100),
('bible_person', '도마', '도마', '12제자', 100),
('bible_person', '토마스', '도마', '도마 영어식', 100),
('bible_person', '안드레', '안드레', '베드로의 형제', 100),
('bible_person', '앤드류', '안드레', '안드레 영어식', 100),
('bible_person', '마리아', '마리아', '예수의 어머니', 100),
('bible_person', '막달라 마리아', '막달라 마리아', '예수의 제자', 100),
('bible_person', '니고데모', '니고데모', '바리새인, 예수를 찾아옴', 100),
('bible_person', '니코데모', '니고데모', '니고데모 오인식', 100),
('bible_person', '삭게오', '삭게오', '세리장', 100),
('bible_person', '사게오', '삭게오', '삭게오 오인식', 100),
('bible_person', '바나바', '바나바', '바울의 동역자', 100),
('bible_person', '디모데', '디모데', '바울의 제자', 100),
('bible_person', '티모시', '디모데', '디모데 영어식', 100),
('bible_person', '실라', '실라', '바울의 동역자', 100),
('bible_person', '아볼로', '아볼로', '설교자', 100),
('bible_person', '브리스길라', '브리스길라', '아굴라의 아내', 100),
('bible_person', '아굴라', '아굴라', '브리스길라의 남편', 100)
ON CONFLICT (original) DO UPDATE SET
    replacement = EXCLUDED.replacement,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ================================================
-- PART 3: 성경 지명 사전 (약 50개)
-- ================================================

INSERT INTO global_dictionary (category, original, replacement, description, priority) VALUES
-- 주요 지명
('bible_place', '예루살렘', '예루살렘', '이스라엘 수도', 100),
('bible_place', '예루샬렘', '예루살렘', '예루살렘 오인식', 100),
('bible_place', '베들레헴', '베들레헴', '예수 탄생지', 100),
('bible_place', '벳레헴', '베들레헴', '베들레헴 오인식', 100),
('bible_place', '나사렛', '나사렛', '예수 성장지', 100),
('bible_place', '나자렛', '나사렛', '나사렛 오인식', 100),
('bible_place', '갈릴리', '갈릴리', '예수 사역지', 100),
('bible_place', '갈릴래아', '갈릴리', '갈릴리 오인식', 100),
('bible_place', '가버나움', '가버나움', '예수 사역 중심지', 100),
('bible_place', '가나안', '가나안', '약속의 땅', 100),
('bible_place', '카난', '가나안', '가나안 오인식', 100),
('bible_place', '이스라엘', '이스라엘', '하나님의 백성', 100),
('bible_place', '애굽', '애굽', '이집트 구약 명칭', 100),
('bible_place', '에굽', '애굽', '애굽 오인식', 100),
('bible_place', '이집트', '애굽', '이집트 현대식', 90),
('bible_place', '바벨론', '바벨론', '고대 제국', 100),
('bible_place', '바빌론', '바벨론', '바벨론 오인식', 100),
('bible_place', '앗수르', '앗수르', '고대 제국', 100),
('bible_place', '앗시리아', '앗수르', '앗수르 현대식', 90),
('bible_place', '사마리아', '사마리아', '북이스라엘 지역', 100),
('bible_place', '사말리아', '사마리아', '사마리아 오인식', 100),
('bible_place', '유다', '유다', '남왕국', 100),
('bible_place', '유대', '유대', '로마 시대 지명', 100),
('bible_place', '시내산', '시내산', '모세 율법 수여지', 100),
('bible_place', '시나이', '시내산', '시내산 영어식', 100),
('bible_place', '갈보리', '갈보리', '예수 십자가', 100),
('bible_place', '골고다', '골고다', '해골의 장소', 100),
('bible_place', '겟세마네', '겟세마네', '예수 기도처', 100),
('bible_place', '게세마니', '겟세마네', '겟세마네 오인식', 100),
('bible_place', '감람산', '감람산', '올리브산', 100),
('bible_place', '올리브산', '감람산', '감람산 현대식', 90),
('bible_place', '요단강', '요단강', '이스라엘 강', 100),
('bible_place', '요르단강', '요단강', '요단강 현대식', 90),
('bible_place', '홍해', '홍해', '출애굽 기적지', 100),
('bible_place', '갈릴리 바다', '갈릴리 바다', '갈릴리 호수', 100),
('bible_place', '갈릴리 호수', '갈릴리 바다', '갈릴리 바다 현대식', 90),
('bible_place', '빌립보', '빌립보', '바울 서신지', 100),
('bible_place', '에베소', '에베소', '바울 서신지', 100),
('bible_place', '에페소', '에베소', '에베소 오인식', 100),
('bible_place', '골로새', '골로새', '바울 서신지', 100),
('bible_place', '데살로니가', '데살로니가', '바울 서신지', 100),
('bible_place', '살로니가', '데살로니가', '데살로니가 축약', 100),
('bible_place', '고린도', '고린도', '바울 서신지', 100),
('bible_place', '코린토', '고린도', '고린도 오인식', 100),
('bible_place', '로마', '로마', '로마 제국 수도', 100),
('bible_place', '다마스쿠스', '다마스쿠스', '바울 회심지', 100),
('bible_place', '다메섹', '다마스쿠스', '다마스쿠스 구약식', 100)
ON CONFLICT (original) DO UPDATE SET
    replacement = EXCLUDED.replacement,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ================================================
-- PART 4: 기독교 용어 사전 (약 80개)
-- ================================================

INSERT INTO global_dictionary (category, original, replacement, description, priority) VALUES
-- 핵심 신앙 용어
('christian_term', '하나님', '하나님', '신 (개신교)', 100),
('christian_term', '하느님', '하나님', '하나님 가톨릭식', 90),
('christian_term', '여호와', '여호와', '하나님 이름', 100),
('christian_term', '야훼', '여호와', '여호와 히브리식', 90),
('christian_term', '성령', '성령', '삼위일체 중 하나', 100),
('christian_term', '성령님', '성령님', '성령 경칭', 100),
('christian_term', '성령 님', '성령님', '띄어쓰기 오류', 100),
('christian_term', '삼위일체', '삼위일체', '성부, 성자, 성령', 100),
('christian_term', '삼위 일체', '삼위일체', '띄어쓰기 오류', 100),
('christian_term', '구원', '구원', '죄에서의 해방', 100),
('christian_term', '은혜', '은혜', '하나님의 선물', 100),
('christian_term', '은헤', '은혜', '은혜 오인식', 100),
('christian_term', '십자가', '십자가', '예수의 죽음', 100),
('christian_term', '십자 가', '십자가', '띄어쓰기 오류', 100),
('christian_term', '부활', '부활', '죽음에서 살아남', 100),
('christian_term', '복음', '복음', '좋은 소식', 100),
('christian_term', '말씀', '말씀', '성경, 하나님의 말씀', 100),
('christian_term', '말쓰음', '말씀', '말씀 오인식', 100),
('christian_term', '기도', '기도', '하나님과의 대화', 100),
('christian_term', '기도하다', '기도하다', '기도 동사형', 100),
('christian_term', '찬양', '찬양', '하나님께 드리는 노래', 100),
('christian_term', '찬양 하다', '찬양하다', '띄어쓰기 오류', 100),
('christian_term', '예배', '예배', '하나님께 드리는 경배', 100),
('christian_term', '예배 드리다', '예배드리다', '띄어쓰기', 100),
('christian_term', '헌금', '헌금', '하나님께 드리는 돈', 100),
('christian_term', '십일조', '십일조', '수입의 10%', 100),
('christian_term', '십 일조', '십일조', '띄어쓰기 오류', 100),

-- 성경 관련
('christian_term', '구약', '구약', '구약성경', 100),
('christian_term', '구약 성경', '구약성경', '띄어쓰기', 100),
('christian_term', '신약', '신약', '신약성경', 100),
('christian_term', '신약 성경', '신약성경', '띄어쓰기', 100),
('christian_term', '창세기', '창세기', '성경 첫 권', 100),
('christian_term', '창세 기', '창세기', '띄어쓰기 오류', 100),
('christian_term', '출애굽기', '출애굽기', '모세오경', 100),
('christian_term', '레위기', '레위기', '모세오경', 100),
('christian_term', '민수기', '민수기', '모세오경', 100),
('christian_term', '신명기', '신명기', '모세오경', 100),
('christian_term', '시편', '시편', '찬양과 기도의 책', 100),
('christian_term', '잠언', '잠언', '지혜의 책', 100),
('christian_term', '전도서', '전도서', '인생의 책', 100),
('christian_term', '요한복음', '요한복음', '복음서', 100),
('christian_term', '요한 복음', '요한복음', '띄어쓰기', 100),
('christian_term', '마태복음', '마태복음', '복음서', 100),
('christian_term', '마가복음', '마가복음', '복음서', 100),
('christian_term', '누가복음', '누가복음', '복음서', 100),
('christian_term', '사도행전', '사도행전', '초대교회 역사', 100),
('christian_term', '사도 행전', '사도행전', '띄어쓰기', 100),
('christian_term', '로마서', '로마서', '바울 서신', 100),
('christian_term', '고린도전서', '고린도전서', '바울 서신', 100),
('christian_term', '고린도후서', '고린도후서', '바울 서신', 100),
('christian_term', '갈라디아서', '갈라디아서', '바울 서신', 100),
('christian_term', '에베소서', '에베소서', '바울 서신', 100),
('christian_term', '빌립보서', '빌립보서', '바울 서신', 100),
('christian_term', '골로새서', '골로새서', '바울 서신', 100),
('christian_term', '히브리서', '히브리서', '일반 서신', 100),
('christian_term', '요한계시록', '요한계시록', '종말론', 100),
('christian_term', '요한 계시록', '요한계시록', '띄어쓰기', 100),
('christian_term', '계시록', '요한계시록', '요한계시록 축약', 90),

-- 교회 용어
('christian_term', '목사', '목사', '교회 지도자', 100),
('christian_term', '목사님', '목사님', '목사 경칭', 100),
('christian_term', '목사 님', '목사님', '띄어쓰기 오류', 100),
('christian_term', '전도사', '전도사', '교회 직분', 100),
('christian_term', '전도사님', '전도사님', '전도사 경칭', 100),
('christian_term', '장로', '장로', '교회 직분', 100),
('christian_term', '장로님', '장로님', '장로 경칭', 100),
('christian_term', '집사', '집사', '교회 직분', 100),
('christian_term', '집사님', '집사님', '집사 경칭', 100),
('christian_term', '권사', '권사', '교회 직분', 100),
('christian_term', '권사님', '권사님', '권사 경칭', 100),
('christian_term', '성도', '성도', '교회 구성원', 100),
('christian_term', '성도님', '성도님', '성도 경칭', 100),
('christian_term', '형제', '형제', '남성 성도', 100),
('christian_term', '자매', '자매', '여성 성도', 100),
('christian_term', '주일', '주일', '일요일', 100),
('christian_term', '주일 예배', '주일예배', '띄어쓰기', 100),
('christian_term', '수요 예배', '수요예배', '띄어쓰기', 100),
('christian_term', '금요 기도회', '금요기도회', '띄어쓰기', 100),
('christian_term', '새벽 기도', '새벽기도', '띄어쓰기', 100),
('christian_term', '성경 공부', '성경공부', '띄어쓰기', 100),
('christian_term', 'QT', 'QT', '매일 묵상', 100),
('christian_term', '큐티', 'QT', 'QT 한글 발음', 100),

-- 집단/파벌
('christian_term', '바리새인', '바리새인', '유대 종파', 100),
('christian_term', '바리새 인', '바리새인', '띄어쓰기 오류', 100),
('christian_term', '사두개인', '사두개인', '유대 종파', 100),
('christian_term', '사두개 인', '사두개인', '띄어쓰기 오류', 100),
('christian_term', '서기관', '서기관', '율법 학자', 100),
('christian_term', '레위인', '레위인', '제사장 지파', 100),
('christian_term', '이방인', '이방인', '비유대인', 100)
ON CONFLICT (original) DO UPDATE SET
    replacement = EXCLUDED.replacement,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ================================================
-- PART 5: 일반 오인식 패턴 (공통)
-- ================================================

INSERT INTO global_dictionary (category, original, replacement, description, priority) VALUES
-- 띄어쓰기 오류
('common', '할 수 있다', '할 수 있다', '띄어쓰기 정상', 100),
('common', '할수있다', '할 수 있다', '띄어쓰기 오류', 100),
('common', '할 수있다', '할 수 있다', '띄어쓰기 오류', 100),
('common', '있는 것', '있는 것', '띄어쓰기 정상', 100),
('common', '있는것', '있는 것', '띄어쓰기 오류', 100),
('common', '하는 것', '하는 것', '띄어쓰기 정상', 100),
('common', '하는것', '하는 것', '띄어쓰기 오류', 100),
('common', '되는 것', '되는 것', '띄어쓰기 정상', 100),
('common', '되는것', '되는 것', '띄어쓰기 오류', 100),

-- 음성 인식 오류 패턴
('common', '그래갖고', '그래 가지고', '구어체 오인식', 80),
('common', '근데', '그런데', '구어체 축약', 80),
('common', '걍', '그냥', '구어체 축약', 80),
('common', '어케', '어떻게', '구어체 축약', 80),
('common', '뭔가', '뭔가', '뭔가 정상', 100),
('common', '왠지', '왠지', '왠지 정상 (이유)', 100),
('common', '웬지', '왠지', '왠지 오인식', 100),
('common', '안돼', '안 돼', '띄어쓰기 오류', 100),
('common', '안 되', '안 돼', '맞춤법 오류', 100),
('common', '됬다', '됐다', '맞춤법 오류', 100),
('common', '됬어요', '됐어요', '맞춤법 오류', 100)
ON CONFLICT (original) DO UPDATE SET
    replacement = EXCLUDED.replacement,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ================================================
-- PART 6: 검증 쿼리
-- ================================================

SELECT
    category,
    COUNT(*) as count
FROM global_dictionary
WHERE is_active = true
GROUP BY category
ORDER BY count DESC;

-- 전체 개수
SELECT 'global_dictionary' as table_name, COUNT(*) as total FROM global_dictionary;
