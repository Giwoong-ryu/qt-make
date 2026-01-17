-- 자동 치환 사전 테이블
-- 자막 수정 시 자동으로 저장되어 같은 교회의 다음 STT에 적용됨

CREATE TABLE IF NOT EXISTS replacement_dictionary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id UUID NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    original TEXT NOT NULL,           -- 원본 텍스트 (STT 결과)
    replacement TEXT NOT NULL,        -- 치환 텍스트 (사용자 수정)
    use_count INTEGER DEFAULT 1,      -- 사용 횟수 (자주 쓰일수록 높음)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 같은 교회에서 같은 원본 텍스트는 하나만 존재
    UNIQUE(church_id, original)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_replacement_dictionary_church_id
    ON replacement_dictionary(church_id);

CREATE INDEX IF NOT EXISTS idx_replacement_dictionary_original
    ON replacement_dictionary(church_id, original);

CREATE INDEX IF NOT EXISTS idx_replacement_dictionary_use_count
    ON replacement_dictionary(church_id, use_count DESC);

-- RLS (Row Level Security) 정책
ALTER TABLE replacement_dictionary ENABLE ROW LEVEL SECURITY;

-- 정책: 자신의 교회 데이터만 조회/수정 가능
CREATE POLICY "Users can view own church dictionary"
    ON replacement_dictionary FOR SELECT
    USING (
        church_id IN (
            SELECT church_id FROM user_profiles
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own church dictionary"
    ON replacement_dictionary FOR INSERT
    WITH CHECK (
        church_id IN (
            SELECT church_id FROM user_profiles
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can update own church dictionary"
    ON replacement_dictionary FOR UPDATE
    USING (
        church_id IN (
            SELECT church_id FROM user_profiles
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own church dictionary"
    ON replacement_dictionary FOR DELETE
    USING (
        church_id IN (
            SELECT church_id FROM user_profiles
            WHERE id = auth.uid()
        )
    );

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_replacement_dictionary_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_replacement_dictionary_updated_at
    BEFORE UPDATE ON replacement_dictionary
    FOR EACH ROW
    EXECUTE FUNCTION update_replacement_dictionary_updated_at();

-- 주석
COMMENT ON TABLE replacement_dictionary IS '교회별 자동 치환 사전 - 자막 수정 시 자동 저장되어 STT 후처리에 적용';
COMMENT ON COLUMN replacement_dictionary.original IS 'STT가 잘못 인식한 원본 텍스트';
COMMENT ON COLUMN replacement_dictionary.replacement IS '사용자가 수정한 올바른 텍스트';
COMMENT ON COLUMN replacement_dictionary.use_count IS '해당 치환이 적용된 횟수 (자주 사용되는 항목 우선 표시용)';
