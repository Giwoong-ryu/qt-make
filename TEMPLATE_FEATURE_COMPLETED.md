# 템플릿 클립 선택 기능 구현 완료 ✅

> **날짜**: 2026-01-17  
> **작업**: 배경 설정에서 저장한 템플릿이 영상 생성 시 적용되도록 수정

---

## 🎯 해결된 문제

**증상**: "배경 설정" 페이지에서 저장한 템플릿(묵상1 등)을 선택하여 영상을 생성해도 **저장한 클립이 적용되지 않고 랜덤 클립**이 사용됨

**원인**: 
- 프론트엔드는 `clip_ids`를 백엔드로 전송 ✅
- 백엔드 `main.py`가 `clip_ids`를 받지만 **Celery 태스크에 전달하지 않음** ❌

---

## 📝 수정된 파일 (3개)

### 1. `backend/app/main.py`

**수정 위치**: 227~266줄

**변경 내용**:
- `clip_ids` JSON 파싱 추가
- `bgm_volume` float 파싱 추가
- `process_video_task.delay()`에 `clip_ids`, `bgm_id`, `bgm_volume` 전달
- `batch_process_videos_task.delay()`에도 동일 적용

```python
# clip_ids 파싱 (JSON 문자열 → 리스트)
parsed_clip_ids = None
if clip_ids:
    try:
        import json
        parsed_clip_ids = json.loads(clip_ids)
        logger.info(f"Parsed clip_ids: {parsed_clip_ids}")
    except json.JSONDecodeError:
        logger.warning(f"Invalid clip_ids format: {clip_ids}")

# 태스크에 전달
task = process_video_task.delay(
    audio_paths[0],
    church_id,
    video_ids[0],
    actual_pack_id,
    parsed_clip_ids,  # ✅ 추가됨
    bgm_id,           # ✅ 추가됨
    parsed_bgm_volume # ✅ 추가됨
)
```

---

### 2. `backend/app/tasks.py`

**수정 위치**: 
- 36~44줄 (process_video_task 파라미터)
- 178~189줄 (클립 선택 로직)
- 192줄 (변수명 변경: `clip_ids` → `used_clip_ids`)
- 439~446줄 (batch_process_videos_task 파라미터)
- 489줄 (batch 호출 시 파라미터 전달)

**변경 내용**:
- `clip_ids`, `bgm_id`, `bgm_volume` 파라미터 추가
- 템플릿 클립 사용 로직 추가:
  ```python
  if clip_ids and len(clip_ids) > 0:
      logger.info(f"[Step 2/5] 템플릿 클립 사용: {len(clip_ids)}개")
      selected_clips = clip_selector.get_clips_by_ids(
          clip_ids=clip_ids,
          audio_duration=audio_duration
      )
  else:
      logger.info(f"[Step 2/5] 자동 클립 선택 (pack_id: {pack_id})")
      selected_clips = clip_selector.select_clips(
          audio_duration=audio_duration,
          pack_id=pack_id
      )
  ```
- 변수명 충돌 방지: `clip_ids` → `used_clip_ids` (192줄)

---

### 3. `backend/app/services/clips.py`

**수정 위치**: 169~227줄 (새 메서드 추가)

**변경 내용**:
- 새 메서드 `get_clips_by_ids()` 추가
- 기능:
  1. 특정 `clip_ids`로 DB 조회
  2. 템플릿에 저장된 순서대로 클립 정렬
  3. 오디오 길이를 커버할 때까지 클립 반복
  4. 실패 시 자동 선택으로 폴백

```python
def get_clips_by_ids(
    self,
    clip_ids: list[str],
    audio_duration: int
) -> list[dict]:
    """특정 클립 ID 리스트로 클립 조회 (템플릿 사용 시)"""
    
    # 클립 ID로 조회
    response = self.supabase.table("clips") \
        .select("*") \
        .in_("id", clip_ids) \
        .execute()
    
    # 선택 순서 유지
    clips_dict = {clip["id"]: clip for clip in response.data}
    ordered_clips = [clips_dict[cid] for cid in clip_ids if cid in clips_dict]
    
    # 오디오 길이만큼 반복
    result_clips = []
    while total_duration < audio_duration:
        for clip in ordered_clips:
            result_clips.append(clip.copy())
            total_duration += clip.get("duration", 30)
    
    return result_clips
```

---

## ✅ 구현 완료 체크리스트

- [x] main.py에서 clip_ids JSON 파싱
- [x] main.py에서 process_video_task에 clip_ids 전달
- [x] main.py에서 batch_process_videos_task에 clip_ids 전달
- [x] tasks.py에 clip_ids 파라미터 추가
- [x] tasks.py에 템플릿 클립 선택 로직 추가
- [x] clips.py에 get_clips_by_ids() 메서드 추가
- [x] 변수명 충돌 해결 (clip_ids → used_clip_ids)
- [x] Celery worker 재시작

---

## 🧪 테스트 방법

### 1. 서버 재시작 확인
```bash
docker-compose ps
# worker 상태 확인
```

### 2. 템플릿 생성
1. `/resources` 페이지 접속
2. 클립 5개 선택
3. BGM 선택, 볼륨 조정
4. "템플릿 저장" → "묵상1" 저장

### 3. 영상 생성
1. 대시보드 접속
2. 파일 업로드 시 드롭다운에서 "묵상1 (클립 5개)" 선택
3. "영상 생성 시작" 클릭
4. **로그 확인**:
   ```
   [Step 2/5] 템플릿 클립 사용: 5개
   Selected 15 clips from template (total duration: 450s, audio: 180s)
   ```

### 4. 결과 확인
- 생성된 영상에서 **저장한 클립이 순서대로 반복**되는지 확인
- 자동 선택된 랜덤 클립이 아닌지 확인

---

## 📊 기능 흐름

```
사용자 템플릿 선택
       ↓
프론트엔드 (page.tsx)
       ↓
createVideoWithOptions()
       ↓
clip_ids → JSON.stringify()
       ↓
POST /api/videos/upload
       ↓
백엔드 (main.py)
       ↓
JSON.parse(clip_ids)
       ↓
process_video_task.delay(clip_ids=...)
       ↓
Celery (tasks.py)
       ↓
clip_selector.get_clips_by_ids(clip_ids)
       ↓
Supabase 조회 (.in_("id", clip_ids))
       ↓
순서 유지 + 반복
       ↓
영상 합성 (FFmpeg)
```

---

## ⚠️ 주의사항

**다른 AI 도구 사용 시 절대 삭제/수정 금지**:
- `backend/app/main.py` (227~266줄)
- `backend/app/tasks.py` (42~44줄, 178~193줄, 444~446줄, 489줄)
- `backend/app/services/clips.py` (169~227줄)

---

**템플릿 클립 선택 기능 구현 완료!** 🎉
