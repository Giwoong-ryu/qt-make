-- STT 교정 시스템 스키마
-- 실행: Supabase Dashboard > SQL Editor

-- ============================================
-- 1. church_dictionary (교회별 사전)
-- ============================================
CREATE TABLE IF NOT EXISTS church_dictionary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    wrong_text TEXT NOT NULL,           -- 잘못 인식되는 텍스트
    correct_text TEXT NOT NULL,         -- 올바른 텍스트
    category TEXT DEFAULT 'general',    -- 분류: person, place, bible, hymn, general
    frequency INT DEFAULT 1,            -- 사용 빈도 (자동 증가)
    is_active BOOLEAN DEFAULT TRUE,     -- 활성화 여부
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(church_id, wrong_text)       -- 교회별 중복 방지
);

-- 인덱스
CREATE INDEX idx_church_dictionary_church_id ON church_dictionary(church_id);
CREATE INDEX idx_church_dictionary_wrong_text ON church_dictionary(wrong_text);
CREATE INDEX idx_church_dictionary_frequency ON church_dictionary(frequency DESC);
CREATE INDEX idx_church_dictionary_category ON church_dictionary(category);

-- 업데이트 트리거
CREATE TRIGGER church_dictionary_updated_at
    BEFORE UPDATE ON church_dictionary
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

COMMENT ON TABLE church_dictionary IS '교회별 STT 교정 사전';
COMMENT ON COLUMN church_dictionary.wrong_text IS 'Whisper가 잘못 인식하는 텍스트';
COMMENT ON COLUMN church_dictionary.correct_text IS '올바른 텍스트';
COMMENT ON COLUMN church_dictionary.category IS '분류: person(인명), place(지명), bible(성경용어), hymn(찬양), general(일반)';


-- ============================================
-- 2. correction_history (교정 이력)
-- ============================================
CREATE TABLE IF NOT EXISTS correction_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    church_id UUID NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,        -- 원본 텍스트 (Whisper 결과)
    corrected_text TEXT NOT NULL,       -- 교정된 텍스트
    correction_source TEXT NOT NULL DEFAULT 'ai',  -- 'ai', 'user', 'dictionary'
    subtitle_index INT,                 -- 자막 인덱스 (SRT 순서)
    timestamp_start FLOAT,              -- 자막 시작 시간 (초)
    timestamp_end FLOAT,                -- 자막 끝 시간 (초)
    confidence FLOAT,                   -- AI 교정 신뢰도 (0-1)
    applied_to_dictionary BOOLEAN DEFAULT FALSE,  -- 사전에 반영 여부
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_correction_history_video_id ON correction_history(video_id);
CREATE INDEX idx_correction_history_church_id ON correction_history(church_id);
CREATE INDEX idx_correction_history_source ON correction_history(correction_source);
CREATE INDEX idx_correction_history_created_at ON correction_history(created_at DESC);

COMMENT ON TABLE correction_history IS 'STT 교정 이력 (AI/사용자 교정 기록)';
COMMENT ON COLUMN correction_history.correction_source IS '교정 출처: ai(AI 자동), user(사용자 수정), dictionary(사전 적용)';


-- ============================================
-- 3. church_stt_settings (교회별 STT 설정)
-- ============================================
CREATE TABLE IF NOT EXISTS church_stt_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID NOT NULL REFERENCES churches(id) ON DELETE CASCADE UNIQUE,

    -- Whisper 설정
    whisper_prompt TEXT,                -- Whisper initial_prompt (최대 224토큰)
    whisper_language TEXT DEFAULT 'ko', -- 언어 코드

    -- AI 교정 설정
    correction_enabled BOOLEAN DEFAULT TRUE,   -- AI 교정 활성화
    quality_mode BOOLEAN DEFAULT FALSE,        -- TRUE: Gemini 3 Flash, FALSE: Gemini 2.5 Flash
    auto_learn BOOLEAN DEFAULT TRUE,           -- 자동 학습 (사용자 수정 → 사전 반영)
    min_confidence FLOAT DEFAULT 0.7,          -- 최소 신뢰도 (이하면 원본 유지)

    -- 프롬프트 설정
    correction_prompt_template TEXT,    -- 커스텀 교정 프롬프트 (NULL이면 기본값)
    context_words TEXT[],               -- 추가 컨텍스트 단어 (담임목사명, 교회명 등)

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 업데이트 트리거
CREATE TRIGGER church_stt_settings_updated_at
    BEFORE UPDATE ON church_stt_settings
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

COMMENT ON TABLE church_stt_settings IS '교회별 STT 및 AI 교정 설정';
COMMENT ON COLUMN church_stt_settings.whisper_prompt IS 'Whisper initial_prompt (도메인 특화 용어, 최대 224토큰)';
COMMENT ON COLUMN church_stt_settings.quality_mode IS 'TRUE: Gemini 3 Flash ($0.50), FALSE: Gemini 2.5 Flash ($0.15)';


-- ============================================
-- 4. 헬퍼 함수들
-- ============================================

-- 사전 빈도 증가 함수
CREATE OR REPLACE FUNCTION increment_dictionary_frequency(dict_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE church_dictionary
    SET frequency = frequency + 1, updated_at = NOW()
    WHERE id = dict_id;
END;
$$ LANGUAGE plpgsql;

-- 교회별 자주 사용되는 사전 항목 조회 (Whisper prompt 생성용)
CREATE OR REPLACE FUNCTION get_top_dictionary_terms(p_church_id UUID, p_limit INT DEFAULT 50)
RETURNS TABLE(correct_text TEXT, category TEXT, frequency INT) AS $$
BEGIN
    RETURN QUERY
    SELECT d.correct_text, d.category, d.frequency
    FROM church_dictionary d
    WHERE d.church_id = p_church_id
      AND d.is_active = TRUE
    ORDER BY d.frequency DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 사용자 교정 시 사전 자동 추가/업데이트
CREATE OR REPLACE FUNCTION auto_update_dictionary()
RETURNS TRIGGER AS $$
BEGIN
    -- 사용자 교정이고, 원본과 다른 경우만
    IF NEW.correction_source = 'user' AND NEW.original_text != NEW.corrected_text THEN
        -- 사전에 이미 있으면 빈도 증가, 없으면 추가
        INSERT INTO church_dictionary (church_id, wrong_text, correct_text, category, frequency)
        VALUES (NEW.church_id, NEW.original_text, NEW.corrected_text, 'general', 1)
        ON CONFLICT (church_id, wrong_text)
        DO UPDATE SET
            correct_text = EXCLUDED.correct_text,
            frequency = church_dictionary.frequency + 1,
            updated_at = NOW();

        -- 반영 플래그 업데이트
        NEW.applied_to_dictionary := TRUE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거: 사용자 교정 시 자동 사전 업데이트
CREATE TRIGGER correction_auto_dictionary
    BEFORE INSERT ON correction_history
    FOR EACH ROW EXECUTE FUNCTION auto_update_dictionary();


-- ============================================
-- 5. 기본 데이터 (테스트용)
-- ============================================

-- 테스트 교회에 기본 STT 설정 추가
INSERT INTO church_stt_settings (church_id, whisper_prompt, context_words)
SELECT
    id,
    '묵상, 말씀, 은혜, 성경, 하나님, 예수님, 성령, 기도, 찬양, 예배',
    ARRAY['테스트교회', '담임목사']
FROM churches
WHERE id = '00000000-0000-0000-0000-000000000001'
ON CONFLICT (church_id) DO NOTHING;

-- 기본 교회용어 사전 (모든 교회 공통으로 사용 가능한 템플릿)
-- 실제 운영 시 church_id를 특정 교회로 지정
