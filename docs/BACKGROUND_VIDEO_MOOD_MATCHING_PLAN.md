# 배경 영상 감정 매칭 시스템 구현 계획서 (Pillar v4.0 Stage 2)

> **작성일**: 2026-01-19
> **상태**: 계획 단계 (자막 버그 수정 후 진행 예정)
> **우선순위**: Medium (자막 시스템 안정화 후)

---

## 📊 현황 분석

### 기존 시스템 구조

| 항목 | 현재 상태 | 파일 위치 |
|------|----------|-----------|
| 배경 클립 선택 | ✅ 카테고리 기반 다양성 선택 | `backend/app/services/clips.py:30-101` |
| 자막 생성 | ✅ Whisper → SRT 변환 | `backend/app/services/stt.py:114-167` |
| 자막 분석 | ❌ 없음 (분위기 무관 랜덤) | - |
| Gemini 통합 | ✅ STT Correction 서비스 | `backend/app/services/stt_correction.py` |
| Pexels API | ❌ 없음 | - |

### 통합 지점

```python
# backend/app/tasks.py:166-205
# 현재: pack-free에서 랜덤 선택
# 개선: 자막 감정 분석 → Pexels 검색 → 기존 클립 혼합
```

---

## 🎯 MVP 구현 범위 (Phase 1 - 2-3시간)

### 핵심 기능

1. **자막 감정 분석**: Gemini 2.5 Flash-Lite로 6차원 분석
   - emotion: joy, peace, hope, reverence, sorrow, contemplation, determination
   - subject: nature, abstract, light, water, sky, earth
   - motion: static, slow, medium, dynamic
   - intensity: subtle, moderate, strong
   - color_tone: warm, cool, neutral, golden

2. **Pexels 검색**: 무료 API (200 requests/hour)
   - 3단계 우선순위 쿼리 (Runway AI Prompt Engineering)
   - Priority 1: subject + emotion + color_tone
   - Priority 2: subject + motion
   - Priority 3: subject only

3. **혼합 전략**: Pexels 50% + 기존 DB 클립 50%

4. **안전 필터**: Gemini Vision으로 썸네일 검증 (표정 기반 필터링)

   **📖 QT/명상 콘텐츠의 본질:**
   - 인간의 **문제** (고통/좌절/결핍) → 하나님의 **해결책**
   - 행복/기쁨은 **결과**이지 과정이 아님
   - 공감 가능한 고통의 순간 → 자막/말씀으로 위로

   **핵심 통찰: 인간 = 고통 표현의 유일한 매개체**
   - ✅ 평화/안정감 → 자연 영상으로 대체 가능 (산, 바다, 하늘)
   - ❌ 고통/결핍/절망 → **인간 없이는 표현 불가능**
   - → 따라서 표정 숨긴 인간 영상이 필수

   **핵심 철학: 표정을 숨긴다 = 더 강렬한 감정 표현**
   - 후드로 가림 → 고립감, 은폐하고 싶은 고통
   - 고개 숙임 → 수치심, 회개, 겸손
   - 뒷모습 → 소외감, 고독, "나도 이랬었어"
   - 실루엣 → 보편적 인간 조건
   - 엎드림/무릎 꿇음 → 절망, 간구, 탄원

   **필터링 기준:**
   - ✅ 허용: 표정이 보이지 않는 인간 (뒷모습, 실루엣, 후드, 고개 숙임, 신체 표현)
   - ❌ 차단: 얼굴 표정이 명확히 보임 (클로즈업, 웃는 얼굴, 대화)
   - ❌ 차단: 자동차, 기계류, 부적절 콘텐츠

   **Why?**
   - 웃는 얼굴 = 피상적, 광고 같음 (자연으로 대체 가능)
   - 고통의 신체 언어 = 대체 불가능 (인간만이 표현 가능)
   - QT는 진짜 고통에서 시작하므로 **표정 숨긴 인간이 필수**

---

## 📁 신규 파일 구조

```
backend/app/services/
├── mood_analyzer.py              # 신규 - 자막 감정 6차원 분석
├── background_video_search.py    # 신규 - Pexels API 검색
└── clips.py                      # 기존 - 그대로 유지

backend/app/tasks.py              # 수정 - lines 166-205 통합

.env                              # 수정 - PEXELS_API_KEY 추가
```

---

## 🔧 기술 설계

### 1. MoodAnalyzer (mood_analyzer.py)

**입력**: SRT 파일 경로
**출력**: 세그먼트별 감정 데이터

```python
[
    {
        "start": 0.0,
        "end": 3.5,
        "text": "오늘 우리가 함께 묵상할...",
        "mood": {
            "emotion": "peace",
            "subject": "light",
            "motion": "slow",
            "intensity": "subtle",
            "color_tone": "warm"
        }
    }
]
```

**Gemini API 호출**:
- Model: gemini-2.5-flash-lite
- Temperature: 0.1 (일관성 중시)
- 배치 처리: 5개씩 묶어서 API 호출 최소화
- 비용: ~$0.0015/영상 (30 segments × $0.00005)

---

### 2. PexelsVideoSearch (background_video_search.py)

**입력**: mood 딕셔너리, duration_needed
**출력**: 검증된 안전 영상 리스트 (품질 점수 포함)

```python
[
    {
        "id": 12345,
        "file_path": "https://...",
        "duration": 15,
        "quality_score": 85,  # 0-100점
        "vision_verified": True  # Gemini Vision 검증 완료
    }
]
```

**검색 및 검증 프로세스**:
1. Pexels API로 후보 영상 20개 검색
2. 각 후보의 썸네일을 Gemini Vision으로 검증
3. 검증 통과한 영상 중 품질 점수 상위 5개 반환

**Gemini Vision 검증 기준 (표정 기반)**:
- ❌ 차단: 사람의 얼굴 표정이 명확하게 보임 (표정 식별 가능)
- ❌ 차단: 사람 얼굴이 화면 중앙에 크게 보임 (클로즈업)
- ✅ 허용: 사람은 있지만 표정이 보이지 않음 (뒷모습, 실루엣, 후드, 고개 숙임)
- ✅ 허용: 풍경/자연/건축물 메인, 사람 손발만 보임
- ❌ 차단: 자동차, 오토바이, 기계류
- ❌ 차단: 부적절한 콘텐츠

**품질 점수 계산 (0-100점)**:
- 검색 우선순위: 40점 (Priority 1=40, 2=25, 3=10)
- 해상도: 20점 (1920x1080=20)
- 영상 길이: 20점 (15-30초=20)
- Gemini Vision 안전성: 20점 (검증 통과=20)

---

### 3. tasks.py 통합 (빈도 기반 감정 분석)

```python
# line 166 이후 추가

from app.services.emotion_frequency_analyzer import get_emotion_analyzer
from app.services.background_video_search import get_video_search

# 1. 자막 텍스트 추출 (SRT → 텍스트 리스트)
with open(srt_path, 'r', encoding='utf-8') as f:
    srt_content = f.read()

# SRT 파싱하여 자막 텍스트만 추출
subtitle_texts = []
for block in srt_content.split('\n\n'):
    lines = block.strip().split('\n')
    if len(lines) >= 3:
        # 3번째 줄부터가 자막 텍스트
        text = ' '.join(lines[2:])
        subtitle_texts.append(text)

# 2. 빈도 기반 감정 분석
analyzer = get_emotion_analyzer()
frequency = analyzer.analyze(subtitle_texts)

# 로깅: 분석 결과 출력
logger.info(
    f"Emotion Frequency Analysis: "
    f"pain={frequency.pain_count}({frequency.pain_ratio:.1f}%), "
    f"hope={frequency.hope_count}({frequency.hope_ratio:.1f}%), "
    f"total={frequency.total_words}"
)

# 3. 영상 전략 결정
strategy = analyzer.get_video_strategy(frequency)
logger.info(f"Video Strategy: {strategy}")

# 4. 전략별 Pexels 검색
video_search = get_video_search()
pexels_videos = video_search.search_by_mood(
    mood=None,  # strategy 사용 시 mood는 무시됨
    duration_needed=int(audio_duration * 0.5),
    max_results=3,
    strategy=strategy  # "human" / "nature_bright" / "nature_calm"
)

# 5. DB 클립 선택 (나머지 50%)
db_clips = clip_selector.select_clips(
    audio_duration - sum(v.duration for v in pexels_videos),
    pack_id
)

# 6. 혼합 + 랜덤 셔플
all_clips = pexels_videos + db_clips
random.shuffle(all_clips)
```

**핵심 변경사항**:
- MoodAnalyzer 대신 EmotionFrequencyAnalyzer 사용
- 자막 텍스트에서 고통/희망 단어 빈도 측정
- 임계값 비교로 자동 전략 결정 (human/nature_bright/nature_calm)
- 전략별 키워드로 Pexels 검색

---

## 📊 예상 비용

| 항목 | 단가 | 3분 영상 | 월 100개 |
|------|------|---------|---------|
| Gemini 2.5 Flash-Lite (자막 분석) | $0.00005/segment | $0.0015 | $0.15 |
| Gemini Vision (썸네일 검증 20개) | $0.00025/image | $0.005 | $0.50 |
| Pexels API | 무료 | $0 | $0 |
| **합계** | - | **$0.0065** | **$0.65** |

**기존 대비**: +0.65% (무시 가능)
**ROI**: 부적절 영상 차단으로 사용자 신뢰도 확보 (필수 투자)

---

## ✅ 검증 기준

- **감정 정확도**: 70% 이상 (10개 샘플 중 7개 만족)
- **안전성**: 사람/자동차 출현 0%
- **API 성공률**: 95% 이상

---

## 🚀 Phase 2 확장 계획 (선택사항)

| 기능 | 예상 시간 | 효과 | 상태 |
|------|----------|------|------|
| ~~Gemini Vision 검증~~ | ~~1일~~ | ~~사람/자동차 필터링 100%~~ | ✅ **MVP 포함** |
| 세그먼트별 영상 매칭 | 2일 | 자막 변화 따라 영상 전환 | 미정 |
| 커스텀 팩 자동 생성 | 3일 | 교회별 Pexels 팩 | 미정 |
| 사용자 피드백 루프 | 1주 | 학습 기반 품질 향상 | 미정 |

---

## 📝 다음 단계

### 완료된 작업 (2026-01-20)
1. ✅ **빈도 기반 감정 분석 시스템 구현**
   - `emotion_frequency_analyzer.py` 생성
   - 고통 키워드 25개, 희망 키워드 16개
   - 임계값 설정: 고통 5%, 희망 3%
   - 3가지 전략: human / nature_bright / nature_calm

2. ✅ **전략별 Pexels 검색 키워드 추가**
   - `background_video_search.py`에 STRATEGY_KEYWORDS 추가
   - 각 전략별 primary 키워드 4개 + fallback 1개
   - strategy 파라미터로 검색 쿼리 자동 전환

3. ✅ **Gemini Vision 필터링 규칙 정리**
   - 표정 가시성 기준으로 단순화
   - 얼굴 표정 보임 = REJECT
   - 신체 표현만 있음 = ACCEPT (후드, 뒷모습, 기도 자세 등)

4. ✅ **타입 에러 수정 (2026-01-20 완료)**
   - `mood: Optional[MoodData]` 타입 변경
   - 로깅 에러 수정 (mood=None 시 대응)
   - mood=None 폴백 처리 추가
   - 타입 체커 에러 0개

### 남은 작업
1. ⏳ **자막 버그 수정** (우선) - celery worker 충돌 해결
2. ⏳ **tasks.py 통합** - 빈도 분석 시스템 연결
3. ⏳ **테스트 및 검증**
   - 실제 QT 자막으로 빈도 분석 테스트
   - 임계값 조정 (5%/3% 적정성 검증)
   - Pexels 검색 품질 확인

---

## 🔗 참고 문서

- [자막 드래그 위치 조정 기능](./SUBTITLE_DRAG_POSITION_FEATURE.md)
- [한국어 자막 분할 가이드](./KOREAN_SUBTITLE_SEGMENTATION_GUIDE.md)
- Prompt-A-Video (Dec 2024)
- VPO: Unlocking Full-Body Video Keypoint Estimation (2025)
- VidProM Dataset (1.67M prompts)
