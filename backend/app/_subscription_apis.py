
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

        # 이벤트 타입별 처리
        event_type = body.get("type")

        if event_type == "Transaction.Ready":
            # 빌링키 발급 완료
            data = body.get("data", {})
            billing_key = data.get("billingKey")
            customer_id = data.get("customer", {}).get("id")

            if billing_key and customer_id:
                # 구독 활성화 (백업 처리)
                try:
                    subscription_service = get_subscription_service()
                    portone_service = get_portone_service()

                    # 첫 결제 실행
                    payment_result = await portone_service.charge_billing_key(
                        billing_key=billing_key,
                        amount=30000,
                        order_name="QT Video SaaS basic 플랜 (웹훅)",
                        customer_id=customer_id,
                    )

                    if payment_result.get("success"):
                        subscription_service.upgrade_subscription(
                            church_id=customer_id,
                            tier="basic",
                            billing_key=billing_key
                        )
                        logger.info(f"웹훅을 통한 구독 활성화 완료: {customer_id}")
                except Exception as sub_error:
                    logger.error(f"웹훅 구독 활성화 실패: {sub_error}")

        elif event_type == "Transaction.Paid":
            # 결제 성공
            logger.info(f"결제 성공 웹훅: {body}")

        elif event_type == "Transaction.Failed":
            # 결제 실패
            logger.warning(f"결제 실패 웹훅: {body}")

        return {"status": "received"}

    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
