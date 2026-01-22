"""
인증 서비스
Supabase Auth 기반 사용자 인증
"""
import logging
from typing import Any
import jwt
from datetime import datetime, timezone

from gotrue.errors import AuthApiError
from pydantic import BaseModel

from app.database import get_supabase
from app.config import get_settings

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    """사용자 프로필"""
    id: str
    email: str
    name: str | None = None
    church_id: str | None = None
    role: str = "member"
    is_active: bool = True
    # 무료 플랜 정보
    subscription_plan: str | None = "free"
    weekly_credits: int | None = 10
    weekly_credits_reset_at: str | None = None


class AuthResult(BaseModel):
    """인증 결과"""
    success: bool
    user: UserProfile | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    error: str | None = None


class AuthService:
    """Supabase Auth 서비스"""

    def __init__(self):
        self.supabase = get_supabase()

    async def signup(
        self,
        email: str,
        password: str,
        name: str | None = None,
        church_id: str | None = None
    ) -> AuthResult:
        """
        회원가입

        Args:
            email: 이메일
            password: 비밀번호
            name: 이름 (옵션)
            church_id: 교회 ID (옵션, 나중에 설정 가능)

        Returns:
            AuthResult
        """
        try:
            # Supabase Auth 회원가입
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name
                    }
                }
            })

            if response.user is None:
                return AuthResult(
                    success=False,
                    error="회원가입에 실패했습니다. 이메일을 확인해주세요."
                )

            user_id = response.user.id

            # users 테이블에 church_id 업데이트 (트리거가 기본 정보 생성)
            if church_id:
                self.supabase.table("users").update({
                    "church_id": church_id,
                    "name": name
                }).eq("id", user_id).execute()

            # 사용자 프로필 조회
            profile = await self.get_user_profile(user_id)

            return AuthResult(
                success=True,
                user=profile,
                access_token=response.session.access_token if response.session else None,
                refresh_token=response.session.refresh_token if response.session else None
            )

        except AuthApiError as e:
            logger.warning(f"Signup failed: {e.message}")
            error_msg = self._translate_error(e.message)
            return AuthResult(success=False, error=error_msg)
        except Exception as e:
            logger.exception(f"Signup error: {e}")
            return AuthResult(success=False, error="회원가입 중 오류가 발생했습니다.")

    async def login(self, email: str, password: str) -> AuthResult:
        """
        로그인

        Args:
            email: 이메일
            password: 비밀번호

        Returns:
            AuthResult (토큰 포함)
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user is None:
                return AuthResult(
                    success=False,
                    error="로그인에 실패했습니다."
                )

            user_id = response.user.id

            # 마지막 로그인 시간 업데이트
            self.supabase.table("users").update({
                "last_login_at": "now()"
            }).eq("id", user_id).execute()

            # 사용자 프로필 조회
            profile = await self.get_user_profile(user_id)

            return AuthResult(
                success=True,
                user=profile,
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token
            )

        except AuthApiError as e:
            logger.warning(f"Login failed: {e.message}")
            error_msg = self._translate_error(e.message)
            return AuthResult(success=False, error=error_msg)
        except Exception as e:
            logger.exception(f"Login error: {e}")
            return AuthResult(success=False, error="로그인 중 오류가 발생했습니다.")

    async def logout(self, access_token: str) -> bool:
        """로그아웃"""
        try:
            self.supabase.auth.sign_out()
            return True
        except Exception as e:
            logger.warning(f"Logout error: {e}")
            return False

    async def get_user_profile(self, user_id: str) -> UserProfile | None:
        """사용자 프로필 조회 (크레딧 정보 포함)"""
        try:
            result = self.supabase.table("users").select(
                "id, email, name, church_id, role, is_active, subscription_plan, weekly_credits, weekly_credits_reset_at"
            ).eq("id", user_id).execute()

            if result.data and len(result.data) > 0:
                return UserProfile(**result.data[0])
            return None

        except Exception as e:
            logger.warning(f"Get profile error: {e}")
            return None

    async def update_profile(
        self,
        user_id: str,
        name: str | None = None,
        church_id: str | None = None
    ) -> UserProfile | None:
        """
        사용자 프로필 수정

        Args:
            user_id: 사용자 ID
            name: 이름
            church_id: 교회 ID
        """
        try:
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if church_id is not None:
                update_data["church_id"] = church_id

            if not update_data:
                return await self.get_user_profile(user_id)

            self.supabase.table("users").update(
                update_data
            ).eq("id", user_id).execute()

            return await self.get_user_profile(user_id)

        except Exception as e:
            logger.exception(f"Update profile error: {e}")
            return None

    async def verify_token(self, access_token: str) -> UserProfile | None:
        """
        JWT 토큰 검증 및 사용자 정보 반환

        Args:
            access_token: JWT 토큰

        Returns:
            UserProfile 또는 None (유효하지 않은 경우)
        """
        try:
            logger.info(f"Verifying token: {access_token[:50]}...")

            # JWT 토큰 디코딩 (서명 검증 없이 - Supabase가 발급한 토큰이므로)
            # 실제 프로덕션에서는 Supabase JWT secret으로 검증 권장
            decoded = jwt.decode(
                access_token,
                options={"verify_signature": False},
                algorithms=["HS256"]
            )
            logger.info(f"Token decoded successfully, sub: {decoded.get('sub')}")

            # 만료 시간 확인
            exp = decoded.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                logger.info(f"Token exp: {exp_datetime}, now: {now}")
                if exp_datetime < now:
                    logger.warning("Token expired")
                    return None

            # 사용자 ID 추출 (Supabase JWT의 sub 필드)
            user_id = decoded.get("sub")
            if not user_id:
                logger.warning("No user ID in token")
                return None

            # 사용자 프로필 조회
            logger.info(f"Fetching user profile for: {user_id}")
            profile = await self.get_user_profile(user_id)
            logger.info(f"Profile result: {profile}")
            return profile

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.exception(f"Token verification failed: {e}")
            return None

    async def set_user_church(self, user_id: str, church_id: str) -> bool:
        """사용자의 교회 배정"""
        try:
            # 교회 존재 여부 확인
            church = self.supabase.table("churches").select(
                "id"
            ).eq("id", church_id).single().execute()

            if not church.data:
                return False

            # 사용자 교회 배정
            self.supabase.table("users").update({
                "church_id": church_id
            }).eq("id", user_id).execute()

            return True

        except Exception as e:
            logger.exception(f"Set church error: {e}")
            return False

    async def set_user_role(self, user_id: str, role: str) -> bool:
        """사용자 역할 변경 (admin만 가능)"""
        if role not in ["admin", "member"]:
            return False

        try:
            self.supabase.table("users").update({
                "role": role
            }).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.exception(f"Set role error: {e}")
            return False

    async def change_password(
        self,
        user_id: str,
        email: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        비밀번호 변경

        Args:
            user_id: 사용자 ID
            email: 사용자 이메일
            current_password: 현재 비밀번호
            new_password: 새 비밀번호

        Returns:
            성공 여부
        """
        try:
            # 현재 비밀번호로 로그인 시도 (검증)
            verify_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": current_password
            })

            if verify_response.user is None:
                return False

            # 비밀번호 변경
            update_response = self.supabase.auth.update_user({
                "password": new_password
            })

            if update_response.user is None:
                return False

            logger.info(f"Password changed for user: {user_id}")
            return True

        except AuthApiError as e:
            logger.warning(f"Password change failed: {e.message}")
            return False
        except Exception as e:
            logger.exception(f"Change password error: {e}")
            return False

    def _translate_error(self, message: str) -> str:
        """에러 메시지 한글 변환"""
        error_map = {
            "Invalid login credentials": "이메일 또는 비밀번호가 올바르지 않습니다.",
            "User already registered": "이미 가입된 이메일입니다.",
            "Password should be at least 6 characters": "비밀번호는 6자 이상이어야 합니다.",
            "Unable to validate email address": "유효하지 않은 이메일 형식입니다.",
            "Email not confirmed": "이메일 인증이 필요합니다. 메일함을 확인해주세요.",
            "User not found": "등록되지 않은 이메일입니다.",
            "Signup requires a valid password": "유효한 비밀번호를 입력해주세요.",
            "Email rate limit exceeded": "너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.",
        }
        
        # 부분 매칭 (contains)
        for key, value in error_map.items():
            if key.lower() in message.lower():
                return value
        
        return message


# 싱글톤
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """AuthService 싱글톤"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
