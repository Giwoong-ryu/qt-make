"""
구독 관리 서비스
유료/무료 사용자 관리 및 기능 제한
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import get_supabase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# 티어별 제한 설정
TIER_LIMITS = {
    "free": {
        "monthly_videos": 7,
        "thumbnail_templates": 5,
        "custom_thumbnail": False,
        "all_packs": False,
        "all_bgm": False,
    },
    "basic": {
        "monthly_videos": float("inf"),
        "thumbnail_templates": float("inf"),
        "custom_thumbnail": True,
        "all_packs": True,
        "all_bgm": True,
        "price": 30000,
    },
    "premium": {
        "monthly_videos": float("inf"),
        "thumbnail_templates": float("inf"),
        "custom_thumbnail": True,
        "all_packs": True,
        "all_bgm": True,
        "price": 50000,
    }
}


class SubscriptionService:
    """구독 관리 서비스"""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    def get_subscription(self, church_id: str) -> dict:
        """
        교회의 구독 정보 조회
        
        Returns:
            {
                "tier": "free" | "basic" | "premium",
                "status": "active" | "cancelled" | "expired",
                "billing_key": str | None,
                "current_period_end": datetime | None
            }
        """
        try:
            # churches 테이블에서 subscription_tier 조회
            result = self.supabase.table("churches").select(
                "subscription_tier"
            ).eq("id", church_id).single().execute()
            
            if result.data:
                tier = result.data.get("subscription_tier", "free")
            else:
                tier = "free"
            
            # subscriptions 테이블에서 상세 정보 조회
            sub_result = self.supabase.table("subscriptions").select(
                "*"
            ).eq("church_id", church_id).eq("status", "active").single().execute()
            
            if sub_result.data:
                return {
                    "tier": tier,
                    "status": sub_result.data.get("status", "active"),
                    "billing_key": sub_result.data.get("billing_key"),
                    "current_period_start": sub_result.data.get("current_period_start"),
                    "current_period_end": sub_result.data.get("current_period_end"),
                }
            
            return {
                "tier": tier,
                "status": "active" if tier != "free" else None,
                "billing_key": None,
                "current_period_start": None,
                "current_period_end": None,
            }
            
        except Exception as e:
            logger.error(f"구독 정보 조회 실패: {e}")
            return {"tier": "free", "status": None, "billing_key": None}
    
    def get_tier_limits(self, tier: str) -> dict:
        """티어별 제한 정보 반환"""
        return TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    
    def check_feature_access(self, church_id: str, feature: str) -> bool:
        """
        특정 기능 접근 권한 확인
        
        Args:
            church_id: 교회 ID
            feature: "custom_thumbnail", "all_packs", "all_bgm"
            
        Returns:
            True if accessible, False otherwise
        """
        subscription = self.get_subscription(church_id)
        limits = self.get_tier_limits(subscription["tier"])
        return limits.get(feature, False)
    
    def get_monthly_usage(self, church_id: str) -> dict:
        """
        월간 사용량 조회
        
        Returns:
            {
                "video_count": int,
                "limit": int,
                "remaining": int,
                "year_month": "2026-01"
            }
        """
        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        try:
            result = self.supabase.table("monthly_usage").select(
                "video_count"
            ).eq("church_id", church_id).eq("year_month", year_month).single().execute()
            
            subscription = self.get_subscription(church_id)
            limits = self.get_tier_limits(subscription["tier"])
            monthly_limit = limits["monthly_videos"]
            
            if result.data:
                count = result.data.get("video_count", 0)
            else:
                count = 0
            
            # 무제한인 경우 처리
            if monthly_limit == float("inf"):
                remaining = float("inf")
            else:
                remaining = max(0, monthly_limit - count)
            
            return {
                "video_count": count,
                "limit": monthly_limit if monthly_limit != float("inf") else -1,
                "remaining": remaining if remaining != float("inf") else -1,
                "year_month": year_month,
            }
            
        except Exception as e:
            logger.error(f"월간 사용량 조회 실패: {e}")
            return {
                "video_count": 0,
                "limit": 7,
                "remaining": 7,
                "year_month": year_month,
            }
    
    def can_create_video(self, church_id: str) -> tuple[bool, str]:
        """
        영상 생성 가능 여부 확인
        
        Returns:
            (can_create: bool, message: str)
        """
        usage = self.get_monthly_usage(church_id)
        
        # 무제한 (-1)인 경우
        if usage["limit"] == -1:
            return True, "영상 생성이 가능합니다."
        
        if usage["remaining"] <= 0:
            return False, f"이번 달 영상 생성 한도({usage['limit']}개)를 초과했습니다. 프리미엄으로 업그레이드하세요."
        
        return True, f"영상 생성 가능 (남은 횟수: {usage['remaining']}개)"
    
    def increment_usage(self, church_id: str) -> bool:
        """
        월간 사용량 증가
        
        Returns:
            True if successful
        """
        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        try:
            # upsert: 없으면 생성, 있으면 증가
            result = self.supabase.table("monthly_usage").select(
                "id", "video_count"
            ).eq("church_id", church_id).eq("year_month", year_month).execute()
            
            if result.data:
                # 기존 레코드 업데이트
                current_count = result.data[0]["video_count"]
                self.supabase.table("monthly_usage").update({
                    "video_count": current_count + 1
                }).eq("id", result.data[0]["id"]).execute()
            else:
                # 새 레코드 생성
                self.supabase.table("monthly_usage").insert({
                    "church_id": church_id,
                    "year_month": year_month,
                    "video_count": 1,
                }).execute()
            
            logger.info(f"사용량 증가: church_id={church_id}, year_month={year_month}")
            return True
            
        except Exception as e:
            logger.error(f"사용량 증가 실패: {e}")
            return False
    
    def upgrade_subscription(
        self, 
        church_id: str, 
        tier: str, 
        billing_key: str
    ) -> dict:
        """
        구독 업그레이드
        
        Args:
            church_id: 교회 ID
            tier: "basic" | "premium"
            billing_key: 포트원 빌링키
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            now = datetime.now(timezone.utc)
            
            # churches 테이블 업데이트
            self.supabase.table("churches").update({
                "subscription_tier": tier,
            }).eq("id", church_id).execute()
            
            # subscriptions 테이블에 저장
            self.supabase.table("subscriptions").upsert({
                "church_id": church_id,
                "billing_key": billing_key,
                "tier": tier,
                "status": "active",
                "current_period_start": now.isoformat(),
                "current_period_end": (now.replace(month=now.month + 1) if now.month < 12 
                                       else now.replace(year=now.year + 1, month=1)).isoformat(),
            }, on_conflict="church_id").execute()
            
            logger.info(f"구독 업그레이드 완료: church_id={church_id}, tier={tier}")
            return {"success": True, "message": f"{tier} 플랜으로 업그레이드되었습니다."}
            
        except Exception as e:
            logger.error(f"구독 업그레이드 실패: {e}")
            return {"success": False, "message": str(e)}
    
    def cancel_subscription(self, church_id: str) -> dict:
        """
        구독 취소 (기간 만료까지 유지)
        """
        try:
            self.supabase.table("subscriptions").update({
                "status": "cancelled",
            }).eq("church_id", church_id).execute()
            
            logger.info(f"구독 취소: church_id={church_id}")
            return {"success": True, "message": "구독이 취소되었습니다. 현재 결제 기간 종료 후 무료 플랜으로 전환됩니다."}
            
        except Exception as e:
            logger.error(f"구독 취소 실패: {e}")
            return {"success": False, "message": str(e)}


# 싱글톤
_subscription_service: SubscriptionService | None = None


def get_subscription_service() -> SubscriptionService:
    """SubscriptionService 싱글톤"""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
