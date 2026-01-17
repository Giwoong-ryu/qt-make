"""
Celery 백그라운드 작업 - QT 영상 생성 파이프라인
"""
import logging
import os
from datetime import datetime
from uuid import uuid4

from celery import Task

from app.celery_app import celery_app
from app.config import get_settings
from app.services.clips import get_clip_selector
from app.services.storage import get_r2_storage
from app.services.stt import get_whisper_service
from app.services.stt_correction import get_correction_service
from app.services.video import get_video_composer
from app.services.thumbnail import get_thumbnail_generator

logger = logging.getLogger(__name__)
settings = get_settings()


class CallbackTask(Task):
    """작업 진행 상태를 추적하는 베이스 태스크"""

    def on_success(self, retval, task_id, args, kwargs):
        """작업 성공 시"""
        logger.info(f"Task {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """작업 실패 시"""
        logger.error(f"Task {task_id} failed: {exc}")


@celery_app.task(base=CallbackTask, bind=True, max_retries=3)
def process_video_task(
    self,
    audio_file_path: str,
    church_id: str,
    video_id: str,
    pack_id: str = "pack-free",
    clip_ids: list[str] | None = None,
    bgm_id: str | None = None,
    bgm_volume: float = 0.12
):
    """
    QT 영상 생성 메인 파이프라인

    전체 흐름:
    1. MP3 → SRT (Groq Whisper)
    2. 배경 클립 선택 (Supabase)
    3. 클립 + 오디오 + 자막 → MP4 (FFmpeg)
    4. MP4 업로드 (Cloudflare R2)
    5. 메타데이터 저장 (Supabase)

    Args:
        audio_file_path: 업로드된 MP3 파일 경로
        church_id: 교회 UUID
        video_id: 영상 UUID (미리 생성됨)
        pack_id: 배경팩 ID

    Returns:
        dict: {video_url, srt_url, duration, clips_used}
    """
    from supabase import create_client

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    temp_files = []  # 정리할 임시 파일들

    try:
        # ========================================
        # Step 1: 음성 → 자막 (10%)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 5, "step": "음성 인식 중..."}
        )

        whisper = get_whisper_service()
        srt_path = whisper.transcribe_to_srt(audio_file_path, language="ko")
        temp_files.append(srt_path)

        logger.info(f"[Step 1/5] SRT 생성 완료: {srt_path}")

        # ========================================
        # Step 1.5: 이중 사전 적용 (통합 + 교회별)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 15, "step": "자막 자동 교정 중..."}
        )

        try:
            correction_service = get_correction_service()

            # SRT 파일 읽기
            with open(srt_path, "r", encoding="utf-8") as f:
                srt_content = f.read()

            total_applied = []

            # ----------------------------------------
            # 1단계: 통합 사전 적용 (성경 고유명사 등)
            # ----------------------------------------
            global_dict_result = supabase.table("global_dictionary") \
                .select("original, replacement, category, priority") \
                .eq("is_active", True) \
                .order("priority", desc=True) \
                .order("category") \
                .execute()

            if global_dict_result.data:
                # 통합 사전 형식 맞추기 (use_count 필드 추가)
                global_entries = [
                    {"original": e["original"], "replacement": e["replacement"], "use_count": e.get("priority", 0)}
                    for e in global_dict_result.data
                ]

                srt_content, global_applied = correction_service.apply_replacement_dictionary(
                    srt_content, global_entries
                )

                if global_applied:
                    total_applied.extend([f"[통합]{a}" for a in global_applied])
                    logger.info(f"[Step 1.5a] 통합 사전 적용: {len(global_applied)}개 교정")

            # ----------------------------------------
            # 2단계: 교회별 사전 적용 (우선 - 덮어쓰기)
            # ----------------------------------------
            church_dict_result = supabase.table("replacement_dictionary") \
                .select("original, replacement, use_count") \
                .eq("church_id", church_id) \
                .order("use_count", desc=True) \
                .limit(100) \
                .execute()

            if church_dict_result.data:
                srt_content, church_applied = correction_service.apply_replacement_dictionary(
                    srt_content, church_dict_result.data
                )

                if church_applied:
                    total_applied.extend([f"[교회]{a}" for a in church_applied])
                    logger.info(f"[Step 1.5b] 교회별 사전 적용: {len(church_applied)}개 교정")

            # ----------------------------------------
            # 교정된 SRT 저장
            # ----------------------------------------
            if total_applied:
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                logger.info(f"[Step 1.5] 총 {len(total_applied)}개 교정 완료")
            else:
                logger.info(f"[Step 1.5] 교정 없음 (church_id: {church_id})")

        except Exception as e:
            logger.warning(f"치환 사전 적용 실패 (무시하고 진행): {e}")

        self.update_state(
            state="PROCESSING",
            meta={"progress": 20, "step": "자막 생성 완료"}
        )

        # ========================================
        # Step 2: 배경 클립 선택 (20%)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 25, "step": "배경 영상 선택 중..."}
        )

        video_composer = get_video_composer()
        audio_duration = video_composer.get_audio_duration(audio_file_path)

        clip_selector = get_clip_selector()

        # 템플릿에서 선택한 클립이 있으면 그것 사용, 없으면 자동 선택
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

        clip_paths = [clip["file_path"] for clip in selected_clips]
        used_clip_ids = [clip["id"] for clip in selected_clips]
        clip_durations = [clip.get("duration", 30) for clip in selected_clips]

        total_clip_duration = sum(clip_durations)
        logger.info(
            f"[Step 2/5] 클립 선택 완료: {len(clip_paths)}개, "
            f"총 클립 길이: {total_clip_duration}초, 오디오 길이: {audio_duration}초"
        )

        self.update_state(
            state="PROCESSING",
            meta={"progress": 30, "step": f"{len(clip_paths)}개 클립 선택됨"}
        )

        # ========================================
        # Step 3: FFmpeg 영상 합성 (70%)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 35, "step": "영상 합성 중... (시간 소요)"}
        )

        # 썸네일 레이아웃 조회 (인트로/아웃트로 사용 여부 확인)
        thumbnail_layout = None
        use_thumbnail_intro = False
        intro_duration = 2.0
        use_outro = False
        outro_duration = 3.0

        try:
            video_record = supabase.table("videos").select(
                "thumbnail_layout, title"
            ).eq("id", video_id).single().execute()

            if video_record.data and video_record.data.get("thumbnail_layout"):
                thumbnail_layout = video_record.data["thumbnail_layout"]
                intro_settings = thumbnail_layout.get("intro_settings", {})
                use_thumbnail_intro = intro_settings.get("useAsIntro", False)
                intro_duration = intro_settings.get("introDuration", 2.0)
                # 아웃트로 사용 여부
                use_outro = intro_settings.get("useAsOutro", False)
                outro_duration = intro_settings.get("outroDuration", 3.0)

                logger.info(f"[Step 3] 썸네일 레이아웃 발견 - 인트로: {use_thumbnail_intro}, 아웃트로: {use_outro}")
        except Exception as e:
            logger.warning(f"썸네일 레이아웃 조회 실패 (무시하고 진행): {e}")

        # 썸네일 인트로 사용 시 이미지 생성
        thumbnail_image_path = None
        if use_thumbnail_intro and thumbnail_layout:
            try:
                self.update_state(
                    state="PROCESSING",
                    meta={"progress": 38, "step": "인트로 썸네일 생성 중..."}
                )

                thumbnail_gen = get_thumbnail_generator()
                text_boxes = thumbnail_layout.get("text_boxes", [])

                # 배경 이미지 URL 가져오기
                background_url = thumbnail_layout.get("background_image_url", "")

                if background_url:
                    # 원격 URL인 경우 임시 다운로드
                    import httpx
                    import tempfile as tf

                    if background_url.startswith("http"):
                        # URL 공백 인코딩
                        from urllib.parse import quote, urlparse, urlunparse
                        parsed = urlparse(background_url)
                        encoded_path = quote(parsed.path, safe='/')
                        background_url = urlunparse(parsed._replace(path=encoded_path))

                        response = httpx.get(background_url, timeout=30.0)
                        response.raise_for_status()

                        # 임시 파일로 저장
                        with tf.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                            f.write(response.content)
                            local_bg_path = f.name
                        temp_files.append(local_bg_path)
                    else:
                        local_bg_path = background_url

                    # 범용 텍스트박스 기반 썸네일 생성 (ID 무관하게 위치/색상으로 렌더링)
                    thumbnail_image_path = thumbnail_gen.generate_thumbnail_with_textboxes(
                        background_image_path=local_bg_path,
                        text_boxes=text_boxes,
                        overlay_opacity=0.3,
                        output_size=(1920, 1080)
                    )
                    temp_files.append(thumbnail_image_path)
                    logger.info(f"[Step 3] 인트로 썸네일 이미지 생성 완료: {thumbnail_image_path}")
                else:
                    logger.warning("[Step 3] 배경 이미지 URL 없음 - 인트로 생략")
                    use_thumbnail_intro = False

            except Exception as e:
                logger.warning(f"인트로 썸네일 생성 실패 (인트로 없이 진행): {e}")
                use_thumbnail_intro = False
                thumbnail_image_path = None

        # 아웃트로 이미지 생성 (인트로와 같은 배경, 텍스트 없이)
        outro_image_path = None
        if use_outro and thumbnail_layout:
            try:
                self.update_state(
                    state="PROCESSING",
                    meta={"progress": 42, "step": "아웃트로 이미지 생성 중..."}
                )

                # 배경 이미지 다운로드 (인트로와 동일한 배경 사용)
                background_url = thumbnail_layout.get("background_image_url", "")

                if background_url:
                    import httpx
                    import tempfile as tf

                    # 이미 다운로드한 로컬 파일이 있으면 재사용
                    if 'local_bg_path' not in locals():
                        if background_url.startswith("http"):
                            from urllib.parse import quote, urlparse, urlunparse
                            parsed = urlparse(background_url)
                            encoded_path = quote(parsed.path, safe='/')
                            background_url = urlunparse(parsed._replace(path=encoded_path))

                            response = httpx.get(background_url, timeout=30.0)
                            response.raise_for_status()

                            with tf.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                                f.write(response.content)
                                local_bg_path = f.name
                            temp_files.append(local_bg_path)
                        else:
                            local_bg_path = background_url

                    # 아웃트로 이미지 생성 (텍스트 없이 배경만)
                    thumbnail_gen = get_thumbnail_generator()
                    outro_image_path = thumbnail_gen.generate_outro_image(
                        background_image_path=local_bg_path,
                        overlay_opacity=0.3,
                        output_size=(1920, 1080)
                    )
                    temp_files.append(outro_image_path)
                    logger.info(f"[Step 3] 아웃트로 이미지 생성 완료: {outro_image_path}")
                else:
                    logger.warning("[Step 3] 배경 이미지 URL 없음 - 아웃트로 생략")
                    use_outro = False

            except Exception as e:
                logger.warning(f"아웃트로 이미지 생성 실패 (아웃트로 없이 진행): {e}")
                use_outro = False
                outro_image_path = None

        # 영상 합성 (인트로/아웃트로 유무에 따라 분기)
        if use_thumbnail_intro and thumbnail_image_path:
            output_video_path = video_composer.compose_video_with_thumbnail(
                clip_paths=clip_paths,
                audio_path=audio_file_path,
                srt_path=srt_path,
                audio_duration=audio_duration,
                thumbnail_path=thumbnail_image_path,
                thumbnail_duration=intro_duration,
                fade_duration=1.0,
                clip_durations=clip_durations,
                # 아웃트로 옵션
                outro_image_path=outro_image_path if use_outro else None,
                outro_duration=outro_duration
            )
        else:
            output_video_path = video_composer.compose_video(
                clip_paths=clip_paths,
                audio_path=audio_file_path,
                srt_path=srt_path,
                audio_duration=audio_duration,
                clip_durations=clip_durations
            )
        temp_files.append(output_video_path)

        logger.info(f"[Step 3/5] 영상 합성 완료: {output_video_path}")

        self.update_state(
            state="PROCESSING",
            meta={"progress": 70, "step": "영상 합성 완료"}
        )

        # ========================================
        # Step 4: R2 업로드 (90%)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 75, "step": "클라우드 업로드 중..."}
        )

        r2 = get_r2_storage()

        # 영상 업로드
        video_url = r2.upload_file(
            file_path=output_video_path,
            folder="videos",
            content_type="video/mp4"
        )

        # 자막 업로드
        srt_url = r2.upload_file(
            file_path=srt_path,
            folder="srt",
            content_type="text/plain"
        )

        # 오디오 파일 업로드 (재생성 시 필요)
        audio_ext = os.path.splitext(audio_file_path)[1].lower()
        audio_content_type = "audio/mpeg" if audio_ext == ".mp3" else "audio/mp4"
        audio_url = r2.upload_file(
            file_path=audio_file_path,
            folder="audio",
            content_type=audio_content_type
        )

        logger.info(f"[Step 4/5] R2 업로드 완료 (video, srt, audio)")

        self.update_state(
            state="PROCESSING",
            meta={"progress": 90, "step": "업로드 완료"}
        )

        # ========================================
        # Step 5: Supabase 메타데이터 저장 (100%)
        # ========================================
        self.update_state(
            state="PROCESSING",
            meta={"progress": 95, "step": "메타데이터 저장 중..."}
        )

        # videos 테이블 업데이트
        supabase.table("videos").update({
            "video_file_path": video_url,
            "srt_file_path": srt_url,
            "audio_file_path": audio_url,  # R2 URL로 업데이트 (재생성 시 필요)
            "duration": audio_duration,
            "status": "completed",
            "clips_used": used_clip_ids,
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", video_id).execute()

        # 클립 사용 횟수 증가
        for cid in used_clip_ids:
            supabase.rpc("increment_clip_used_count", {"clip_id": cid}).execute()

        logger.info(f"[Step 5/5] 메타데이터 저장 완료")

        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "step": "완료!"}
        )

        return {
            "status": "completed",
            "video_id": video_id,
            "video_url": video_url,
            "srt_url": srt_url,
            "duration": audio_duration,
            "clips_used": used_clip_ids
        }

    except Exception as e:
        logger.exception(f"Video processing failed: {e}")

        # 실패 상태 저장
        try:
            supabase.table("videos").update({
                "status": "failed",
                "error_message": str(e)[:500]
            }).eq("id", video_id).execute()
        except Exception:
            pass

        # Celery 재시도 (최대 3회)
        raise self.retry(exc=e, countdown=60)

    finally:
        # 임시 파일 정리
        _cleanup_temp_files(temp_files)
        _cleanup_temp_files([audio_file_path])


def _cleanup_temp_files(paths: list) -> None:
    """임시 파일 삭제"""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.debug(f"Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")


@celery_app.task(base=CallbackTask, bind=True)
def batch_process_videos_task(
    self,
    audio_file_paths: list,
    church_id: str,
    pack_id: str = "pack-free",
    clip_ids: list[str] | None = None,
    bgm_id: str | None = None,
    bgm_volume: float = 0.12
):
    """
    주간 영상 일괄 처리 (7개 파일)

    Args:
        audio_file_paths: MP3 파일 경로 리스트
        church_id: 교회 UUID
        pack_id: 배경팩 ID
        clip_ids: 템플릿에서 선택한 클립 ID 리스트
        bgm_id: BGM ID
        bgm_volume: BGM 볼륨

    Returns:
        list: 각 영상의 처리 결과
    """
    from supabase import create_client

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    results = []
    total = len(audio_file_paths)

    for idx, audio_path in enumerate(audio_file_paths, 1):
        try:
            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": int((idx - 1) / total * 100),
                    "step": f"영상 {idx}/{total} 처리 중..."
                }
            )

            # videos 테이블에 레코드 생성
            video_record = supabase.table("videos").insert({
                "church_id": church_id,
                "audio_file_path": audio_path,
                "status": "processing"
            }).execute()

            video_id = video_record.data[0]["id"]

            # 개별 영상 처리 (동기 호출)
            result = process_video_task.apply(
                args=[audio_path, church_id, video_id, pack_id, clip_ids, bgm_id, bgm_volume]
            ).get(timeout=600)  # 10분 타임아웃

            results.append({
                "index": idx,
                "status": "success",
                "video_id": video_id,
                "video_url": result.get("video_url")
            })

        except Exception as e:
            logger.error(f"Batch item {idx} failed: {e}")
            results.append({
                "index": idx,
                "status": "failed",
                "error": str(e)[:200]
            })

    return {
        "total": total,
        "success": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results
    }



@celery_app.task(base=CallbackTask, bind=True, max_retries=3)
def regenerate_video_task(
    self,
    video_id: str,
    church_id: str,
    clip_ids: list[str] | None = None,
    bgm_id: str | None = None,
    bgm_volume: float = 0.12
):
    """
    영상 재생성 (자막 수정, BGM 변경, 클립 변경 반영)
    STT 단계를 건너뛰고 기존 SRT(또는 수정된 SRT)를 사용
    """
    from supabase import create_client
    import httpx
    import tempfile
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    temp_files = []
    
    try:
        # 1. 영상 정보 조회
        video_res = supabase.table("videos").select("*").eq("id", video_id).single().execute()
        if not video_res.data:
            raise ValueError(f"Video not found: {video_id}")
            
        video_data = video_res.data
        if video_data["church_id"] != church_id:
             raise ValueError("Permission denied")

        audio_url = video_data["audio_file_path"]
        srt_url = video_data["srt_file_path"]

        # URL이 상대 경로인 경우 R2 Public URL 붙이기
        if audio_url and not audio_url.startswith("http"):
            audio_url = f"{settings.R2_PUBLIC_URL}/{audio_url}"
        if srt_url and not srt_url.startswith("http"):
            srt_url = f"{settings.R2_PUBLIC_URL}/{srt_url}"

        # 2. 리소스 다운로드 (Audio, SRT)
        self.update_state(state="PROCESSING", meta={"progress": 10, "step": "리소스 다운로드 중..."})

        # Audio 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            resp = httpx.get(audio_url, timeout=60.0)
            if resp.status_code != 200:
                raise ValueError(f"오디오 파일 다운로드 실패 (HTTP {resp.status_code}): {audio_url}")
            if len(resp.content) < 1000:  # 1KB 미만이면 유효하지 않음
                raise ValueError(f"오디오 파일이 비어있거나 손상됨: {audio_url}")
            f.write(resp.content)
            audio_path = f.name
            temp_files.append(audio_path)

        # SRT 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=".srt") as f:
            resp = httpx.get(srt_url, timeout=60.0)
            if resp.status_code != 200:
                raise ValueError(f"자막 파일 다운로드 실패 (HTTP {resp.status_code}): {srt_url}")
            f.write(resp.content)
            srt_path = f.name
            temp_files.append(srt_path)
            
        # BGM 다운로드 (옵션)
        bgm_path = None
        if bgm_id:
            bgm_res = supabase.table("bgms").select("file_path").eq("id", bgm_id).single().execute()
            if bgm_res.data:
                bgm_url = bgm_res.data["file_path"]
                if not bgm_url.startswith("http"):
                    bgm_url = f"{settings.R2_PUBLIC_URL}/{bgm_url}"
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    resp = httpx.get(bgm_url, timeout=30.0)
                    f.write(resp.content)
                    bgm_path = f.name
                    temp_files.append(bgm_path)

        # 3. 클립 선택
        self.update_state(state="PROCESSING", meta={"progress": 30, "step": "클립 구성 중..."})
        
        clip_selector = get_clip_selector()
        video_composer = get_video_composer()
        audio_duration = video_composer.get_audio_duration(audio_path)
        
        final_clip_ids = clip_ids if clip_ids else video_data.get("clips_used", [])
        
        if final_clip_ids:
            selected_clips = clip_selector.get_clips_by_ids(final_clip_ids, audio_duration)
        else:
            # Fallback
            selected_clips = clip_selector.select_clips(audio_duration, pack_id="pack-free")
            
        clip_paths = [c["file_path"] for c in selected_clips]
        used_clip_ids = [c["id"] for c in selected_clips]
        clip_durations = [c.get("duration", 30) for c in selected_clips]
        
        # Note: video_composer.BGM_VOLUME can be overridden if needed, 
        # but for now we set it globally or need to refactor VideoComposer to accept volume per call.
        # Currently VideoComposer uses a class constant BGM_VOLUME = 0.12.
        # To support custom volume, we might need to modify VideoComposer later. 
        # For now, we proceed with default or modification if class allows.
        # VideoComposer.BGM_VOLUME = bgm_volume # Not thread safe for concurrent tasks!
        
        # 4. 썸네일 인트로 확인
        thumbnail_layout = video_data.get("thumbnail_layout")
        use_intro = False
        intro_duration = 2.0
        thumbnail_image_path = None
        
        # 아웃트로 설정
        use_outro = False
        outro_duration = 3.0
        outro_image_path = None

        if thumbnail_layout:
            intro_settings = thumbnail_layout.get("intro_settings", {})
            use_intro = intro_settings.get("useAsIntro", False)
            intro_duration = intro_settings.get("introDuration", 2.0)
            # 아웃트로 사용 여부 (인트로와 같은 배경 사용, 텍스트 없이)
            use_outro = intro_settings.get("useAsOutro", False)
            outro_duration = intro_settings.get("outroDuration", 3.0)

        if use_intro:
            try:
                # 썸네일 생성 로직
                self.update_state(state="PROCESSING", meta={"progress": 40, "step": "인트로 썸네일 생성 중..."})

                import httpx
                import tempfile as tf

                # 배경 이미지 다운로드 (snake_case 또는 camelCase 둘 다 지원)
                bg_url = thumbnail_layout.get("background_image_url") or thumbnail_layout.get("backgroundImageUrl")
                if not bg_url:
                    raise ValueError("Background image URL missing")

                # R2 URL 처리
                if not bg_url.startswith("http"):
                    bg_url = f"{settings.R2_PUBLIC_URL}/{bg_url}"

                # URL 공백 인코딩
                from urllib.parse import quote, urlparse, urlunparse
                parsed = urlparse(bg_url)
                encoded_path = quote(parsed.path, safe='/')
                bg_url = urlunparse(parsed._replace(path=encoded_path))

                # 이미지 다운로드
                resp = httpx.get(bg_url, timeout=30.0)
                resp.raise_for_status()
                with tf.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                    f.write(resp.content)
                    local_bg_path = f.name
                temp_files.append(local_bg_path)

                # 텍스트 박스 준비 (snake_case 또는 camelCase 둘 다 지원)
                text_boxes = thumbnail_layout.get("text_boxes") or thumbnail_layout.get("textBoxes") or []

                # 범용 텍스트박스 기반 썸네일 생성 (ID 무관하게 위치/색상으로 렌더링)
                thumbnail_gen = get_thumbnail_generator()
                thumbnail_image_path = thumbnail_gen.generate_thumbnail_with_textboxes(
                    background_image_path=local_bg_path,
                    text_boxes=text_boxes,
                    overlay_opacity=0.3,
                    output_size=(1920, 1080)
                )
                temp_files.append(thumbnail_image_path)
                logger.info(f"[Regenerate] 인트로 썸네일 이미지 생성 완료: {thumbnail_image_path}")

            except Exception as e:
                logger.warning(f"인트로 썸네일 생성 실패 (인트로 없이 진행): {e}")
                use_intro = False
                thumbnail_image_path = None

        # 아웃트로 이미지 생성 (인트로와 같은 배경, 텍스트 없이)
        if use_outro and thumbnail_layout:
            try:
                self.update_state(state="PROCESSING", meta={"progress": 45, "step": "아웃트로 이미지 생성 중..."})

                import httpx
                import tempfile as tf

                # 배경 이미지 다운로드 (인트로와 동일한 배경 사용)
                bg_url = thumbnail_layout.get("background_image_url") or thumbnail_layout.get("backgroundImageUrl")
                if not bg_url:
                    raise ValueError("Background image URL missing for outro")

                if not bg_url.startswith("http"):
                    bg_url = f"{settings.R2_PUBLIC_URL}/{bg_url}"

                # URL 공백 인코딩
                from urllib.parse import quote, urlparse, urlunparse
                parsed = urlparse(bg_url)
                encoded_path = quote(parsed.path, safe='/')
                bg_url = urlunparse(parsed._replace(path=encoded_path))

                # 이미지 다운로드 (인트로에서 이미 다운로드했으면 재사용)
                if 'local_bg_path' not in locals() or not os.path.exists(local_bg_path):
                    resp = httpx.get(bg_url, timeout=30.0)
                    resp.raise_for_status()
                    with tf.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                        f.write(resp.content)
                        local_bg_path = f.name
                    temp_files.append(local_bg_path)

                # 아웃트로 이미지 생성 (텍스트 없이 배경만)
                thumbnail_gen = get_thumbnail_generator()
                outro_image_path = thumbnail_gen.generate_outro_image(
                    background_image_path=local_bg_path,
                    overlay_opacity=0.3,
                    output_size=(1920, 1080)
                )
                temp_files.append(outro_image_path)
                logger.info(f"[Regenerate] 아웃트로 이미지 생성 완료: {outro_image_path}")

            except Exception as e:
                logger.warning(f"아웃트로 이미지 생성 실패 (아웃트로 없이 진행): {e}")
                use_outro = False
                outro_image_path = None

        # 5. 영상 합성
        self.update_state(state="PROCESSING", meta={"progress": 50, "step": "영상 합성 중..."})

        if use_intro and thumbnail_image_path:
            output_video_path = video_composer.compose_video_with_thumbnail(
                clip_paths=clip_paths,
                audio_path=audio_path,
                srt_path=srt_path,
                audio_duration=audio_duration,
                thumbnail_path=thumbnail_image_path,
                thumbnail_duration=intro_duration,
                bgm_path=bgm_path,
                clip_durations=clip_durations,
                bgm_volume=bgm_volume,
                # 아웃트로 옵션
                outro_image_path=outro_image_path if use_outro else None,
                outro_duration=outro_duration
            )
        else:
            output_video_path = video_composer.compose_video(
                clip_paths=clip_paths,
                audio_path=audio_path,
                srt_path=srt_path,
                audio_duration=audio_duration,
                bgm_path=bgm_path,
                clip_durations=clip_durations,
                bgm_volume=bgm_volume
            )
        temp_files.append(output_video_path)
        
        # 6. 업로드 및 저장
        self.update_state(state="PROCESSING", meta={"progress": 80, "step": "업로드 중..."})
        
        r2 = get_r2_storage()
        video_url = r2.upload_file(output_video_path, "videos", "video/mp4")
        
        supabase.table("videos").update({
            "video_file_path": video_url,
            "clips_used": used_clip_ids,
            "bgm_id": bgm_id,
            "bgm_volume": bgm_volume,
            "status": "completed"
        }).eq("id", video_id).execute()
        
        # Cleanup
        for p in temp_files:
            if os.path.exists(p):
                os.remove(p)
                
        return {"video_url": video_url}
        
    except Exception as e:
        logger.exception(f"Regenerate task failed: {e}")

        # 사용자 친화적 에러 메시지 생성
        error_str = str(e).lower()
        if "audio" in error_str or "mp3" in error_str or "m4a" in error_str or "wav" in error_str:
            user_message = "audio: 음성 파일 처리 실패 - 파일이 손상되었거나 지원하지 않는 형식입니다"
        elif "clip" in error_str or "background" in error_str or "video file" in error_str:
            user_message = "clip: 배경 클립 처리 실패 - 클립 파일을 찾을 수 없거나 손상되었습니다"
        elif "bgm" in error_str or "music" in error_str:
            user_message = "bgm: BGM 처리 실패 - BGM 파일을 찾을 수 없거나 손상되었습니다"
        elif "srt" in error_str or "subtitle" in error_str:
            user_message = "subtitle: 자막 파일 생성 실패 - 음성 인식에 문제가 발생했습니다"
        elif "thumbnail" in error_str or "intro" in error_str:
            user_message = "intro: 인트로/썸네일 생성 실패 - 썸네일 설정을 확인해주세요"
        elif "ffmpeg" in error_str or "codec" in error_str or "encoding" in error_str:
            user_message = "encoding: 영상 인코딩 실패 - 서버 문제일 수 있습니다. 다시 시도해주세요"
        elif "duration" in error_str or "too long" in error_str:
            user_message = "duration: 영상 길이 초과 - 최대 10분까지 지원됩니다"
        elif "storage" in error_str or "r2" in error_str or "upload" in error_str:
            user_message = "storage: 파일 저장 실패 - 잠시 후 다시 시도해주세요"
        else:
            user_message = f"unknown: {str(e)[:300]}"

        # 실패 상태 저장 (사용자 친화적 메시지 포함)
        try:
            supabase.table("videos").update({
                "status": "failed",
                "error_message": user_message
            }).eq("id", video_id).execute()
        except Exception:
            pass

        # Cleanup on failure
        for p in temp_files:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass
        raise e
