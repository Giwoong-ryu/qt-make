"""
FastAPI 메인 애플리케이션
"""
import logging
import os
import tempfile
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import httpx

from app.config import get_settings
from app.services.storage import R2Storage
from app.services.thumbnail import get_thumbnail_generator
from app.tasks import batch_process_videos_task, process_video_task, regenerate_video_task
from app.utils.srt_utils import generate_srt, parse_srt, validate_subtitles
from app.utils.thumbnail_utils import extract_thumbnail_from_url, validate_image_file
from app.routers.stt import router as stt_router
from app.routers.dictionary import router as dictionary_router
from app.routers.replacement_dictionary import router as replacement_dictionary_router
from app.routers.auth import router as auth_router
from app.routers.subscription import router as subscription_router, webhook_router
from supabase import create_client

# Rate Limiting (slowapi 설치 필요 - Docker 재빌드 시 활성화)
# from app.middleware.rate_limit import get_rate_limiter
# from slowapi.errors import RateLimitExceeded
# from slowapi import _rate_limit_exceeded_handler

# Settings
settings = get_settings()

# 로깅 설정 (환경변수 기반)
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Supabase 클라이언트
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# R2 스토리지 클라이언트
r2 = R2Storage()

# 썸네일 생성기
thumbnail_generator = get_thumbnail_generator()

# Rate Limiter (Docker 재빌드 후 활성화)
# limiter = get_rate_limiter()

# FastAPI 앱
app = FastAPI(
    title="QT Video SaaS API",
    description="교회 묵상 영상 자동화 API",
    version="1.0.0",
    debug=settings.DEBUG
)

# Rate Limiter 등록 (Docker 재빌드 후 활성화)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정 (환경변수 + 강제 추가)
# Railway 환경변수에 의해 덮어씌워질 경우를 대비해 코드 레벨에서 필수 도메인 보장
raw_origins = settings.CORS_ORIGINS.split(",")
required_origins = [
    "https://www.qt-make.com", 
    "https://qt-make.com", 
    "http://localhost:3000",
    "http://localhost:3001"
]
# 중복 제거 및 병합
cors_origins = list(set([o.strip() for o in raw_origins + required_origins if o.strip()]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel 프리뷰 (regex 패턴)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안 헤더 미들웨어
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Request validation error handler (400 에러 디버깅용)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
    logger.error(f"Request body type: {type(exc.body)}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)[:500] if exc.body else None}
    )

# 모든 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"=== Incoming request ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Content-Type: {request.headers.get('content-type', 'None')}")
    logger.info(f"Content-Length: {request.headers.get('content-length', 'None')}")

    response = await call_next(request)

    logger.info(f"Response status: {response.status_code}")
    return response

# 라우터 등록
logger.info("라우터 등록 시작...")
app.include_router(auth_router)
app.include_router(stt_router)
app.include_router(dictionary_router)
app.include_router(replacement_dictionary_router)
app.include_router(subscription_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "QT Video SaaS",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """상세 헬스 체크 (외부 서비스 연결 검증)"""
    checks = {}
    all_ok = True

    # Redis 연결 확인
    try:
        from redis import asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"failed: {str(e)[:50]}"
        all_ok = False

    # Supabase 연결 확인
    try:
        # 간단한 쿼리로 연결 테스트
        supabase.table("subscriptions").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"failed: {str(e)[:50]}"
        all_ok = False

    # R2 스토리지 확인 (선택적)
    try:
        # R2 자격증명 확인만 (실제 요청은 비용 발생 가능)
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            checks["r2"] = "configured"
        else:
            checks["r2"] = "not_configured"
    except Exception as e:
        checks["r2"] = f"error: {str(e)[:50]}"

    # 등록된 라우트 확인 (디버깅용)
    routes = []
    for route in request.app.routes:
        if hasattr(route, "path"):
            routes.append(route.path)

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_ok else "degraded",
            "env": settings.ENV,
            "checks": checks,
            "routes": sorted(routes)  # 라우트 목록 반환
        }
    )


@app.post("/api/test-upload")
async def test_upload(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    church_id: str = Form(default=""),
):
    """테스트 업로드 엔드포인트"""
    logger.info(f"Test upload: files={len(files)}, church_id={church_id}")
    logger.info(f"Content-Type: {request.headers.get('content-type')}")
    return {"files": len(files), "church_id": church_id}


@app.post("/api/videos/upload")
async def upload_videos(
    request: Request,
    # 2026-01-23 개선: 기본값 부여하여 FastAPI 기본 422 에러 대신 명확한 커스텀 400 에러 반환
    files: list[UploadFile] = File(default=[]),
    church_id: str = Form(default=""),
    pack_id: str = Form(default="pack-free"),
    # 프론트엔드 호환용
    title: str | None = Form(default=None),
    clip_ids: str | None = Form(default=None),
    bgm_id: str | None = Form(default=None),
    bgm_volume: str | None = Form(default=None),
    generate_thumbnail: str | None = Form(default=None),  # 사용자가 요청한 썸네일 생성 옵션
    generation_mode: str | None = Form(default="natural"),
    subtitle_length: str | None = Form(default="short"),
    generate_edit_pack: str | None = Form(default=None),
    video_tone: str | None = Form(default="bright"),  # v2.2: 영상 톤 ("bright" / "dark")
    authorization: str | None = Header(default=None)
):
    """
    MP3 파일 업로드 및 영상 생성 작업 큐 추가
    """
    # 디버그 로깅
    logger.info(f"Content-Type: {request.headers.get('content-type')}")
    logger.info(f"Upload request: files={len(files)}, church_id={church_id}")

    # 1. 파일 누락 체크 (친절한 에러 메시지)
    if not files:
        raise HTTPException(
            status_code=400,
            detail="업로드할 파일을 선택해주세요. (MP3, M4A, WAV 지원)"
        )

    # 2. 교회 ID 누락 체크
    if not church_id:
        raise HTTPException(
            status_code=400,
            detail="교회 ID가 누락되었습니다. 다시 로그인해주세요."
        )

    # 파일 수 검증
    if len(files) > 7:
        raise HTTPException(
            status_code=400,
            detail="최대 7개 파일까지 업로드 가능합니다."
        )

    # ===== 크레딧 체크 (무료 플랜) =====
    user_id = None
    if authorization:
        # Bearer 토큰 추출
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

            # JWT 토큰 검증
            try:
                from app.services.auth_service import AuthService
                auth_service = AuthService()
                user = await auth_service.verify_token(token)

                if user:
                    user_id = user.id

                    # 사용자 플랜 정보 조회
                    user_result = supabase.table("users").select(
                        "subscription_plan, weekly_credits, weekly_credits_reset_at"
                    ).eq("id", user_id).single().execute()

                    user_data = user_result.data
                    plan = user_data.get("subscription_plan", "free")
                    weekly_credits = user_data.get("weekly_credits", 0)

                    # 무료 플랜 크레딧 체크
                    if plan == "free":
                        required_credits = len(files)  # 파일 1개당 1 크레딧

                        if weekly_credits < required_credits:
                            raise HTTPException(
                                status_code=402,
                                detail=f"주간 무료 크레딧이 부족합니다. (필요: {required_credits}개, 보유: {weekly_credits}개)\n"
                                       f"매주 월요일 0시에 10개로 충전됩니다."
                            )

                        # 크레딧 차감
                        supabase.table("users").update({
                            "weekly_credits": weekly_credits - required_credits
                        }).eq("id", user_id).execute()

                        logger.info(f"Credits deducted: user={user_id}, used={required_credits}, remaining={weekly_credits - required_credits}")

                    # 유료 플랜 (basic, pro, enterprise)은 무제한 (추후 구현)

            except Exception as e:
                logger.warning(f"Auth token verification failed: {e}")
                # 토큰 검증 실패해도 계속 진행 (비회원 허용)
    # ===== 크레딧 체크 끝 =====

    # 파일 형식 검증
    allowed_extensions = ('.mp3', '.wav', '.m4a')
    for file in files:
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식: {file.filename}. MP3, WAV, M4A만 가능합니다."
            )

    # 교회 존재 여부 확인
    church = supabase.table("churches").select("id, pack_id").eq("id", church_id).execute()
    if not church.data:
        raise HTTPException(status_code=404, detail="교회를 찾을 수 없습니다.")

    # 교회의 배경팩 사용 (없으면 기본 무료팩)
    actual_pack_id = church.data[0].get("pack_id") or pack_id

    logger.info(f"Received {len(files)} files from church: {church_id}")

    # 파일 저장 및 DB 레코드 생성
    audio_paths = []
    video_ids = []

    for file in files:
        # 오디오 파일을 R2에 업로드 (API와 Worker가 파일 공유 가능하도록)
        file_id = str(uuid4())
        file_ext = os.path.splitext(file.filename)[1].lower()

        content = await file.read()

        # R2에 업로드
        r2_key = f"audio/{file_id}{file_ext}"
        content_type = "audio/mpeg" if file_ext == ".mp3" else f"audio/{file_ext[1:]}"
        audio_url = r2.upload_bytes(content, r2_key, content_type)

        logger.info(f"Audio uploaded to R2: {audio_url}")
        audio_paths.append(audio_url)

        # videos 테이블에 레코드 생성 (pending 상태)
        # title: 프론트엔드에서 보낸 값 우선, 없으면 파일명 사용
        video_title = title if title else file.filename
        video_record = supabase.table("videos").insert({
            "church_id": church_id,
            "title": video_title,
            "audio_file_path": audio_url,  # R2 URL 저장
            "status": "pending"
        }).execute()

        video_ids.append(video_record.data[0]["id"])

    # clip_ids 파싱 (JSON 문자열 → 리스트)
    parsed_clip_ids = None
    if clip_ids:
        try:
            import json
            parsed_clip_ids = json.loads(clip_ids)
            logger.info(f"Parsed clip_ids: {parsed_clip_ids}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid clip_ids format: {clip_ids}")

    # bgm_volume 파싱 (문자열 → float)
    parsed_bgm_volume = 0.12  # 기본값
    if bgm_volume:
        try:
            parsed_bgm_volume = float(bgm_volume)
        except ValueError:
            logger.warning(f"Invalid bgm_volume format: {bgm_volume}")

    # subtitle_length 검증 (short 또는 long만 허용)
    valid_subtitle_length = subtitle_length if subtitle_length in ("short", "long") else "short"

    # generate_edit_pack 파싱 (문자열 → bool)
    logger.info(f"[DEBUG] generate_edit_pack raw value: {repr(generate_edit_pack)}")
    should_generate_edit_pack = generate_edit_pack and generate_edit_pack.lower() == "true"
    logger.info(f"[DEBUG] should_generate_edit_pack final value: {should_generate_edit_pack}")

    # video_tone 검증 (bright 또는 dark만 허용)
    valid_video_tone = video_tone if video_tone in ("bright", "dark") else "bright"

    # 배치 처리 또는 단일 처리
    if len(files) == 1:
        # 단일 파일: 직접 처리
        task = process_video_task.delay(
            audio_paths[0],
            church_id,
            video_ids[0],
            actual_pack_id,
            parsed_clip_ids,  # 선택된 클립 ID 리스트
            bgm_id,           # BGM ID
            parsed_bgm_volume, # BGM 볼륨
            generation_mode,  # 생성 방식
            valid_subtitle_length,  # 자막 길이
            should_generate_edit_pack,  # Edit Pack 생성 여부
            valid_video_tone  # v2.2: 영상 톤
        )
    else:
        # 다중 파일: 배치 처리
        task = batch_process_videos_task.delay(
            audio_paths,
            church_id,
            actual_pack_id,
            parsed_clip_ids,  # 선택된 클립 ID 리스트
            bgm_id,           # BGM ID
            parsed_bgm_volume, # BGM 볼륨
            generation_mode,  # 생성 방식
            valid_subtitle_length,  # 자막 길이
            should_generate_edit_pack,  # Edit Pack 생성 여부
            valid_video_tone  # v2.2: 영상 톤
        )

    return {
        "status": "queued",
        "task_id": task.id,
        "church_id": church_id,
        "pack_id": actual_pack_id,
        "files_count": len(files),
        "video_ids": video_ids,
        "message": f"{len(files)}개 영상 생성 작업이 큐에 추가되었습니다."
    }


@app.get("/api/videos/status/{task_id}")
async def get_video_status(task_id: str):
    """
    영상 생성 작업 상태 조회

    Args:
        task_id: Celery 작업 ID

    Returns:
        status, progress, result
    """
    task = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task.status,  # PENDING, PROCESSING, SUCCESS, FAILURE
    }

    if task.status == "PROCESSING":
        # 진행 상태 정보
        meta = task.info or {}
        response["progress"] = meta.get("progress", 0)
        response["step"] = meta.get("step", "처리 중...")

    elif task.status == "SUCCESS":
        # 완료된 결과
        response["progress"] = 100
        response["result"] = task.result

    elif task.status == "FAILURE":
        # 실패 정보
        response["progress"] = 0
        response["error"] = str(task.info) if task.info else "알 수 없는 오류"

    else:
        # PENDING
        response["progress"] = 0
        response["step"] = "작업 대기 중..."

    return response


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """
    영상 정보 조회

    Args:
        video_id: 영상 UUID

    Returns:
        video 정보
    """
    result = supabase.table("videos").select("*").eq("id", video_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    return result.data[0]


@app.get("/api/videos")
async def list_videos(
    church_id: str = Query(...),
    limit: int = Query(default=10, le=50),
    offset: int = Query(default=0)
):
    """
    교회별 영상 목록 조회

    Args:
        church_id: 교회 UUID
        limit: 페이지 크기 (최대 50)
        offset: 시작 위치

    Returns:
        videos 리스트
    """
    # schema.sql 기본 필드만 조회 (migration 미실행 대비)
    result = supabase.table("videos") \
        .select("id, title, status, duration, video_file_path, srt_file_path, created_at, completed_at, error_message, clips_used") \
        .eq("church_id", church_id) \
        .order("created_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    return {
        "videos": result.data,
        "count": len(result.data),
        "offset": offset,
        "limit": limit
    }


@app.get("/api/stats/{church_id}")
async def get_church_stats(church_id: str):
    """
    교회별 통계 조회
    
    Args:
        church_id: 교회 UUID
    
    Returns:
        - this_week_videos: 이번 주 생성된 영상 수
        - last_week_videos: 지난 주 생성된 영상 수
        - total_videos: 전체 영상 수
        - completed_videos: 완료된 영상 수
        - storage_used_bytes: 사용된 저장공간 (bytes)
        - storage_limit_bytes: 저장공간 제한 (bytes)
    """
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # 이번 주 시작일 (월요일)
    this_week_start = now - timedelta(days=now.weekday())
    this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 지난 주 시작일/종료일
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start
    
    try:
        # 전체 영상 조회 (저장공간 계산 위해)
        all_videos = supabase.table("videos") \
            .select("id, status, created_at, duration") \
            .eq("church_id", church_id) \
            .execute()
        
        videos = all_videos.data or []
        
        # 통계 계산
        total_videos = len(videos)
        completed_videos = len([v for v in videos if v.get("status") == "completed"])
        
        # 이번 주 영상 수
        this_week_videos = len([
            v for v in videos 
            if datetime.fromisoformat(v["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) >= this_week_start
        ])
        
        # 지난 주 영상 수
        last_week_videos = len([
            v for v in videos 
            if last_week_start <= datetime.fromisoformat(v["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) < last_week_end
        ])
        
        # 저장공간 계산 (평균 영상 크기 추정: 완료된 영상당 약 50MB)
        # 실제로는 R2에서 조회해야 하지만, 일단 추정치 사용
        avg_video_size_mb = 50  # 평균 영상 크기 (MB)
        storage_used_bytes = completed_videos * avg_video_size_mb * 1024 * 1024
        
        # 저장공간 제한 (기본 10GB, 추후 교회별 요금제에서 조회)
        storage_limit_bytes = 10 * 1024 * 1024 * 1024  # 10 GB
        
        # 크레딧 시스템 (기본값, 추후 교회별 설정에서 조회)
        credits_remaining = max(0, 30 - total_videos)  # 월 30개 제한 예시
        credits_reset_date = (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()[:10]
        
        return {
            "church_id": church_id,
            "this_week_videos": this_week_videos,
            "last_week_videos": last_week_videos,
            "total_videos": total_videos,
            "completed_videos": completed_videos,
            "storage_used_bytes": storage_used_bytes,
            "storage_limit_bytes": storage_limit_bytes,
            "storage_used_percent": round((storage_used_bytes / storage_limit_bytes) * 100, 1) if storage_limit_bytes > 0 else 0,
            "credits_remaining": credits_remaining,
            "credits_reset_date": credits_reset_date,
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, church_id: str = Query(...)):
    """
    영상 삭제 (soft delete는 아니고 완전 삭제)

    Args:
        video_id: 영상 UUID
        church_id: 교회 UUID (권한 확인용)
    """
    # 권한 확인
    video = supabase.table("videos") \
        .select("id, church_id, video_file_path") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # R2에서 파일 삭제 (TODO: 구현)
    # video_file_path = video.data[0].get("video_file_path")
    # if video_file_path:
    #     r2.delete_file(extract_key(video_file_path))

    # DB에서 삭제
    supabase.table("videos").delete().eq("id", video_id).execute()

    return {"status": "deleted", "video_id": video_id}


class DeleteVideosRequest(BaseModel):
    video_ids: list[str]
    church_id: str


@app.post("/api/videos/delete-batch")
async def delete_videos_batch(request: DeleteVideosRequest):
    """
    영상 일괄 삭제

    Args:
        video_ids: 삭제할 영상 UUID 리스트
        church_id: 교회 UUID (권한 확인용)
    """
    if not request.video_ids:
        raise HTTPException(status_code=400, detail="삭제할 영상을 선택해주세요.")

    # 권한 확인 - 모든 영상이 해당 교회 소속인지 확인
    videos = supabase.table("videos") \
        .select("id, church_id") \
        .in_("id", request.video_ids) \
        .execute()

    if not videos.data:
        raise HTTPException(status_code=404, detail="선택한 영상을 찾을 수 없습니다.")

    # 권한 확인 - 다른 교회 영상이 포함되어 있는지 확인
    unauthorized = [v for v in videos.data if v["church_id"] != request.church_id]
    if unauthorized:
        raise HTTPException(status_code=403, detail="삭제 권한이 없는 영상이 포함되어 있습니다.")

    # 일괄 삭제
    deleted_count = 0
    for video_id in request.video_ids:
        try:
            supabase.table("videos").delete().eq("id", video_id).execute()
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete video {video_id}: {e}")

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "total_requested": len(request.video_ids)
    }


@app.get("/api/videos/{video_id}/download")
async def download_video_file(
    video_id: str,
    file_type: str = Query(default="video", regex="^(video|srt|edit_pack)$")
):
    """
    영상/자막/편집파일 다운로드 프록시
    
    Args:
        video_id: 영상 UUID
        file_type: 'video', 'srt', 'edit_pack'
    """
    # 영상 정보 조회
    video = supabase.table("videos") \
        .select("id, title, video_file_path, srt_file_path, edit_pack_path") \
        .eq("id", video_id) \
        .execute()
    
    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
    
    video_data = video.data[0]
    
    if file_type == "video":
        file_url = video_data.get("video_file_path")
        content_type = "video/mp4"
        extension = "mp4"
    elif file_type == "srt":
        file_url = video_data.get("srt_file_path")
        content_type = "text/plain; charset=utf-8"
        extension = "srt"
    else:  # edit_pack
        file_url = video_data.get("edit_pack_path")
        content_type = "application/zip"
        extension = "zip"
    
    if not file_url:
        raise HTTPException(status_code=404, detail=f"{file_type} 파일이 없습니다.")
    
    # 파일명 생성 (한글 포함)
    title = video_data.get("title") or video_id
    # Windows에서 금지된 파일명 문자만 제거: \ / : * ? " < > |
    forbidden_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_title = "".join('_' if c in forbidden_chars else c for c in title)
    filename = f"{safe_title}.{extension}"

    # RFC 5987/RFC 8187 호환 인코딩 (한글 파일명 지원)
    from urllib.parse import quote
    # 1) filename: ASCII 전용 (구버전 브라우저용)
    ascii_filename = filename.encode('ascii', errors='ignore').decode('ascii') or "video.mp4"
    # 2) filename*: UTF-8 인코딩 (최신 브라우저용)
    encoded_filename = quote(filename.encode('utf-8'))
    
    try:
        # 외부 URL에서 파일 스트리밍
        async with httpx.AsyncClient() as client:
            response = await client.get(file_url, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="파일 다운로드 실패")
            
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={
                    # RFC 5987/RFC 8187: 양쪽 모두 제공 (브라우저 호환성)
                    "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                    "Content-Length": str(len(response.content))
                }
            )
    except httpx.RequestError as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=502, detail="파일 다운로드 중 오류가 발생했습니다.")


@app.get("/api/videos/{video_id}/stream")
async def stream_video(
    video_id: str,
    request: Request,
    range: str = Header(None)
):
    """
    영상 스트리밍 (Range Request 지원)

    브라우저 <video> 태그가 필요한 부분만 요청할 수 있도록 HTTP Range를 지원합니다.

    Args:
        video_id: 영상 UUID
        range: HTTP Range 헤더 (예: "bytes=0-1023")

    Returns:
        StreamingResponse with 206 Partial Content or 200 OK
    """
    # 영상 정보 조회
    video = supabase.table("videos") \
        .select("id, video_file_path") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    file_url = video.data[0].get("video_file_path")
    if not file_url:
        raise HTTPException(status_code=404, detail="영상 파일이 없습니다.")

    try:
        # HEAD 요청으로 파일 크기 확인
        async with httpx.AsyncClient(timeout=30.0) as client:
            head_response = await client.head(file_url, follow_redirects=True)
            file_size = int(head_response.headers.get("content-length", 0))

            if file_size == 0:
                raise HTTPException(status_code=502, detail="파일 크기를 확인할 수 없습니다.")

            # Range 요청 파싱
            start = 0
            end = file_size - 1

            if range:
                # "bytes=0-1023" 형식 파싱
                range_match = range.replace("bytes=", "").split("-")
                if len(range_match) == 2:
                    if range_match[0]:
                        start = int(range_match[0])
                    if range_match[1]:
                        end = int(range_match[1])

            # 범위 검증
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(
                    status_code=416,
                    detail="Requested Range Not Satisfiable",
                    headers={"Content-Range": f"bytes */{file_size}"}
                )

            # Range 헤더로 부분 요청
            headers = {"Range": f"bytes={start}-{end}"}
            response = await client.get(file_url, headers=headers, follow_redirects=True)

            if response.status_code not in [200, 206]:
                raise HTTPException(status_code=502, detail="파일 스트리밍 실패")

            # 청크 단위로 스트리밍 (메모리 효율성)
            async def stream_chunks():
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk

            # 206 Partial Content 또는 200 OK 응답
            status_code = 206 if range else 200
            content_length = end - start + 1

            response_headers = {
                "Content-Type": "video/mp4",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range",
                "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length",
                "Cache-Control": "public, max-age=3600",
            }

            if range:
                response_headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

            return StreamingResponse(
                stream_chunks(),
                status_code=status_code,
                headers=response_headers,
                media_type="video/mp4"
            )

    except httpx.RequestError as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=502, detail="스트리밍 중 오류가 발생했습니다.")


# ============================================
# 클립 관련 API
# ============================================

@app.get("/api/clips/packs")
async def list_clip_packs():
    """배경팩 목록 조회"""
    # 실제 테이블명: packs (clip_packs 아님)
    result = supabase.table("packs") \
        .select("id, name, description, is_free") \
        .execute()

    # 프론트엔드 호환성을 위해 필드 추가
    packs = []
    for pack in result.data:
        # 해당 팩의 활성 클립 수 조회
        clips_result = supabase.table("clips") \
            .select("id") \
            .eq("pack_id", pack["id"]) \
            .eq("is_active", True) \
            .execute()

        packs.append({
            **pack,
            "thumbnail_url": None,
            "clip_count": len(clips_result.data)
        })

    # DB에 팩이 없으면 클립 테이블에서 고유 pack_id 추출하여 동적 생성
    if not packs:
        clips_packs = supabase.table("clips") \
            .select("pack_id") \
            .eq("is_active", True) \
            .execute()

        unique_pack_ids = list(set(c["pack_id"] for c in clips_packs.data if c.get("pack_id")))

        for pack_id in unique_pack_ids:
            clips_count = supabase.table("clips") \
                .select("id") \
                .eq("pack_id", pack_id) \
                .eq("is_active", True) \
                .execute()

            packs.append({
                "id": pack_id,
                "name": pack_id.replace("-", " ").title(),
                "description": f"{pack_id} 배경 클립",
                "is_free": pack_id == "pack-free" or "free" in pack_id.lower(),
                "thumbnail_url": None,
                "clip_count": len(clips_count.data)
            })

    return {"packs": packs}


@app.get("/api/clips")
async def list_clips(
    pack_id: str = Query(default="pack-free"),
    category: str | None = Query(default=None)
):
    """특정 팩의 클립 목록 조회"""
    # 실제 테이블 컬럼: id, pack_id, file_path, category, duration, is_active, used_count, created_at
    query = supabase.table("clips") \
        .select("id, category, file_path, duration, pack_id") \
        .eq("pack_id", pack_id) \
        .eq("is_active", True)

    if category:
        query = query.eq("category", category)

    result = query.order("category").execute()

    # 프론트엔드 호환성을 위해 name, thumbnail_url 추가
    clips = []
    for clip in result.data:
        clips.append({
            **clip,
            "name": clip["category"].capitalize(),  # category를 name으로 사용
            "thumbnail_url": None  # 썸네일 없음
        })

    return {"clips": clips}


# ============================================
# BGM 관련 API
# ============================================

@app.get("/api/bgm")
async def list_bgms(category: str | None = Query(default=None)):
    """BGM 목록 조회"""
    query = supabase.table("bgms") \
        .select("id, name, category, file_path, duration, preview_url") \
        .eq("is_active", True)

    if category:
        query = query.eq("category", category)

    result = query.order("category").order("sort_order").execute()

    # R2 공개 URL 베이스
    r2_public_url = settings.R2_PUBLIC_URL or "https://pub-65fad94ee5424c55b0505378e2c1fbf1.r2.dev"

    # 상대 경로를 절대 URL로 변환
    bgms = []
    for bgm in result.data:
        file_path = bgm.get("file_path", "")

        # 이미 http로 시작하면 그대로, 아니면 R2 URL 추가
        if file_path and not file_path.startswith("http"):
            file_path = f"{r2_public_url}/{file_path}"

        # preview_url은 file_path와 동일하게 (별도 preview 파일 없음)
        bgms.append({
            **bgm,
            "file_path": file_path,
            "preview_url": file_path  # 전체 파일을 미리듣기로 사용
        })

    return {"bgms": bgms}


# ============================================
# 영상 편집 관련 API
# ============================================

@app.get("/api/videos/{video_id}/detail")
async def get_video_detail(video_id: str):
    """영상 상세 정보 조회 (자막 포함)"""
    result = supabase.table("videos") \
        .select("*") \
        .eq("id", video_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    video = result.data[0]

    # clips_used 파싱 (JSON 문자열인 경우)
    if isinstance(video.get("clips_used"), str):
        import json
        try:
            video["clips_used"] = json.loads(video["clips_used"])
        except:
            video["clips_used"] = []

    return video


class VideoUpdateRequest(BaseModel):
    """영상 정보 수정 요청"""
    title: str | None = None
    church_id: str


@app.patch("/api/videos/{video_id}")
async def update_video(
    video_id: str,
    request: VideoUpdateRequest
):
    """영상 정보 수정 (제목 등)"""
    title = request.title
    church_id = request.church_id
    # 권한 확인
    video = supabase.table("videos") \
        .select("id, church_id") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 업데이트
    update_data = {}
    if title is not None:
        update_data["title"] = title

    if update_data:
        result = supabase.table("videos") \
            .update(update_data) \
            .eq("id", video_id) \
            .execute()
        return result.data[0]

    return video.data[0]


class ThumbnailLayoutRequest(BaseModel):
    """썸네일 레이아웃 저장 요청"""
    church_id: str
    text_boxes: list[dict]
    background_image_url: str | None = None
    intro_settings: dict | None = None


@app.put("/api/videos/{video_id}/thumbnail-layout")
async def save_thumbnail_layout(
    video_id: str,
    request: ThumbnailLayoutRequest
):
    """썸네일 레이아웃 저장 (JSON으로 DB에 저장)"""
    # 권한 확인
    video = supabase.table("videos") \
        .select("id, church_id") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != request.church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 레이아웃 JSON 저장
    layout_data = {
        "text_boxes": request.text_boxes,
        "background_image_url": request.background_image_url,
        "intro_settings": request.intro_settings,
    }

    result = supabase.table("videos") \
        .update({"thumbnail_layout": layout_data}) \
        .eq("id", video_id) \
        .execute()

    logger.info(f"썸네일 레이아웃 저장 완료: video_id={video_id}")

    return {
        "success": True,
        "video_id": video_id,
        "layout": layout_data
    }


@app.get("/api/videos/{video_id}/thumbnail-layout")
async def get_thumbnail_layout(video_id: str):
    """저장된 썸네일 레이아웃 조회"""
    video = supabase.table("videos") \
        .select("id, thumbnail_layout") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    return {
        "video_id": video_id,
        "layout": video.data[0].get("thumbnail_layout")
    }


@app.get("/api/videos/{video_id}/subtitles")
async def get_subtitles(video_id: str):
    """자막 조회 (SRT 파싱)"""
    video = supabase.table("videos") \
        .select("srt_file_path") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    srt_path = video.data[0].get("srt_file_path")
    if not srt_path:
        return {"subtitles": []}

    try:
        # R2에서 SRT 파일 다운로드
        srt_content = r2.download_text(srt_path)
        if not srt_content:
            return {"subtitles": []}

        # SRT 파싱
        subtitles = parse_srt(srt_content)
        return {"subtitles": subtitles}

    except Exception as e:
        logger.error(f"SRT 파싱 실패: {e}")
        return {"subtitles": []}


@app.put("/api/videos/{video_id}/subtitles")
async def update_subtitles(
    video_id: str,
    subtitles: list[dict] = [],
    church_id: str = Query(...)
):
    """자막 수정"""
    # 권한 확인
    video = supabase.table("videos") \
        .select("id, church_id") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 자막 유효성 검증
    is_valid, error_msg = validate_subtitles(subtitles)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # SRT 파일 생성
        srt_content = generate_srt(subtitles)

        # R2에 업로드
        srt_key = f"subtitles/{video_id}/subtitles.srt"
        srt_url = r2.upload_text(srt_content, srt_key, content_type="text/plain")

        # DB 업데이트
        supabase.table("videos") \
            .update({"srt_file_path": srt_url}) \
            .eq("id", video_id) \
            .execute()

        return {"success": True, "srt_url": srt_url}

    except Exception as e:
        logger.error(f"자막 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="자막 저장에 실패했습니다.")


# ============================================
# 썸네일 관련 API
# ============================================

@app.post("/api/videos/{video_id}/thumbnail")
async def generate_thumbnail(
    video_id: str,
    timestamp: float = Query(default=5.0, ge=0),
    church_id: str = Query(...)
):
    """영상에서 썸네일 추출"""
    video = supabase.table("videos") \
        .select("id, church_id, video_file_path") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    video_url = video.data[0].get("video_file_path")
    if not video_url:
        raise HTTPException(status_code=400, detail="영상 파일이 없습니다.")

    try:
        # FFmpeg로 썸네일 추출
        thumbnail_bytes = extract_thumbnail_from_url(video_url, timestamp)
        if not thumbnail_bytes:
            raise HTTPException(status_code=500, detail="썸네일 추출에 실패했습니다.")

        # R2에 업로드
        thumbnail_key = f"thumbnails/{video_id}/thumb_{int(timestamp)}.jpg"
        thumbnail_url = r2.upload_bytes(thumbnail_bytes, thumbnail_key, content_type="image/jpeg")

        # DB 업데이트
        supabase.table("videos") \
            .update({"thumbnail_url": thumbnail_url}) \
            .eq("id", video_id) \
            .execute()

        return {"thumbnail_url": thumbnail_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"썸네일 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="썸네일 생성에 실패했습니다.")


@app.post("/api/videos/{video_id}/thumbnail/upload")
async def upload_thumbnail(
    video_id: str,
    file: UploadFile = File(...),
    church_id: str = Form(...)
):
    """커스텀 썸네일 업로드"""
    video = supabase.table("videos") \
        .select("id, church_id") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    try:
        # 파일 읽기
        file_content = await file.read()

        # 이미지 유효성 검증
        is_valid, result = validate_image_file(file_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=result)

        # R2에 업로드
        file_ext = result  # jpeg, png, gif, webp
        thumbnail_key = f"thumbnails/{video_id}/custom.{file_ext}"
        thumbnail_url = r2.upload_bytes(file_content, thumbnail_key, content_type=f"image/{file_ext}")

        # DB 업데이트
        supabase.table("videos") \
            .update({"thumbnail_url": thumbnail_url}) \
            .eq("id", video_id) \
            .execute()

        return {"thumbnail_url": thumbnail_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"썸네일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="썸네일 업로드에 실패했습니다.")


# ============================================
# 썸네일 컨셉 API
# ============================================

@app.get("/api/thumbnail/categories")
async def list_thumbnail_categories():
    """
    썸네일 카테고리 목록 조회

    Returns:
        categories: 활성화된 카테고리 리스트 (정렬순)
    """
    result = supabase.table("thumbnail_categories") \
        .select("id, name, description, icon, sort_order") \
        .eq("is_active", True) \
        .order("sort_order") \
        .execute()

    return {"categories": result.data}


@app.get("/api/thumbnail/templates")
async def list_thumbnail_templates(
    category_id: str | None = Query(default=None, description="카테고리 ID로 필터링")
):
    """
    썸네일 템플릿 목록 조회

    Args:
        category_id: 특정 카테고리만 조회 (옵션)

    Returns:
        templates: 템플릿 리스트
    """
    query = supabase.table("thumbnail_templates") \
        .select("id, category_id, name, image_url, text_color, text_position, overlay_opacity, used_count") \
        .eq("is_active", True)

    if category_id:
        query = query.eq("category_id", category_id)

    result = query.order("used_count", desc=True).execute()

    return {"templates": result.data}


@app.get("/api/thumbnail/templates/{template_id}")
async def get_thumbnail_template(template_id: str):
    """
    특정 템플릿 상세 조회

    Args:
        template_id: 템플릿 ID

    Returns:
        템플릿 정보
    """
    result = supabase.table("thumbnail_templates") \
        .select("*") \
        .eq("id", template_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    return result.data[0]


@app.post("/api/videos/{video_id}/thumbnail/generate-from-template")
async def generate_thumbnail_from_template(
    video_id: str,
    template_id: str = Form(...),
    title: str = Form(...),
    church_id: str = Form(...)
):
    """
    템플릿 기반 썸네일 생성

    Args:
        video_id: 영상 UUID
        template_id: 사용할 템플릿 ID
        title: 썸네일에 표시할 제목
        church_id: 교회 UUID (권한 확인용)

    Returns:
        thumbnail_url: 생성된 썸네일 URL
    """
    # 권한 확인
    video = supabase.table("videos") \
        .select("id, church_id") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 템플릿 조회
    template = supabase.table("thumbnail_templates") \
        .select("*") \
        .eq("id", template_id) \
        .execute()

    if not template.data:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    template_data = template.data[0]

    # 교회 설정 조회 (옵션)
    church_settings = supabase.table("church_thumbnail_settings") \
        .select("*") \
        .eq("church_id", church_id) \
        .execute()

    church_settings_data = church_settings.data[0] if church_settings.data else None

    try:
        # R2에서 배경 이미지 URL 구성
        background_url = template_data["image_url"]
        if not background_url.startswith("http"):
            # 상대 경로인 경우 R2 Public URL 추가
            if settings.R2_PUBLIC_URL:
                background_url = f"{settings.R2_PUBLIC_URL}/{background_url}"

        # 썸네일 생성
        thumbnail_path = thumbnail_generator.generate_from_template(
            template=template_data,
            title=title,
            church_settings=church_settings_data
        )

        # R2에 업로드
        thumbnail_key = f"thumbnails/{video_id}/concept_{template_id}.jpg"
        thumbnail_url = r2.upload_file(
            file_path=thumbnail_path,
            folder="thumbnails",
            content_type="image/jpeg"
        )

        # 임시 파일 삭제
        import os
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        # DB 업데이트
        supabase.table("videos") \
            .update({
                "thumbnail_url": thumbnail_url,
                "thumbnail_template_id": template_id,
                "thumbnail_title": title
            }) \
            .eq("id", video_id) \
            .execute()

        # 템플릿 사용 횟수 증가
        supabase.table("thumbnail_templates") \
            .update({"used_count": template_data["used_count"] + 1}) \
            .eq("id", template_id) \
            .execute()

        return {
            "thumbnail_url": thumbnail_url,
            "template_id": template_id,
            "title": title
        }

    except Exception as e:
        logger.error(f"썸네일 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"썸네일 생성에 실패했습니다: {str(e)}")


class TextBoxPosition(BaseModel):
    """텍스트 박스 위치 및 스타일"""
    id: str  # main, sub, date, verse
    text: str
    x: float  # 0-100 (퍼센트)
    y: float  # 0-100 (퍼센트)
    fontSize: int
    fontFamily: str = "Nanum Gothic"
    color: str = "#FFFFFF"
    visible: bool = True


class QTThumbnailRequest(BaseModel):
    """QT 썸네일 생성 요청"""
    background_image_url: str
    text_boxes: list[TextBoxPosition]
    overlay_opacity: float = 0.3
    output_width: int = 1920
    output_height: int = 1080
    video_id: str | None = None  # 썸네일을 비디오에 저장할 경우


class IntroSettings(BaseModel):
    """인트로 설정"""
    useAsIntro: bool
    introDuration: int
    separateIntro: bool
    separateIntroImageUrl: str | None = None


class SaveThumbnailLayoutRequest(BaseModel):
    """썸네일 레이아웃 저장 요청"""
    church_id: str
    text_boxes: list[TextBoxPosition]
    background_image_url: str | None = None
    intro_settings: IntroSettings | None = None


@app.post("/api/thumbnail/generate-qt")
async def generate_qt_thumbnail_custom(request: QTThumbnailRequest):
    """
    커스텀 위치로 QT 썸네일 생성

    프론트엔드의 드래그 앤 드롭 에디터에서 설정한 위치/크기/색상으로
    썸네일을 생성합니다.

    Args:
        request: 배경 이미지, 텍스트 박스들 (위치/스타일 포함)

    Returns:
        thumbnail_url: 생성된 썸네일 URL (base64 또는 임시 URL)
    """
    try:
        import tempfile
        import httpx
        import base64
        import subprocess
        import os

        width, height = request.output_width, request.output_height
        bg_url = request.background_image_url

        # URL 공백 인코딩 (공백이 있는 파일명 처리)
        # 이미 인코딩된 경우 이중 인코딩 방지
        from urllib.parse import quote, unquote, urlparse, urlunparse
        parsed = urlparse(bg_url)
        # 먼저 디코딩 후 다시 인코딩 (이중 인코딩 방지)
        decoded_path = unquote(parsed.path)
        encoded_path = quote(decoded_path, safe='/()')  # 괄호는 인코딩 안 함
        bg_url = urlunparse(parsed._replace(path=encoded_path))
        logger.info(f"배경 URL: {bg_url}")

        # URL이 비디오인지 이미지인지 확인
        is_video = any(bg_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.webm'])

        # 배경 파일 다운로드
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(bg_url, follow_redirects=True)
            if response.status_code != 200:
                logger.error(f"배경 다운로드 실패: status={response.status_code}, url={bg_url}")
                raise HTTPException(status_code=400, detail=f"배경 이미지를 다운로드할 수 없습니다. (status: {response.status_code})")

            # 임시 파일로 저장
            suffix = ".mp4" if is_video else ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                downloaded_path = tmp.name

        # 비디오인 경우 첫 프레임 추출
        if is_video:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                bg_path = tmp.name

            extract_cmd = [
                "ffmpeg", "-y",
                "-i", downloaded_path,
                "-vframes", "1",
                "-q:v", "2",
                bg_path
            ]
            extract_result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=30)

            if extract_result.returncode != 0:
                logger.error(f"비디오 프레임 추출 실패: {extract_result.stderr}")
                raise HTTPException(status_code=500, detail="비디오에서 프레임을 추출할 수 없습니다.")

            os.remove(downloaded_path)
        else:
            bg_path = downloaded_path
        
        # FFmpeg 필터 구성 (cover 방식 - 프론트엔드 Canvas와 동일)
        # force_original_aspect_ratio=increase + crop으로 화면을 완전히 채움
        filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        ]
        
        # 어두운 오버레이
        if request.overlay_opacity > 0:
            filters.append(
                f"drawbox=x=0:y=0:w={width}:h={height}:"
                f"color=black@{request.overlay_opacity}:t=fill"
            )
        
        # 텍스트 박스들 추가
        # NanumGothicBold 폰트 사용 - Canvas 프론트엔드와 동일
        import platform
        if platform.system() == "Windows":
            font_path = r"C\:/Windows/Fonts/NanumGothicBold.ttf"
        else:
            font_path = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"  # Docker

        # 텍스트 파일들을 저장할 리스트 (나중에 정리용)
        text_files_to_cleanup = []

        for box in request.text_boxes:
            if not box.visible or not box.text.strip():
                continue

            # 퍼센트 → 픽셀 변환
            x_pos = int((box.x / 100) * width)
            y_pos = int((box.y / 100) * height)

            # 텍스트를 파일로 저장 (UTF-8 인코딩 보장)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_file:
                txt_file.write(box.text)
                text_file_path = txt_file.name
                text_files_to_cleanup.append(text_file_path)

            # Windows 경로를 FFmpeg 형식으로 변환 (백슬래시→슬래시, 콜론 이스케이프)
            ffmpeg_text_path = text_file_path.replace("\\", "/").replace(":", r"\:")

            # 색상 변환
            ffmpeg_color = box.color.replace("#", "0x")

            # 폰트 크기 (프론트엔드 값 그대로 사용 - 생성창과 동일하게)
            scaled_fontsize = int(box.fontSize)
            scaled_fontsize = max(scaled_fontsize, 20)  # 최소 크기

            # drawtext 필터 (textfile 사용으로 UTF-8 한글 지원)
            filters.append(
                f"drawtext=textfile='{ffmpeg_text_path}':"
                f"fontfile='{font_path}':"
                f"fontsize={scaled_fontsize}:"
                f"fontcolor={ffmpeg_color}:"
                f"borderw=2:bordercolor=black:"
                f"shadowcolor=black@0.5:shadowx=2:shadowy=2:"
                f"x={x_pos}-text_w/2:y={y_pos}-text_h/2"
            )
        
        # 출력 파일
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            output_path = tmp.name
        
        # FFmpeg 실행
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", ",".join(filters),
            "-q:v", "2",
            output_path
        ]
        
        logger.info(f"FFmpeg 명령: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if process.returncode != 0:
            logger.error(f"FFmpeg stderr: {process.stderr}")
            logger.error(f"FFmpeg stdout: {process.stdout}")
            raise HTTPException(status_code=500, detail=f"썸네일 생성 실패: {process.stderr[:200]}")
        
        # 결과를 base64로 반환
        with open(output_path, "rb") as f:
            thumbnail_base64 = base64.b64encode(f.read()).decode()

        thumbnail_url = f"data:image/jpeg;base64,{thumbnail_base64}"

        # video_id가 있으면 DB에 저장
        if request.video_id:
            try:
                supabase.table("videos").update({
                    "thumbnail_url": thumbnail_url
                }).eq("id", request.video_id).execute()
                logger.info(f"썸네일 저장 완료: video_id={request.video_id}")
            except Exception as db_error:
                logger.warning(f"썸네일 DB 저장 실패 (무시): {db_error}")

        # 임시 파일 정리
        os.remove(bg_path)
        os.remove(output_path)
        for txt_file in text_files_to_cleanup:
            try:
                os.remove(txt_file)
            except:
                pass

        return {
            "thumbnail_url": thumbnail_url,
            "width": width,
            "height": height,
            "saved_to_video": request.video_id is not None
        }
        
    except Exception as e:
        logger.exception(f"QT 썸네일 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"썸네일 생성에 실패했습니다: {str(e)}")


class CanvasThumbnailRequest(BaseModel):
    """Canvas에서 직접 생성한 썸네일 저장 요청"""
    image_data: str  # data:image/jpeg;base64,... 형식


@app.post("/api/videos/{video_id}/thumbnail/save-canvas")
async def save_canvas_thumbnail(video_id: str, request: CanvasThumbnailRequest):
    """
    Canvas에서 직접 생성한 썸네일 이미지 저장

    프론트엔드 Canvas에서 toDataURL()로 생성한 이미지를 그대로 저장합니다.
    이렇게 하면 미리보기와 최종 결과가 100% 동일합니다.
    """
    import base64

    try:
        # base64 데이터 추출
        if request.image_data.startswith('data:'):
            # data:image/jpeg;base64,xxxx 형식에서 base64 부분만 추출
            header, base64_data = request.image_data.split(',', 1)
        else:
            base64_data = request.image_data

        # base64 디코딩
        image_bytes = base64.b64decode(base64_data)

        # 비디오 정보 조회 (파일명 생성용)
        video_result = supabase.table("videos").select("title").eq("id", video_id).execute()
        video_title = video_result.data[0]["title"] if video_result.data else "thumbnail"

        # 파일명 생성 (한글 제거, 특수문자 제거)
        import re
        safe_title = re.sub(r'[^\w\s-]', '', video_title)[:30]
        filename = f"thumbnails/{video_id}_{safe_title}.jpg"

        # R2에 업로드 (전역 r2 인스턴스 사용)
        thumbnail_url = r2.upload_bytes(image_bytes, filename, content_type="image/jpeg")

        logger.info(f"Canvas 썸네일 R2 업로드 완료: {thumbnail_url}")

        # DB 업데이트
        supabase.table("videos").update({
            "thumbnail_url": thumbnail_url
        }).eq("id", video_id).execute()

        logger.info(f"Canvas 썸네일 DB 저장 완료: video_id={video_id}")

        return {
            "thumbnail_url": thumbnail_url,
            "video_id": video_id,
            "message": "Canvas 썸네일이 저장되었습니다."
        }

    except Exception as e:
        logger.exception(f"Canvas 썸네일 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"썸네일 저장에 실패했습니다: {str(e)}")


@app.get("/api/churches/{church_id}/thumbnail-settings")
async def get_church_thumbnail_settings(church_id: str):
    """
    교회별 썸네일 설정 조회

    Args:
        church_id: 교회 UUID

    Returns:
        교회 썸네일 설정 (없으면 기본값)
    """
    result = supabase.table("church_thumbnail_settings") \
        .select("*") \
        .eq("church_id", church_id) \
        .execute()

    if result.data:
        return result.data[0]

    # 기본 설정 반환
    return {
        "church_id": church_id,
        "default_category_id": None,
        "custom_font": None,
        "custom_text_color": None,
        "logo_url": None,
        "logo_position": "bottom-right"
    }


@app.put("/api/churches/{church_id}/thumbnail-settings")
async def update_church_thumbnail_settings(
    church_id: str,
    default_category_id: str | None = Form(default=None),
    custom_text_color: str | None = Form(default=None),
    logo_position: str | None = Form(default="bottom-right")
):
    """
    교회별 썸네일 설정 업데이트

    Args:
        church_id: 교회 UUID
        default_category_id: 기본 카테고리
        custom_text_color: 커스텀 텍스트 색상
        logo_position: 로고 위치

    Returns:
        업데이트된 설정
    """
    update_data = {
        "church_id": church_id,
        "default_category_id": default_category_id,
        "custom_text_color": custom_text_color,
        "logo_position": logo_position,
        "updated_at": "now()"
    }

    # upsert (있으면 업데이트, 없으면 생성)
    result = supabase.table("church_thumbnail_settings") \
        .upsert(update_data, on_conflict="church_id") \
        .execute()

    return result.data[0] if result.data else update_data


@app.post("/api/churches/{church_id}/thumbnail-settings/logo")
async def upload_church_logo(
    church_id: str,
    file: UploadFile = File(...)
):
    """
    교회 로고 업로드

    Args:
        church_id: 교회 UUID
        file: 로고 이미지 파일

    Returns:
        logo_url: 업로드된 로고 URL
    """
    try:
        # 파일 읽기
        file_content = await file.read()

        # 이미지 유효성 검증
        is_valid, result = validate_image_file(file_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=result)

        # R2에 업로드
        file_ext = result
        logo_key = f"logos/{church_id}/logo.{file_ext}"
        logo_url = r2.upload_bytes(file_content, logo_key, content_type=f"image/{file_ext}")

        # DB 업데이트
        supabase.table("church_thumbnail_settings") \
            .upsert({
                "church_id": church_id,
                "logo_url": logo_url,
                "updated_at": "now()"
            }, on_conflict="church_id") \
            .execute()

        return {"logo_url": logo_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로고 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="로고 업로드에 실패했습니다.")


@app.put("/api/videos/{video_id}/thumbnail-layout")
async def save_thumbnail_layout_endpoint(
    video_id: str,
    request: SaveThumbnailLayoutRequest
):
    """
    썸네일 레이아웃 저장
    """
    try:
        # Pydantic 모델을 dict로 변환 (JSONB 저장을 위해)
        layout_data = request.dict()

        # 저장 데이터 로깅 (디버깅용)
        logger.info(f"[썸네일 저장] video_id={video_id}")
        logger.info(f"[썸네일 저장] intro_settings={layout_data.get('intro_settings')}")
        logger.info(f"[썸네일 저장] textBoxes 개수={len(layout_data.get('text_boxes', []))}")

        result = supabase.table("videos").update({
            "thumbnail_layout": layout_data,
            "updated_at": "now()"
        }).eq("id", video_id).execute()

        # 저장 결과 로깅
        logger.info(f"[썸네일 저장] Supabase 응답: {result.data}")

        return {"success": True, "video_id": video_id, "layout": layout_data}
        
    except Exception as e:
        logger.exception(f"썸네일 레이아웃 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="레이아웃 저장 실패")


@app.get("/api/videos/{video_id}/thumbnail-layout")
async def get_thumbnail_layout_endpoint(video_id: str):
    """
    썸네일 레이아웃 조회
    """
    try:
        result = supabase.table("videos") \
            .select("id, thumbnail_layout") \
            .eq("id", video_id) \
            .execute()
            
        if not result.data:
            raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
            
        layout = result.data[0].get("thumbnail_layout")
        return {"video_id": video_id, "layout": layout}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"썸네일 레이아웃 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="레이아웃 조회 실패")


# ============================================
# 구독 시스템 API
# ============================================

from app.services.subscription_service import get_subscription_service
from app.services.portone_service import get_portone_service


@app.get("/api/subscription/status")
async def get_subscription_status(church_id: str = Query(...)):
    """구독 상태 조회"""
    try:
        subscription_service = get_subscription_service()
        subscription = subscription_service.get_subscription(church_id)
        return subscription
    except Exception as e:
        logger.error(f"구독 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription/usage")
async def get_subscription_usage(church_id: str = Query(...)):
    """월간 사용량 조회"""
    try:
        subscription_service = get_subscription_service()
        usage = subscription_service.get_monthly_usage(church_id)
        return usage
    except Exception as e:
        logger.error(f"사용량 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SubscriptionActivateRequest(BaseModel):
    """구독 활성화 요청"""
    billing_key: str
    tier: str = "basic"
    church_id: str


@app.post("/api/subscription/activate")
async def activate_subscription(request: SubscriptionActivateRequest):
    """구독 활성화 (빌링키 저장 + 첫 결제 실행)"""
    try:
        portone_service = get_portone_service()
        tier_price = 30000 if request.tier == "basic" else 50000
        
        # 첫 결제 실행
        payment_result = await portone_service.charge_billing_key(
            billing_key=request.billing_key,
            amount=tier_price,
            order_name=f"QT Video SaaS {request.tier} 플랜",
            customer_id=request.church_id,
        )
        
        if not payment_result["success"]:
            raise HTTPException(status_code=400, detail=payment_result.get("error", "결제 실패"))
        
        # 구독 업그레이드
        subscription_service = get_subscription_service()
        result = subscription_service.upgrade_subscription(
            church_id=request.church_id,
            tier=request.tier,
            billing_key=request.billing_key
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"구독 활성화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SubscriptionCancelRequest(BaseModel):
    """구독 취소 요청"""
    church_id: str


@app.delete("/api/subscription/cancel")
async def cancel_subscription(request: SubscriptionCancelRequest):
    """구독 취소"""
    try:
        subscription_service = get_subscription_service()
        result = subscription_service.cancel_subscription(request.church_id)
        return result
    except Exception as e:
        logger.error(f"구독 취소 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription/payments")
async def get_payment_history(church_id: str = Query(...), limit: int = Query(default=10)):
    """결제 내역 조회"""
    try:
        portone_service = get_portone_service()
        payments = portone_service.get_payment_history(church_id, limit)
        return payments
    except Exception as e:
        logger.error(f"결제 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhook/portone")
async def portone_webhook(request: Request):
    """포트원 웹훅 처리"""
    try:
        body = await request.json()
        logger.info(f"포트원 웹훅 수신: {body}")
        # TODO: 웹훅 검증 및 처리
        return {"status": "received"}
    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 영상 재생성 API
# ============================================

class RegenerateRequest(BaseModel):
    """영상 재생성 요청"""
    church_id: str
    clip_ids: list[str] | None = None
    bgm_id: str | None = None
    bgm_volume: float | None = 0.12
    canvas_image_data: str | None = None  # Canvas에서 export한 base64 이미지 (data:image/jpeg;base64,...)


@app.post("/api/videos/{video_id}/regenerate")
async def regenerate_video(
    video_id: str,
    request: RegenerateRequest
):
    """영상 재생성 (설정 변경 후)"""
    video = supabase.table("videos") \
        .select("id, church_id, audio_file_path") \
        .eq("id", video_id) \
        .execute()

    if not video.data:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if video.data[0]["church_id"] != request.church_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 상태를 processing으로 업데이트 (UI에서 "처리중" 표시)
    supabase.table("videos") \
        .update({"status": "processing"}) \
        .eq("id", video_id) \
        .execute()

    # Celery 작업 큐에 추가
    task = regenerate_video_task.delay(
        video_id=video_id,
        church_id=request.church_id,
        clip_ids=request.clip_ids,
        bgm_id=request.bgm_id,
        bgm_volume=request.bgm_volume or 0.12,
        canvas_image_data=request.canvas_image_data  # Canvas에서 export한 이미지 (있으면 FFmpeg 썸네일 생성 스킵)
    )

    return {"task_id": str(task.id), "status": "processing"}


# ============================================
# 이미지 프록시 API (CORS 우회)
# ============================================

@app.get("/api/proxy/image")
async def proxy_image(url: str = Query(..., description="이미지 URL")):
    """외부 이미지를 프록시하여 CORS 문제 해결"""
    try:
        # URL 검증 (R2 또는 허용된 도메인만)
        allowed_domains = [
            "pub-65fad94ee5424c55b0505378e2c1fbf1.r2.dev",
            "r2.dev",
            settings.R2_PUBLIC_URL.replace("https://", "").replace("http://", "") if settings.R2_PUBLIC_URL else ""
        ]

        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not any(domain in parsed.netloc for domain in allowed_domains if domain):
            raise HTTPException(status_code=403, detail="허용되지 않은 도메인입니다")

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            # Content-Type 가져오기
            content_type = response.headers.get("content-type", "image/jpeg")

            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # 1일 캐시
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except httpx.HTTPError as e:
        logger.error(f"이미지 프록시 실패: {e}")
        raise HTTPException(status_code=502, detail="이미지를 가져올 수 없습니다")
    except Exception as e:
        logger.error(f"이미지 프록시 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
