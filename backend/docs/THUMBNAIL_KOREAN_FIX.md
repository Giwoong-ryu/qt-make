# FFmpeg 한글 썸네일 문제 분석 및 해결 기록

> 작성일: 2026-01-18
> 문제 해결 소요 시간: 약 2시간 (불필요하게 길었음)

---

## 1. 문제 현상

- FFmpeg `drawtext` 필터에서 한글 텍스트가 렌더링되지 않음
- 에러 메시지: `Error parsing a filter description`
- 썸네일 생성 실패 → 영상에 인트로 없이 생성됨

---

## 2. 근본 원인 (Root Cause)

### 실제 원인: 2가지 문제가 복합적으로 발생

| 문제 | 원인 | 해결 |
|------|------|------|
| **1. Windows 경로 형식** | FFmpeg는 `C:\path`를 인식 못함 | `\` → `/` 변환 |
| **2. 폰트 파일 누락** | 프론트엔드 폰트(Google Fonts)가 백엔드에 없음 | 폰트 다운로드 + 매핑 |

### 왜 헷갈렸나?

1. **에러 메시지가 모호함**: `Error parsing a filter description`만 나오고 구체적 원인 불명
2. **두 가지 문제가 동시에 존재**: 경로 문제 해결해도 폰트 문제가 남아있어서 "여전히 안 됨"
3. **이전에 작동했던 기억**: "자간 수정 후 작동했다"는 정보에 집착 → 코드 변경점 추적에 시간 낭비

---

## 3. 시도한 접근들 (시간순)

### 3.1 잘못된 접근들

| 시도 | 왜 잘못됨 | 소요 시간 |
|------|----------|----------|
| 콜론 이스케이프 (`\:`) 추가 | FFmpeg가 `C\:/path` 형식 인식 못함 | 30분 |
| `subprocess` text=True/False 변경 | 근본 원인과 무관 | 20분 |
| git 히스토리 추적 | 파일이 git에 없었음 | 15분 |
| 백슬래시만 변환 | 이것만으로는 부족 (폰트 문제 남음) | 15분 |

### 3.2 올바른 접근

1. **경로 문제 해결**: `path.replace("\\", "/")` (콜론은 그대로)
2. **폰트 문제 해결**: Google Fonts 다운로드 → `FONT_MAPPING` 추가

---

## 4. 최종 해결 코드

### 4.1 경로 변환 (Windows → FFmpeg)

```python
def ffmpeg_path(path: str) -> str:
    # 백슬래시만 변환 (콜론은 드라이브 문자이므로 그대로)
    return path.replace("\\", "/")
```

**결과**: `C:\Users\...\file.txt` → `C:/Users/.../file.txt`

### 4.2 폰트 매핑

```python
FONT_MAPPING = {
    "Do Hyeon": "DoHyeon-Regular.ttf",
    "Hahmlet": "NotoSansKR-Regular.ttf",  # 대체
    "Noto Sans KR": "NotoSansKR-Regular.ttf",
    # ...
}

def _get_font_path_for_family(font_family: str | None) -> str:
    if font_family and font_family in FONT_MAPPING:
        font_file = FONTS_DIR / FONT_MAPPING[font_family]
        if font_file.exists():
            return str(font_file).replace("\\", "/")
    # 폴백: 기본 폰트 또는 시스템 폰트
```

### 4.3 텍스트박스별 폰트 적용

```python
for box in text_boxes:
    box_font_family = box.get("fontFamily")
    box_font_path = _get_font_path_for_family(box_font_family)
    # 각 텍스트박스에 개별 폰트 적용
```

---

## 5. 왜 헤맸는가? (자기 반성)

### 5.1 문제 분리 실패

- 경로 문제와 폰트 문제를 별개로 인식하지 못함
- 하나 고치고 "여전히 안 됨" → 이전 수정이 잘못됐다고 판단 → 롤백 → 무한 루프

### 5.2 가설 검증 부족

- "콜론 이스케이프가 필요하다"는 가설을 검증 없이 적용
- FFmpeg 공식 문서 확인 안 함

### 5.3 사용자 정보 해석 오류

- "자간 수정 후 작동했다" → 자간 코드에 집착
- 실제로는 그 시점에 우연히 폰트/경로가 맞았던 것

---

## 6. 다음에 안 헤매려면?

### 6.1 문제 분리 원칙

```
문제 발생
  ↓
[단계 1] 로그에서 정확한 에러 메시지 확인
  ↓
[단계 2] 가능한 원인 목록 작성 (최소 3개)
  ↓
[단계 3] 각 원인을 독립적으로 테스트
  ↓
[단계 4] 한 번에 하나씩만 수정 → 테스트 → 기록
```

### 6.2 FFmpeg Windows 경로 규칙 (기억해둘 것)

| 경로 형식 | FFmpeg 인식 | 비고 |
|-----------|------------|------|
| `C:\path\file` | X | 백슬래시 불가 |
| `C:/path/file` | O | 포워드슬래시 OK |
| `C\:/path/file` | X | 콜론 이스케이프 불필요 |
| `/c/path/file` | O | MSYS/Git Bash 형식 |

### 6.3 폰트 문제 체크리스트

```
[ ] 프론트엔드에서 사용하는 폰트 목록 확인
[ ] 백엔드에 해당 폰트 파일이 있는지 확인
[ ] 폰트 경로가 FFmpeg에 전달되는지 로그 확인
[ ] 폰트 파일이 실제로 존재하는지 확인
```

### 6.4 디버깅 순서

1. **최소 재현 케이스 만들기**: 복잡한 워크플로우 대신 단독 FFmpeg 명령 테스트
2. **로그 강화**: 실제 실행되는 FFmpeg 명령어 전체 출력
3. **단계별 검증**: 경로 변환 → 폰트 확인 → 텍스트 인코딩 → 필터 구문

---

## 7. 파일 구조

```
backend/app/
├── fonts/                      # 폰트 파일 디렉토리 (신규)
│   ├── DoHyeon-Regular.ttf    # 도현 폰트
│   └── NotoSansKR-Regular.ttf # Noto Sans KR (기본, Hahmlet 대체)
│
└── services/
    └── thumbnail.py           # 폰트 매핑 로직 추가
```

---

## 8. 관련 커밋

- 폰트 매핑 추가: `FONT_MAPPING` 딕셔너리
- 텍스트박스별 폰트: `_get_font_path_for_family()` 함수
- 경로 변환: `ffmpeg_path()` 함수 (콜론 이스케이프 제거)

---

## 9. 테스트 방법

```bash
# Celery 워커 재시작
# (코드 변경 후 반드시 필요)

# 프론트엔드에서 썸네일 생성 테스트
# - Do Hyeon 폰트 선택 → 한글 입력 → 생성
# - Hahmlet 폰트 선택 → Noto Sans로 대체되어 생성
```

---

## 10. 핵심 교훈

> **"작동했던 시점"에 집착하지 말고, 현재 상태에서 원인을 분리하여 검증하라.**

1. 문제가 여러 개일 수 있다 (경로 + 폰트)
2. 하나씩 고치고 테스트하라
3. 가설을 세우면 반드시 검증하라
4. FFmpeg 경로는 포워드슬래시, 콜론 그대로
