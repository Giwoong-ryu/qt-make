# 얼굴 및 동물 필터링 시스템 문서

## 📋 목차
1. [문제 배경](#문제-배경)
2. [해결 방안](#해결-방안)
3. [필터링 정책](#필터링-정책)
4. [구현 내역](#구현-내역)
5. [테스트 결과](#테스트-결과)
6. [향후 운영 가이드](#향후-운영-가이드)

---

## 문제 배경

### 초기 문제 (2026-01-21)
- 영상 생성 시 사람 얼굴이 포함된 클립이 계속 나타남
- 특히 **Pexels ID 8719740** (수녀 기도 영상)이 반복 출현
- Gemini Vision API의 얼굴 감지 프롬프트로만 필터링하는 한계 발견

### 문제 클립 분석

**Pexels ID 8719740: "A nun praying inside the church"**
- 썸네일 URL: `https://images.pexels.com/videos/8719740/adult-art-bead-bible-8719740.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=630&w=1200`
- 비디오 페이지: https://www.pexels.com/video/8719740/
- **문제점**: Gemini Vision이 "hooded figure with face completely hidden" 예외 조항으로 오인식
- **실제**: 수녀의 얼굴이 베일 아래로 명확히 보임

### 테스트 결과
- 강화된 프롬프트로 여러 차례 테스트했으나 **계속 ACCEPT 반환**
- 프롬프트 추가 내용:
  - `⚠️ CRITICAL: ANY PERSON IN CENTER OF FRAME = AUTOMATIC REJECT`
  - `Religious figures: nun, priest, monk with ANY face visible`
  - 명시적 reject 예시: `Nun/priest with face visible under veil/habit ❌`

**결론**: Gemini Vision 프롬프트만으로는 100% 필터링 불가능

---

## 해결 방안

### 2단계 방어 시스템 구축

#### 1단계: Gemini Vision 필터링 (1차 방어)
- 대부분의 부적절한 클립 사전 차단
- 비용 효율적 (API 호출 1회로 검증)

#### 2단계: 블랙리스트 시스템 (2차 방어)
- Gemini Vision이 놓친 False Positive 수동 차단
- 영구 블랙리스트 DB 테이블 관리
- **목적**: AI 한계를 사람이 보완

### 시스템 흐름도

```
[Pexels API 클립 검색]
         ↓
[Gemini Vision 필터링] ← 1차 방어 (자동)
    ACCEPT ↓ REJECT → 버림
         ↓
[블랙리스트 확인]     ← 2차 방어 (수동)
    포함 X ↓ 포함 O → 버림
         ↓
[클립 사용]
```

---

## 필터링 정책

### 사람 얼굴 필터링 (엄격)

#### ❌ REJECT (차단)
- **정면/측면 얼굴** (눈, 코, 입이 보이는 경우)
- **중앙 프레임의 사람** (포즈, 앉기, 무릎 꿇기)
- **클로즈업/미디엄샷** (얼굴 디테일 보임)
- **종교인** (수녀, 신부, 수도자 - 얼굴 보이는 경우)
- **스튜디오 촬영** (회색 배경, 인터뷰 스타일)

#### ✅ ACCEPT (허용)
- **완전한 실루엣** (검은 그림자만, 얼굴 디테일 없음)
- **뒷모습** (얼굴이 카메라 반대편)
- **후드 인물** (얼굴이 완전히 그림자에 숨음)
- **극단적 롱샷** (사람이 프레임의 2% 미만)
- **심한 블러** (얼굴 인식 불가능)

### 동물 필터링 (조건부) - 2026-01-21 정책 협의

#### 배경
- 초기에는 동물 전체 차단 시도
- 사용자 피드백: "성경은 사람/감정이 메인인데 사람도 빼고 동물도 빼면 찾을 영상이 없을 것"
- 협의 결과: **상징적 동물은 허용, 부적절한 동물만 차단**

#### ❌ REJECT (차단)
- **애완동물 클로즈업** (강아지, 고양이 얼굴)
- **귀여운 동물 영상** (유튜브 스타일, 엔터테인먼트)
- **징그러운 생물** (곤충, 파충류, 크롤링 생물)
- **부자연스러운 환경** (애완동물 쇼, 서커스)

#### ✅ ACCEPT (허용 - 성경 상징)
- **양떼/어린양** (들판 배경, 먼 거리)
- **비둘기/독수리** (새가 날아가는 모습, 먼 거리)
- **물고기** (수중 촬영, 상징적 의미)
- **야생동물** (자연 서식지, 와이드샷)

**핵심**: 성경 콘텐츠에 자주 등장하는 상징적 동물(양, 비둘기, 독수리)은 명상에 도움이 되므로 허용

### 기타 필터링

#### ❌ REJECT
- **노출/선정적 콘텐츠** (수영복, 드러난 어깨, 패션 포즈)
- **상업적 콘텐츠** (제품 홍보, 로고, 브랜드)
- **차량** (자동차, 오토바이 운전 장면)
- **부적절한 콘텐츠** (폭력, 무기, 술, 담배, 클럽)

#### ✅ ACCEPT
- **자연 풍경** (산, 바다, 숲, 하늘, 구름, 일몰)
- **건축물** (교회, 대성당, 고대 건물 - 사람 없음)
- **오브제** (촛불, 십자가, 책, 컵과 일몰)
- **빛 효과** (햇살, 골든 아워, 렌즈 플레어)
- **추상적** (물결, 파도, 아트 블러, 흑백)

---

## 구현 내역

### 1. Gemini Vision 프롬프트 강화

**파일**: `backend/app/services/background_video_search.py`

**변경 내역** (2026-01-21):

```python
# Lines 461-520: Gemini Vision Prompt

prompt = """<task>
Classify this video thumbnail for meditation/prayer/spiritual content.
This is for a Christian prayer/meditation app. Be EXTREMELY STRICT about human faces.
Output only: ACCEPT or REJECT
</task>

<reject_criteria>
REJECT if ANY of the following is present:

1. HUMAN FACES (HIGHEST PRIORITY - ALWAYS REJECT):

   ⚠️ CRITICAL: ANY PERSON IN CENTER OF FRAME = AUTOMATIC REJECT
   Even if religious figure (nun, priest, monk) = REJECT

   - ANY face looking at camera (front view, 3/4 view, side view)
   - Eyes, nose, or mouth visible (even partially)
   - Face clearly identifiable (even without smile)
   - Person posing or sitting in center of frame
   - Person kneeling/praying in center of frame
   - Close-up or medium shot showing face details
   - Studio portrait style (gray background, centered person)
   - Interview/vlog/presentation setup
   - Religious figures: nun, priest, monk with ANY face visible

   EXCEPTION (ONLY these are acceptable):
   - Complete silhouette (black shadow only, no face details)
   - Back of head only (facing away from camera, no face visible)
   - Hooded figure with face COMPLETELY HIDDEN IN SHADOW (if ANY face part visible = REJECT)
   - Extreme long shot where person is tiny dot (< 2% of frame)
   - Heavy intentional blur (no features recognizable)

2. REVEALING/SUGGESTIVE CONTENT:
   - Low-cut tops, cleavage, revealing necklines
   - Tight/form-fitting clothing emphasizing body
   - Swimwear, bikini, lingerie, underwear
   - Bare shoulders, midriff, exposed skin
   - Fashion model poses (hand on hip, looking over shoulder)
   - Glamour/beauty shots, studio fashion photography
   - Seductive or alluring expressions
   - Entertainment industry footage (music videos, fashion shows)

3. Product/commercial content:
   - Hand holding light bulb, unboxing, brand logos, advertisements

4. Vehicles:
   - Cars, motorcycles, driving scenes

5. Animals (selective):
   ⚠️ REJECT ONLY:
   - Pet animals: dogs, cats (especially close-ups)
   - Cute animal videos (YouTube pet style)
   - Insects, reptiles, creepy creatures
   - Animals in unnatural/entertainment settings

   ✅ ACCEPT (Biblical/nature symbols):
   - Sheep, lamb flock (in distance/background)
   - Doves, eagles (birds in flight, distant)
   - Fish (underwater, symbolic)
   - Wildlife in natural habitat (wide shots)

6. Other inappropriate:
   - Violence, weapons, blood
   - Alcohol, smoking, drugs
   - Nightclub, bar, party scenes
</reject_criteria>

<accept_examples>
- Nature ONLY: mountains, ocean, forest, sky, clouds, sunset, fog, rain, waterfalls
- Architecture: church, cathedral, ancient buildings, throne rooms (no people)
- Objects: coffee cup with sunset, candles, religious symbols, books
- Text graphics: "Forgiveness", spiritual messages on nature background
- Light effects: sun rays, golden hour, lens flare
- Artistic blur, soft focus, black and white, dreamy atmosphere
- Complete silhouettes: person as black shadow against bright background
- Back view: person walking away, back of head visible only
- Hooded figures: face completely hidden in shadow
- Praying hands ONLY (no face visible at all)
- Biblical animals: sheep flock in field, doves flying, eagles soaring (distant)
</accept_examples>

<reject_examples>
- Woman sitting facing camera (even with neutral expression) ❌
- Man looking at camera from any angle ❌
- Person in center of frame with face visible ❌
- Studio portrait with gray background ❌
- Close-up of person's face (even if serious) ❌
- Person in tight clothing ❌
- Fashion/modeling poses ❌
- Hand holding product ❌
- Car driving ❌
- Beach scenes with swimwear ❌
- Nun/priest with face visible under veil/habit ❌
- Religious person praying with face visible ❌
- Person in church with face looking at camera ❌
- Pet dogs/cats (especially close-ups) ❌
- Cute animal videos (YouTube style) ❌
- Insects, reptiles, creepy creatures ❌
</reject_examples>

CRITICAL RULE: If you can see a person's face clearly (eyes, nose, mouth), ALWAYS REJECT.
This is for meditation content - faces distract from contemplation.

Output:"""
```

### 2. 블랙리스트 시스템 구축

#### 2.1. Supabase 테이블 생성

**파일**: `backend/create_blacklist_clips_table.sql`

```sql
-- 얼굴 포함 클립 영구 블랙리스트 테이블
-- Gemini Vision이 ACCEPT했지만 실제로 얼굴이 있는 클립 차단

CREATE TABLE IF NOT EXISTS blacklist_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id INTEGER NOT NULL UNIQUE,  -- Pexels video ID
    reason TEXT NOT NULL,              -- 차단 이유 (예: "nun face visible")
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스: clip_id 기준 빠른 조회
CREATE INDEX IF NOT EXISTS idx_blacklist_clips_id
ON blacklist_clips(clip_id);

COMMENT ON TABLE blacklist_clips IS '얼굴 포함 클립 영구 블랙리스트 (Gemini Vision 우회용)';
COMMENT ON COLUMN blacklist_clips.clip_id IS 'Pexels video ID (integer) - 영구 차단';
COMMENT ON COLUMN blacklist_clips.reason IS '차단 이유 (디버깅용)';

-- 초기 블랙리스트 추가
INSERT INTO blacklist_clips (clip_id, reason)
VALUES
    (8719740, 'nun with face visible (Gemini Vision false positive)')
ON CONFLICT (clip_id) DO NOTHING;
```

#### 2.2. ClipHistoryService 수정

**파일**: `backend/app/services/clip_history.py`

**변경 내역** (Lines 17-85):

```python
def get_recently_used_clips(self, church_id: str, limit: int = 10) -> Set[int]:
    """
    최근 N개 영상에서 사용된 클립 ID + 영구 블랙리스트 클립 가져오기

    Args:
        church_id: 교회 ID
        limit: 최근 영상 개수 (기본 10개)

    Returns:
        최근 사용된 clip_id + 블랙리스트 clip_id (Pexels video ID) Set
    """
    try:
        sb = get_supabase()

        # 1. 최근 N개 영상 ID 가져오기
        recent_videos = (
            sb.table("videos")
            .select("id")
            .eq("church_id", church_id)
            .eq("status", "completed")  # 완료된 영상만
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        if not recent_videos.data:
            logger.info(f"[ClipHistory] No recent videos for church {church_id[:8]}")
            video_ids = []
        else:
            video_ids = [v["id"] for v in recent_videos.data]

        # 2. 해당 영상들에서 사용된 클립 ID 조회
        if video_ids:
            used_clips = (
                sb.table("used_clips")
                .select("clip_id")
                .in_("video_id", video_ids)
                .execute()
            )
            clip_ids = {clip["clip_id"] for clip in used_clips.data}
        else:
            clip_ids = set()

        # 3. 영구 블랙리스트 클립 추가 (얼굴 포함 클립)
        blacklist = (
            sb.table("blacklist_clips")
            .select("clip_id")
            .execute()
        )

        if blacklist.data:
            blacklist_ids = {clip["clip_id"] for clip in blacklist.data}
            clip_ids.update(blacklist_ids)

            logger.info(
                f"[ClipHistory] Added {len(blacklist_ids)} blacklisted clips"
            )

        logger.info(
            f"[ClipHistory] Found {len(clip_ids)} clips to filter "
            f"(recent: {len(clip_ids) - len(blacklist_ids) if blacklist.data else len(clip_ids)}, "
            f"blacklist: {len(blacklist_ids) if blacklist.data else 0})"
        )

        return clip_ids

    except Exception as e:
        logger.exception(f"[ClipHistory] Failed to fetch recent clips: {e}")
        return set()  # 실패 시 빈 set 반환 (중복 방지 실패하더라도 영상 생성은 계속)
```

**핵심 변경점**:
- 기존: 최근 10개 영상에서 사용된 클립만 필터링
- 변경: 최근 사용 클립 + **블랙리스트 클립** 모두 필터링

### 3. 테스트 스크립트 작성

#### 3.1. 문제 클립 테스트

**파일**: `backend/test_clip_8719740.py`

```python
"""
Pexels ID 8719740 클립을 Gemini Vision으로 테스트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import google.generativeai as genai
import requests

# Gemini API 설정 (GOOGLE_API_KEY 또는 GEMINI_API_KEY 사용)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

def test_clip_classification():
    """Pexels ID 8719740의 썸네일을 Gemini Vision으로 분류"""

    # Pexels 클립 ID
    clip_id = 8719740

    # Pexels 썸네일 URL (실제 Pexels API가 반환하는 형식)
    thumbnail_url = f"https://images.pexels.com/videos/{clip_id}/adult-art-bead-bible-{clip_id}.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=630&w=1200"

    print(f"[테스트 클립]")
    print(f"  Pexels ID: {clip_id}")
    print(f"  Thumbnail URL: {thumbnail_url}")
    print(f"  Video Page: https://www.pexels.com/video/{clip_id}/")
    print()

    # Gemini Vision Prompt (background_video_search.py와 동일)
    prompt = """... (생략) ..."""

    # Gemini 2.5 Flash 모델 사용 (background_video_search.py와 동일)
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("[Gemini Vision 분류 시작...]")
    try:
        # 1. 썸네일 다운로드
        print(f"  썸네일 다운로드 중...")
        img_response = requests.get(thumbnail_url, timeout=10)
        img_response.raise_for_status()

        # 2. Gemini Vision 호출 (바이너리 데이터로 전달)
        print(f"  Gemini Vision 분석 중...")
        response = model.generate_content([
            {
                "mime_type": "image/jpeg",
                "data": img_response.content
            },
            prompt
        ])

        result = response.text.strip().upper()
        print(f"\n[결과] {result}")

        if "REJECT" in result:
            print("  → ❌ REJECT (얼굴 또는 부적절한 콘텐츠 감지)")
        elif "ACCEPT" in result:
            print("  → ✅ ACCEPT (명상/기도 콘텐츠로 분류됨)")
        else:
            print(f"  → ⚠️ 예상치 못한 응답: {result}")

    except Exception as e:
        print(f"\n[에러] {e}")

if __name__ == "__main__":
    test_clip_classification()
```

**실행 결과**: 강화된 프롬프트에도 불구하고 계속 ACCEPT 반환 → 블랙리스트 필요성 입증

#### 3.2. 블랙리스트 검증

**파일**: `backend/verify_blacklist.py`

```python
"""
블랙리스트 시스템 동작 확인
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.clip_history import get_clip_history_service

def main():
    service = get_clip_history_service()

    # 테스트용 church_id (실제 데이터 있는 교회 ID 사용)
    church_id = "test_church"

    print("[블랙리스트 시스템 검증]")
    print(f"  Church ID: {church_id}")
    print()

    # 최근 사용된 클립 + 블랙리스트 가져오기
    filtered_clips = service.get_recently_used_clips(church_id, limit=10)

    print(f"[필터링 대상 클립]")
    print(f"  총 {len(filtered_clips)}개 클립이 필터링됩니다.")
    print()

    # 8719740이 포함되어 있는지 확인
    if 8719740 in filtered_clips:
        print("✅ Pexels ID 8719740 (수녀님 얼굴) → 블랙리스트에 포함됨")
        print("   → 향후 영상 생성 시 자동으로 제외됩니다!")
    else:
        print("❌ Pexels ID 8719740이 블랙리스트에 없습니다.")
        print("   → Supabase SQL 실행을 확인하세요.")

    print()
    print(f"[필터링 목록] (최대 20개만 표시)")
    for idx, clip_id in enumerate(sorted(filtered_clips)[:20], 1):
        marker = " ← 블랙리스트" if clip_id == 8719740 else ""
        print(f"  {idx}. Pexels ID: {clip_id}{marker}")

if __name__ == "__main__":
    main()
```

**실행 결과**: Pexels ID 8719740이 블랙리스트에 정상 포함 확인

### 4. Worker 재시작

```bash
# Worker 컨테이너 재시작 (변경사항 적용)
cd c:\Users\user\Desktop\gpt\n8n-make\kmong_work\qt-make\qt-video-saas
docker compose restart worker

# 재시작 확인
docker compose logs worker --tail=30
```

**재시작 시각**:
- 1차 재시작: 2026-01-21 13:20:37 (04:20:37 UTC) - 얼굴 필터 강화
- 2차 재시작: 2026-01-21 13:54:12 (04:54:12 UTC) - 동물 전체 차단
- 3차 재시작: 2026-01-21 13:59:21 (04:59:21 UTC) - 동물 조건부 허용 (최종)

---

## 테스트 결과

### 1. Gemini Vision 프롬프트 강화 테스트

| 테스트 | Pexels ID | 설명 | Gemini Vision 결과 | 기대 결과 | 일치 여부 |
|--------|-----------|------|-------------------|-----------|-----------|
| 1 | 8719740 | 수녀 기도 (얼굴 보임) | ACCEPT | REJECT | ❌ |
| 2 | 8719740 | 프롬프트 강화 후 재테스트 | ACCEPT | REJECT | ❌ |
| 3 | 8719740 | "CRITICAL" 문구 추가 후 | ACCEPT | REJECT | ❌ |

**결론**: Gemini Vision의 분류 한계 확인 → 블랙리스트 시스템 필요

### 2. 블랙리스트 시스템 테스트

| 테스트 | 동작 | 결과 |
|--------|------|------|
| Supabase 테이블 생성 | `create_blacklist_clips_table.sql` 실행 | ✅ 성공 |
| 초기 데이터 삽입 | Pexels ID 8719740 추가 | ✅ 성공 |
| ClipHistoryService 통합 | `get_recently_used_clips()` 수정 | ✅ 성공 |
| 블랙리스트 조회 | `verify_blacklist.py` 실행 | ✅ 8719740 포함 확인 |
| Worker 로그 확인 | `[ClipHistory] Added 1 blacklisted clips` | ✅ 정상 작동 |

### 3. 실제 영상 생성 테스트

| 영상 생성 시각 | Worker 재시작 | Pexels ID 8719740 출현 | 결과 |
|---------------|--------------|----------------------|------|
| 2026-01-21 13:21 | 13:20:37 이후 | ❌ 차단됨 | ✅ 성공 |
| 2026-01-21 13:24-13:28 | 13:20:37 이후 | ❌ 차단됨 | ✅ 성공 |

**결론**: 블랙리스트 시스템이 정상 작동하여 문제 클립 차단 확인

---

## 향후 운영 가이드

### 1. 새로운 문제 클립 발견 시

#### Step 1: Pexels ID 확인
- 프론트엔드에서 영상의 클립 정보 확인
- 또는 Supabase `used_clips` 테이블에서 `clip_id` 조회

```sql
-- 특정 영상에서 사용된 클립 조회
SELECT clip_id, clip_url
FROM used_clips
WHERE video_id = '영상ID'
ORDER BY created_at;
```

#### Step 2: 블랙리스트 추가
```sql
-- Supabase Dashboard → SQL Editor
INSERT INTO blacklist_clips (clip_id, reason)
VALUES
    (클립ID, '차단 이유 설명')
ON CONFLICT (clip_id) DO NOTHING;
```

**예시**:
```sql
INSERT INTO blacklist_clips (clip_id, reason)
VALUES
    (1234567, 'person face visible in prayer scene'),
    (7654321, 'close-up of dog face (distracting)')
ON CONFLICT (clip_id) DO NOTHING;
```

#### Step 3: 블랙리스트 확인
```python
python backend/verify_blacklist.py
```

또는 SQL로 직접 확인:
```sql
SELECT clip_id, reason, added_at
FROM blacklist_clips
ORDER BY added_at DESC;
```

#### Step 4: Worker 재시작 불필요
- 블랙리스트는 매 영상 생성 시 실시간 조회
- Worker 재시작 없이 즉시 적용됨

### 2. 블랙리스트 관리

#### 블랙리스트 전체 조회
```sql
SELECT
    clip_id,
    reason,
    added_at,
    'https://www.pexels.com/video/' || clip_id || '/' AS video_url
FROM blacklist_clips
ORDER BY added_at DESC;
```

#### 블랙리스트에서 제거 (실수로 추가한 경우)
```sql
-- 특정 클립 제거
DELETE FROM blacklist_clips
WHERE clip_id = 클립ID;

-- 여러 클립 제거
DELETE FROM blacklist_clips
WHERE clip_id IN (클립ID1, 클립ID2, 클립ID3);
```

#### 블랙리스트 통계
```sql
-- 전체 블랙리스트 개수
SELECT COUNT(*) AS total_blacklisted
FROM blacklist_clips;

-- 최근 30일 추가된 블랙리스트
SELECT COUNT(*) AS recent_blacklisted
FROM blacklist_clips
WHERE added_at >= NOW() - INTERVAL '30 days';
```

### 3. Gemini Vision 프롬프트 수정

#### 언제 수정하는가?
- 특정 유형의 클립이 **반복적으로** 블랙리스트에 추가될 때
- 예: 특정 포즈/상황이 5회 이상 발견되면 프롬프트 추가 고려

#### 수정 방법

**파일**: `backend/app/services/background_video_search.py`

1. `<reject_criteria>` 섹션에 새 규칙 추가
2. `<reject_examples>` 섹션에 예시 추가
3. Worker 재시작:
   ```bash
   cd c:\Users\user\Desktop\gpt\n8n-make\kmong_work\qt-make\qt-video-saas
   docker compose restart worker
   ```

#### 예시: 손 클로즈업 차단
```python
# reject_criteria에 추가
7. Body parts close-up:
   - Close-up of hands (prayer hands OK if no face)
   - Feet, legs in focus
   - Body parts as main focus

# reject_examples에 추가
- Hands close-up (praying hands with face visible) ❌
```

### 4. 동물 필터링 정책 변경

현재 정책은 사용자와 협의하여 **조건부 허용**으로 설정되었습니다.

#### 정책 변경이 필요한 경우

**시나리오 1**: 양떼/비둘기도 불편하다는 피드백
```python
# 동물 전체 차단으로 변경
5. Animals:
   - ALL animals (dogs, cats, birds, wildlife)
   - Close-ups of animals
   - Animals as main focus of frame
```

**시나리오 2**: 특정 동물만 추가 차단
```python
# 예: 소/말 추가 차단
5. Animals (selective):
   ⚠️ REJECT ONLY:
   - Pet animals: dogs, cats (especially close-ups)
   - Farm animals: cows, horses (close-ups)  # 추가
   - Cute animal videos (YouTube pet style)
   ...
```

### 5. 모니터링 및 로그 확인

#### Worker 로그 확인
```bash
# 실시간 로그
docker compose logs worker -f

# 최근 30줄
docker compose logs worker --tail=30

# 블랙리스트 관련 로그만 필터링
docker compose logs worker | grep "blacklist"
```

#### 주요 로그 메시지
```
[ClipHistory] Added {N} blacklisted clips
[ClipHistory] Found {N} clips to filter (recent: {M}, blacklist: {K})
```

- `N`: 필터링 대상 총 클립 수
- `M`: 최근 10개 영상에서 사용된 클립 수
- `K`: 블랙리스트 클립 수

### 6. 블랙리스트 백업

#### 백업 생성
```sql
-- Supabase Dashboard → SQL Editor
COPY blacklist_clips TO '/path/to/backup/blacklist_backup_20260121.csv'
WITH (FORMAT CSV, HEADER);
```

또는 Python 스크립트:
```python
import csv
from app.database import get_supabase

sb = get_supabase()
result = sb.table("blacklist_clips").select("*").execute()

with open('blacklist_backup.csv', 'w', newline='') as f:
    if result.data:
        writer = csv.DictWriter(f, fieldnames=result.data[0].keys())
        writer.writeheader()
        writer.writerows(result.data)
```

#### 백업 복원
```sql
-- CSV 파일에서 복원
COPY blacklist_clips (clip_id, reason, added_at)
FROM '/path/to/backup/blacklist_backup_20260121.csv'
WITH (FORMAT CSV, HEADER);
```

---

## 부록

### A. 관련 파일 목록

| 파일 | 경로 | 용도 |
|------|------|------|
| Gemini Vision 프롬프트 | `backend/app/services/background_video_search.py` | 1차 필터링 (자동) |
| ClipHistoryService | `backend/app/services/clip_history.py` | 블랙리스트 통합 |
| 블랙리스트 테이블 스키마 | `backend/create_blacklist_clips_table.sql` | Supabase 테이블 생성 |
| 블랙리스트 초기화 | `backend/create_blacklist_table.py` | 테이블 생성 + 초기 데이터 |
| 문제 클립 테스트 | `backend/test_clip_8719740.py` | Gemini Vision 테스트 |
| 블랙리스트 검증 | `backend/verify_blacklist.py` | 블랙리스트 시스템 확인 |

### B. Pexels 썸네일 URL 형식

```
https://images.pexels.com/videos/{clip_id}/[단어]-{clip_id}.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=630&w=1200
```

**예시**:
- Pexels ID 8719740: `https://images.pexels.com/videos/8719740/adult-art-bead-bible-8719740.jpeg?...`

**주의**: 단어 부분(`adult-art-bead-bible`)은 클립마다 다르므로, 실제 Pexels API 응답에서 확인 필요

### C. Gemini Vision 모델 정보

| 항목 | 값 |
|------|-----|
| 모델명 | `gemini-2.5-flash` |
| API 키 환경변수 | `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` |
| 입력 형식 | JPEG 이미지 (바이너리) |
| 출력 형식 | `ACCEPT` 또는 `REJECT` (텍스트) |
| 비용 | Input: $0.075/1M tokens<br>Output: $0.30/1M tokens |

**참고**: 이미지 1장 = 약 258 tokens (1080p 기준)

### D. Supabase 테이블 스키마

#### `used_clips` 테이블
```sql
CREATE TABLE used_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    church_id TEXT NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    clip_id INTEGER NOT NULL,  -- Pexels video ID
    clip_url TEXT,             -- 클립 다운로드 URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(video_id, clip_id)
);
```

#### `blacklist_clips` 테이블
```sql
CREATE TABLE blacklist_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id INTEGER NOT NULL UNIQUE,  -- Pexels video ID
    reason TEXT NOT NULL,              -- 차단 이유
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### E. 문제 해결 가이드

#### Q1. 블랙리스트에 추가했는데도 클립이 나타남

**체크리스트**:
1. Supabase에 실제로 추가되었는지 확인:
   ```sql
   SELECT * FROM blacklist_clips WHERE clip_id = 문제클립ID;
   ```
2. Worker 로그 확인:
   ```bash
   docker compose logs worker | grep "blacklist"
   ```
3. 문제 클립이 최근 10개 영상 범위 밖이면 → 괜찮음 (중복 방지 범위 외)

#### Q2. Gemini Vision이 너무 많은 클립을 차단함

**원인**: 프롬프트가 너무 엄격
**해결**:
1. `<reject_criteria>` 섹션에서 조건 완화
2. `<accept_examples>` 섹션에 허용 예시 추가
3. Worker 재시작

#### Q3. 동물 필터링 정책을 다시 바꾸고 싶음

**방법**:
1. `background_video_search.py` 파일 수정 (5. Animals 섹션)
2. Worker 재시작:
   ```bash
   docker compose restart worker
   ```

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 담당자 |
|------|------|-----------|--------|
| 2026-01-21 | 1.0 | 초기 문서 작성 | Claude |
| 2026-01-21 | 1.1 | 동물 필터링 정책 협의 및 반영 | Claude + User |
| 2026-01-21 | 1.2 | 조건부 동물 허용 정책 최종 확정 | Claude + User |

---

## 참고 링크

- Pexels API 문서: https://www.pexels.com/api/documentation/
- Gemini Vision API: https://ai.google.dev/gemini-api/docs/vision
- Supabase 문서: https://supabase.com/docs
- 문제 클립 비디오 페이지: https://www.pexels.com/video/8719740/

---

**문서 작성**: Claude Sonnet 4.5
**최종 업데이트**: 2026-01-21 14:00 KST
