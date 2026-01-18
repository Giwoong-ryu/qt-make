# 자막 드래그 위치 조정 기능 (고급 기능)

> **상태**: 기획 단계 (미구현)
> **우선순위**: Low (고급 기능)
> **예상 구현 시간**: 1-2시간

---

## 기능 개요

사용자가 영상 편집 시 자막 위치를 마우스 드래그로 실시간 조정할 수 있는 기능

**사용자 시나리오:**
1. 영상 편집 모달에서 영상 미리보기
2. 자막 미리보기 박스를 마우스로 드래그
3. 원하는 위치로 이동 (수직 방향만)
4. "영상 재생성" 시 조정된 위치로 자막 생성

---

## 구현 방식: 프론트엔드 미리보기 (추천)

### 장점
- 실시간 미리보기 가능
- 사용자 경험 좋음 (썸네일 편집기와 동일한 UX)
- 구현 빠름

### 단점
- 미리보기 스타일과 실제 영상 자막이 약간 다를 수 있음 (폰트 렌더링 차이)

---

## 기술 구현 계획

### 1. 프론트엔드 (`VideoEditModal.tsx`)

#### 1.1 상태 관리
```typescript
// 자막 위치 상태 (margin_bottom 값)
const [subtitleMarginBottom, setSubtitleMarginBottom] = useState(150);
const [isDraggingSubtitle, setIsDraggingSubtitle] = useState(false);
```

#### 1.2 드래그 가능한 자막 미리보기
```tsx
{/* 영상 플레이어 위에 오버레이 */}
<div className="relative">
  <video ref={videoRef} />

  {/* 드래그 가능한 자막 미리보기 */}
  <div
    className="absolute left-0 right-0 pointer-events-auto cursor-move"
    style={{
      bottom: `${subtitleMarginBottom}px`,
    }}
    onMouseDown={handleSubtitleDragStart}
  >
    <div className="bg-black/70 text-white text-center py-2 px-4 rounded-lg mx-auto max-w-fit">
      <p className="font-noto text-2xl">자막 미리보기 예시</p>
      <p className="text-xs text-gray-300 mt-1">드래그하여 위치 조정</p>
    </div>
  </div>
</div>
```

#### 1.3 드래그 핸들러
```typescript
const handleSubtitleDragStart = (e: React.MouseEvent) => {
  e.preventDefault();
  setIsDraggingSubtitle(true);

  const videoRect = videoRef.current?.getBoundingClientRect();
  if (!videoRect) return;

  const handleMouseMove = (moveEvent: MouseEvent) => {
    const relativeY = videoRect.bottom - moveEvent.clientY;
    // 50px ~ 500px 범위로 제한
    const clampedY = Math.max(50, Math.min(500, relativeY));
    setSubtitleMarginBottom(clampedY);
  };

  const handleMouseUp = () => {
    setIsDraggingSubtitle(false);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};
```

#### 1.4 영상 재생성 시 전송
```typescript
const handleRegenerate = async () => {
  await regenerateVideo(videoId, {
    title: editedTitle,
    intro_text: editedIntro,
    intro_settings: localIntroSettings,
    canvas_image_data: canvasImageData,
    subtitle_margin_bottom: subtitleMarginBottom,  // ← 추가
  });
};
```

---

### 2. 백엔드 (`app/api/routes/videos.py`)

#### 2.1 API 파라미터 추가
```python
class RegenerateVideoRequest(BaseModel):
    title: str | None = None
    intro_text: str | None = None
    intro_settings: dict | None = None
    canvas_image_data: str | None = None
    subtitle_margin_bottom: int | None = None  # ← 추가
```

#### 2.2 Celery Task 전달
```python
@router.post("/{video_id}/regenerate")
async def regenerate_video(
    video_id: str,
    request: RegenerateVideoRequest,
    # ...
):
    # ...
    celery_app.send_task(
        "app.tasks.regenerate_video_task",
        args=[
            video_id,
            church_id,
            request.title,
            request.intro_text,
            request.intro_settings,
            request.canvas_image_data,
            request.subtitle_margin_bottom,  # ← 추가
        ]
    )
```

---

### 3. 백엔드 (`app/tasks.py`)

#### 3.1 Task 파라미터 추가
```python
@celery_app.task(name="app.tasks.regenerate_video_task")
def regenerate_video_task(
    video_id: str,
    church_id: str,
    title: str | None = None,
    intro_text: str | None = None,
    intro_settings: dict | None = None,
    canvas_image_data: str | None = None,
    subtitle_margin_bottom: int | None = None,  # ← 추가
):
    # ...
```

#### 3.2 영상 합성 시 전달
```python
# SubtitleStyle 생성 시 사용자 설정 반영
style = SubtitleStyle(
    font_path=str(font_path),
    font_size=96,
    outline_width=6,
    margin_bottom=subtitle_margin_bottom or 150,  # ← 사용자 값 또는 기본값
    video_width=1920,
    video_height=1080
)
```

---

### 4. 백엔드 (`app/services/video.py`)

#### 4.1 `_add_subtitles_pil()` 수정
```python
def _add_subtitles_pil(
    self,
    video_path: str,
    srt_path: str,
    output_path: str,
    subtitle_margin_bottom: int | None = None  # ← 추가
) -> None:
    # ...
    style = SubtitleStyle(
        font_path=str(font_path) if font_path.exists() else "",
        font_size=96,
        outline_width=6,
        margin_bottom=subtitle_margin_bottom or 150,  # ← 적용
        video_width=self.OUTPUT_WIDTH,
        video_height=self.OUTPUT_HEIGHT
    )
```

---

## UI/UX 개선 사항

### 1. 미리보기 실제 자막 표시
- 현재: 고정된 "자막 미리보기 예시" 텍스트
- 개선: SRT 파일에서 첫 번째 자막 텍스트 읽어서 표시
- 구현: `useEffect`로 SRT 파일 fetch → 파싱 → 첫 줄 추출

### 2. 위치 가이드라인
```tsx
{/* 위치 가이드 (10%, 20%, 30% 등) */}
<div className="absolute left-0 right-0 pointer-events-none">
  {[10, 20, 30, 40, 50].map(percent => (
    <div
      key={percent}
      className="border-t border-dashed border-gray-500/30"
      style={{ bottom: `${percent}%` }}
    />
  ))}
</div>
```

### 3. 위치 수치 표시
```tsx
{/* 현재 위치 표시 */}
<div className="absolute top-2 right-2 bg-black/80 text-white px-2 py-1 rounded text-xs">
  자막 위치: {subtitleMarginBottom}px (하단에서 {(subtitleMarginBottom / 1080 * 100).toFixed(1)}%)
</div>
```

### 4. 리셋 버튼
```tsx
<button
  onClick={() => setSubtitleMarginBottom(150)}
  className="text-xs text-gray-400 hover:text-white"
>
  기본값으로 리셋
</button>
```

---

## 대안: 슬라이더 방식 (더 간단)

드래그 대신 슬라이더로 위치 조정하는 방식도 고려 가능:

```tsx
<div className="flex items-center gap-4">
  <label className="text-sm font-medium">자막 위치</label>
  <input
    type="range"
    min="50"
    max="500"
    step="10"
    value={subtitleMarginBottom}
    onChange={(e) => setSubtitleMarginBottom(Number(e.target.value))}
    className="flex-1"
  />
  <span className="text-sm text-gray-400">{subtitleMarginBottom}px</span>
</div>
```

**장점:**
- 구현 더 간단
- 정확한 픽셀 값 조정 가능
- 모바일에서도 사용 편리

**단점:**
- 직관성이 드래그보다 떨어짐

---

## 구현 우선순위

1. **Phase 1 (필수)**: 슬라이더 방식 구현
   - 구현 시간: 30분
   - 사용자 경험: 충분히 좋음

2. **Phase 2 (선택)**: 드래그 방식 추가
   - 구현 시간: 1시간
   - 사용자 경험: 더 직관적

3. **Phase 3 (고급)**: 실제 자막 미리보기 + 가이드라인
   - 구현 시간: 30분
   - SRT 파싱 + UI 가이드

---

## 참고 사항

### 현재 기본값
- `margin_bottom`: 150px (화면 하단에서 약 14% 위치)
- `video_height`: 1080px

### 권장 범위
- 최소: 50px (화면 맨 아래)
- 최대: 500px (화면 중앙에 가까움)
- 기본: 150px

### 스타일 일관성
- 썸네일 편집기와 동일한 드래그 UX 적용
- 커서: `cursor-move`
- 드래그 중: 약간 투명하게 (`opacity-80`)

---

## 구현 시 주의사항

1. **영상 비율 대응**
   - 현재: 1920x1080 고정
   - 향후: 다른 해상도 대응 시 퍼센트 기반으로 변환 필요

2. **실제 자막과 미리보기 차이**
   - 미리보기: HTML/CSS 렌더링
   - 실제 영상: PIL 렌더링
   - 폰트, 크기, 외곽선이 완전히 동일하지 않을 수 있음

3. **성능**
   - 드래그 중 과도한 re-render 방지
   - `throttle` 또는 `debounce` 적용 고려

---

## 테스트 시나리오

1. 슬라이더로 위치 조정 → 영상 재생성 → 자막 위치 확인
2. 드래그로 위치 조정 → 영상 재생성 → 자막 위치 확인
3. 극단값 테스트 (50px, 500px)
4. 기본값 리셋 테스트
5. 영상 재생 중 미리보기 위치와 실제 자막 위치 비교

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `frontend/src/components/VideoEditModal.tsx` | 드래그/슬라이더 UI |
| `backend/app/api/routes/videos.py` | API 파라미터 추가 |
| `backend/app/tasks.py` | Celery Task 전달 |
| `backend/app/services/video.py` | SubtitleStyle 적용 |
| `backend/app/services/subtitle_renderer.py` | margin_bottom 사용 |

---

## 마무리

이 기능은 **고급 기능**으로 분류되며, 기본 기능 완료 후 사용자 피드백을 받아 구현 여부를 결정하는 것이 좋습니다.

**구현 권장 타이밍:**
- 기본 영상 생성 기능 안정화 후
- 사용자가 자막 위치 조정 요청 시
- v2.0 업데이트 시
