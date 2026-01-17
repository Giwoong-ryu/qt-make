# QT Video SaaS 작업 플랜

> 작성일: 2026-01-14
> 프로젝트: 교회 묵상 영상 자동화 SaaS
> 기술 스택: Next.js 16 + FastAPI + Celery + Supabase + R2

---

## 프로젝트 현황 분석

### 완료된 기능 (구현됨)
- [OK] 파일 업로드 (MP3, WAV, M4A) - 최대 7개
- [OK] Celery 비동기 작업 큐
- [OK] 작업 상태 Polling (PENDING → PROCESSING → SUCCESS/FAILURE)
- [OK] 영상 목록 조회/삭제
- [OK] 배경 클립/팩 조회
- [OK] BGM 조회
- [OK] 자막 조회/수정 (SRT)
- [OK] 썸네일 생성/업로드
- [OK] 영상 재생성 API 스텁 (TODO 표시)

### 미완성 기능 (코드에 TODO 또는 미구현)
1. **영상 재생성 로직** (line 626: `regenerate_video_task.delay()` TODO)
2. **파일 삭제 R2 연동** (line 302: `r2.delete_file()` TODO)
3. **배경 클립/BGM 선택 UI** (VideoOptionsForm 컴포넌트 필요)

### 타입 불일치 발견 (백엔드 ↔ 프론트)

| 항목 | 백엔드 (main.py) | 프론트엔드 (types/index.ts) | 문제 |
|------|-----------------|---------------------------|------|
| **PATCH /api/videos/{video_id}** | title, church_id를 Form으로 받음 (line 396-400) | types에는 VideoOptions 인터페이스만 (title 포함) | [MISMATCH] Form 방식 vs JSON body |
| **subtitle 업데이트** | PUT /api/videos/{video_id}/subtitles (line 459-501) | updateSubtitles() 정의됨 (api.ts:187-198) | [OK] |
| **regenerate API** | POST /api/videos/{video_id}/regenerate (line 606-629) | regenerateVideo() 정의됨 (api.ts:273-284) | [OK] 하지만 백엔드는 빈 task_id 반환 |

### patterns.json 관련 문제 발견

```
[file-extension-hardcode-srt]
증상: M4A 파일 업로드 시 SRT 파일 생성 실패
원인: stt.py에서 audio_path.replace('.mp3', '.srt')로 하드코딩
해결책: os.path.splitext(audio_path)[0] + '.srt' 사용
```

→ **백엔드 `app/services/stt.py` 파일 확인 필요!**

---

## 작업 플랜

### Phase 1: 패턴 검증 및 버그 수정 (최우선!)

#### Task 1.1: 확장자 하드코딩 문제 확인
- [ ] `app/services/stt.py` 읽기
- [ ] `.replace('.mp3', '.srt')` 패턴 검색
- [ ] `os.path.splitext()` 방식으로 수정
- [ ] M4A, WAV도 정상 작동 확인

#### Task 1.2: 백엔드 파일 형식 지원 검증
- [ ] `app/services/video.py` 읽기
- [ ] 파일 형식 관련 하드코딩 전수 검색
- [ ] FFmpeg 명령어에서 확장자 추측 부분 검토

#### Task 1.3: 보안 스캔
```bash
grep -rE "(AIzaSy|sk-|ghp_|gho_|api_key\s*=)" --include="*.py" --include="*.ts" .
```
- [ ] API 키 하드코딩 검증
- [ ] `.env` 파일 사용 확인

---

### Phase 2: 미완성 기능 완성

#### Task 2.1: 영상 재생성 로직 구현
**백엔드** (`app/main.py:606-629`, `app/tasks.py`):
- [ ] `regenerate_video_task` Celery 작업 생성
- [ ] 기존 `process_video_task` 코드 재사용 구조 검토
- [ ] 클립/BGM 커스터마이징 파라미터 전달 로직

**프론트엔드** (필요시):
- [ ] VideoEditModal에 재생성 버튼 추가
- [ ] 옵션 변경 후 재생성 플로우 구현

#### Task 2.2: R2 파일 삭제 연동
- [ ] `app/services/storage.py` 확인 (R2Storage 클래스)
- [ ] `delete_file()` 메서드 구현
- [ ] `main.py:302` TODO 주석 제거 후 연동

#### Task 2.3: VideoOptionsForm 컴포넌트 구현
**UI 요구사항**:
- [ ] 배경팩 선택 (ClipPack 목록)
- [ ] 클립 선택 (체크박스 또는 갤러리)
- [ ] BGM 선택 (드롭다운 + 미리듣기)
- [ ] BGM 볼륨 슬라이더 (0-1, 기본 0.12)
- [ ] 썸네일 생성 여부 토글

**API 연동**:
- [ ] `getClipPacks()` 호출
- [ ] `getClips(packId)` 호출
- [ ] `getBGMs()` 호출
- [ ] 선택된 값들을 VideoOptions로 전달

---

### Phase 3: 타입 불일치 수정

#### Task 3.1: PATCH /api/videos/{video_id} 타입 통일
**옵션 A (권장)**: Form → JSON body로 변경
```python
# main.py:395-426 수정
@app.patch("/api/videos/{video_id}")
async def update_video(
    video_id: str,
    update_data: dict,  # JSON body
    church_id: str = Query(...)
):
    # ...
```

**옵션 B**: 프론트엔드를 Form으로 변경
```typescript
// api.ts:164-175 수정
const formData = new FormData();
formData.append("title", title);
formData.append("church_id", churchId);
```

- [ ] 옵션 선택 후 수정
- [ ] 프론트엔드/백엔드 타입 일치 확인

---

### Phase 4: 추가 개선사항 (선택)

#### Task 4.1: 에러 처리 강화
- [ ] 프론트엔드 에러 토스트 UI 추가
- [ ] 백엔드 에러 로깅 구조화 (현재 logger 사용 중)

#### Task 4.2: 업로드 진행률 표시
- [ ] FormData 업로드 시 `onUploadProgress` 콜백 추가
- [ ] ProgressCard에 업로드 진행률 표시

#### Task 4.3: Celery 작업 실패 시 재시도 로직
- [ ] `tasks.py`에서 `@app.task(bind=True, max_retries=3)` 추가
- [ ] 실패 시 exponential backoff

#### Task 4.4: 썸네일 자동 생성
- [ ] 영상 생성 완료 후 자동으로 5초 지점 썸네일 추출
- [ ] `VideoOptions.generateThumbnail` 기본값 True 활용

---

## 우선순위 권장

### 높음 (즉시 작업)
1. **Task 1.1**: 확장자 하드코딩 버그 수정 (M4A 미지원 문제)
2. **Task 2.3**: VideoOptionsForm 구현 (사용자가 클립/BGM 선택 불가능)

### 중간 (다음 스프린트)
3. **Task 2.1**: 영상 재생성 로직 구현
4. **Task 3.1**: 타입 불일치 수정

### 낮음 (추후)
5. **Task 2.2**: R2 파일 삭제 (현재 DB에서만 삭제)
6. **Phase 4**: 추가 개선사항

---

## 작업 시작 전 체크리스트

```
□ 백엔드 개발 환경 실행 확인 (uvicorn, Redis, Celery)
□ 프론트엔드 개발 환경 실행 확인 (npm run dev)
□ Supabase 연결 확인 (SUPABASE_URL, SUPABASE_KEY)
□ R2 스토리지 연결 확인 (app/config.py 환경변수)
□ patterns.json 읽기 완료 (file-extension-hardcode-srt 패턴 확인)
```

---

## 다음 단계

**어떤 작업부터 시작할까요?**

옵션:
1. **Task 1.1 먼저** - M4A 지원 버그 수정 (patterns.json 패턴 발견됨)
2. **Task 2.3 먼저** - VideoOptionsForm 구현 (사용자 기능 추가)
3. **전체 Phase 1 실행** - 패턴 검증 + 보안 스캔 먼저 완료
4. **다른 작업** - 우선순위 조정 필요

**사용자님께 확인:**
- 현재 가장 급한 문제가 무엇인가요?
- M4A 파일 업로드가 실제로 실패하고 있나요?
- 사용자들이 클립/BGM 선택 기능을 요구하고 있나요?
