"""
인증 API 라우터
"""
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr

from app.services.auth_service import (
    AuthResult,
    AuthService,
    UserProfile,
    get_auth_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ===================
# Pydantic 모델
# ===================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    church_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    church_id: str | None = None


class SetChurchRequest(BaseModel):
    church_id: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AuthResponse(BaseModel):
    success: bool
    message: str | None = None
    user: UserProfile | None = None
    access_token: str | None = None
    refresh_token: str | None = None


# ===================
# 의존성
# ===================

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserProfile:
    """
    현재 로그인한 사용자 조회 (의존성)

    Header: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    # Bearer 토큰 추출
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="잘못된 인증 형식입니다.")

    token = parts[1]

    # 토큰 검증
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    return user


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserProfile | None:
    """선택적 인증 (로그인 안 해도 됨)"""
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, auth_service)
    except HTTPException:
        return None


# ===================
# API 엔드포인트
# ===================

@router.post("/signup", response_model=AuthResponse)
async def signup(
    request: SignupRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    회원가입

    Args:
        email: 이메일
        password: 비밀번호 (6자 이상)
        name: 이름 (옵션)
        church_id: 교회 ID (옵션)

    Returns:
        인증 정보 및 토큰
    """
    result = await auth_service.signup(
        email=request.email,
        password=request.password,
        name=request.name,
        church_id=request.church_id
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return AuthResponse(
        success=True,
        message="회원가입이 완료되었습니다.",
        user=result.user,
        access_token=result.access_token,
        refresh_token=result.refresh_token
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    로그인

    Args:
        email: 이메일
        password: 비밀번호

    Returns:
        인증 정보 및 토큰
    """
    result = await auth_service.login(
        email=request.email,
        password=request.password
    )

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return AuthResponse(
        success=True,
        message="로그인되었습니다.",
        user=result.user,
        access_token=result.access_token,
        refresh_token=result.refresh_token
    )


@router.post("/logout")
async def logout(
    current_user: UserProfile = Depends(get_current_user),
    authorization: Annotated[str | None, Header()] = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """로그아웃"""
    token = authorization.split()[1] if authorization else ""
    await auth_service.logout(token)
    return {"success": True, "message": "로그아웃되었습니다."}


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """
    현재 사용자 정보 조회

    Header: Authorization: Bearer <token>
    """
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_me(
    request: UpdateProfileRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    현재 사용자 프로필 수정

    Args:
        name: 이름
        church_id: 교회 ID
    """
    updated = await auth_service.update_profile(
        user_id=current_user.id,
        name=request.name,
        church_id=request.church_id
    )

    if not updated:
        raise HTTPException(status_code=500, detail="프로필 수정에 실패했습니다.")

    return updated


@router.post("/set-church")
async def set_church(
    request: SetChurchRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    교회 배정

    처음 가입 후 교회를 선택할 때 사용합니다.
    """
    success = await auth_service.set_user_church(
        user_id=current_user.id,
        church_id=request.church_id
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="교회 배정에 실패했습니다. 교회 ID를 확인해주세요."
        )

    return {"success": True, "church_id": request.church_id}


@router.get("/churches")
async def list_churches(
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    가입 가능한 교회 목록

    회원가입 시 교회 선택에 사용합니다.
    """
    supabase = auth_service.supabase
    result = supabase.table("churches").select("id, name").execute()

    return {
        "churches": result.data or []
    }


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    현재 사용자 프로필 수정 (별칭 경로)

    Args:
        name: 이름
        church_id: 교회 ID
    """
    updated = await auth_service.update_profile(
        user_id=current_user.id,
        name=request.name,
        church_id=request.church_id
    )

    if not updated:
        raise HTTPException(status_code=500, detail="프로필 수정에 실패했습니다.")

    return updated


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserProfile = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    비밀번호 변경

    Args:
        current_password: 현재 비밀번호
        new_password: 새 비밀번호 (6자 이상)
    """
    # 비밀번호 유효성 검사: 8자 이상, 문자+숫자+기호 포함
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다.")

    has_letter = bool(re.search(r'[a-zA-Z]', request.new_password))
    has_number = bool(re.search(r'[0-9]', request.new_password))
    has_symbol = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', request.new_password))

    if not (has_letter and has_number and has_symbol):
        raise HTTPException(status_code=400, detail="비밀번호는 문자, 숫자, 기호를 모두 포함해야 합니다.")

    success = await auth_service.change_password(
        user_id=current_user.id,
        email=current_user.email,
        current_password=request.current_password,
        new_password=request.new_password
    )

    if not success:
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")

    return {"success": True, "message": "비밀번호가 변경되었습니다."}
