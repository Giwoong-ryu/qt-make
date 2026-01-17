"""
포트원 결제 서비스
정기결제(빌링키) 발급 및 결제 처리
"""
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.database import get_supabase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PortOneService:
    """포트원 결제 서비스"""
    
    BASE_URL = "https://api.portone.io"
    
    def __init__(self):
        self.supabase = get_supabase()
        self.api_key = getattr(settings, "PORTONE_API_KEY", None)
        self.api_secret = getattr(settings, "PORTONE_API_SECRET", None)
        self._access_token = None
        self._token_expires_at = None
    
    async def _get_access_token(self) -> str:
        """포트원 액세스 토큰 발급"""
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at:
                return self._access_token
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/login/api-secret",
                    json={
                        "apiSecret": self.api_secret,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                self._access_token = data["accessToken"]
                # 토큰 유효기간 (약 1시간, 여유있게 50분으로 설정)
                from datetime import timedelta
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=50)
                
                logger.info(f"포트원 토큰 발급 성공: {self._access_token[:10]}...")
                return self._access_token
                
        except Exception as e:
            logger.error(f"포트원 토큰 발급 실패: {e}")
            raise
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: dict = None
    ) -> dict:
        """포트원 API 요청"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method,
                f"{self.BASE_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=data,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_billing_key_info(self, billing_key: str) -> dict:
        """빌링키 정보 조회"""
        try:
            result = await self._request(
                "GET",
                f"/billing-keys/{billing_key}"
            )
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"빌링키 정보 조회 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def charge_billing_key(
        self,
        billing_key: str,
        amount: int,
        order_name: str,
        customer_id: str,
        payment_id: str = None,
    ) -> dict:
        """
        빌링키로 결제 실행
        
        Args:
            billing_key: 포트원 빌링키
            amount: 결제 금액 (원)
            order_name: 주문명
            customer_id: 고객 ID (church_id)
            payment_id: 결제 ID (없으면 자동 생성)
        """
        if not payment_id:
            payment_id = f"payment_{customer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            result = await self._request(
                "POST",
                f"/payments/{payment_id}/billing-key",
                data={
                    "billingKey": billing_key,
                    "orderName": order_name,
                    "amount": {
                        "total": amount,
                    },
                    "currency": "KRW",
                    "customer": {
                        "id": customer_id,
                    },
                }
            )
            
            # 결제 내역 저장
            await self._save_payment_history(
                church_id=customer_id,
                amount=amount,
                status="paid",
                portone_payment_id=payment_id,
            )
            
            logger.info(f"결제 성공: payment_id={payment_id}, amount={amount}")
            return {"success": True, "payment_id": payment_id, "data": result}
            
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except:
                pass
            
            # 실패 내역 저장
            await self._save_payment_history(
                church_id=customer_id,
                amount=amount,
                status="failed",
                portone_payment_id=payment_id,
            )
            
            logger.error(f"결제 실패: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"결제 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _save_payment_history(
        self,
        church_id: str,
        amount: int,
        status: str,
        portone_payment_id: str,
    ):
        """결제 내역 저장"""
        try:
            self.supabase.table("payment_history").insert({
                "church_id": church_id,
                "amount": amount,
                "status": status,
                "portone_payment_id": portone_payment_id,
                "paid_at": datetime.now(timezone.utc).isoformat() if status == "paid" else None,
            }).execute()
        except Exception as e:
            logger.error(f"결제 내역 저장 실패: {e}")
    
    async def cancel_payment(self, payment_id: str, reason: str = "고객 요청") -> dict:
        """결제 취소 (환불)"""
        try:
            result = await self._request(
                "POST",
                f"/payments/{payment_id}/cancel",
                data={
                    "reason": reason,
                }
            )
            logger.info(f"결제 취소 성공: payment_id={payment_id}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"결제 취소 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def get_payment_history(self, church_id: str, limit: int = 10) -> list:
        """결제 내역 조회"""
        try:
            result = self.supabase.table("payment_history").select(
                "*"
            ).eq("church_id", church_id).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"결제 내역 조회 실패: {e}")
            return []


# 싱글톤
_portone_service: PortOneService | None = None


def get_portone_service() -> PortOneService:
    """PortOneService 싱글톤"""
    global _portone_service
    if _portone_service is None:
        _portone_service = PortOneService()
    return _portone_service
