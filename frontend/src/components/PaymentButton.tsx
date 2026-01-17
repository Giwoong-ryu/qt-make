"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface PaymentButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

export default function PaymentButton({
  onSuccess,
  onError,
  className = "",
}: PaymentButtonProps) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubscribe = async () => {
    if (!user?.church_id) {
      onError?.("교회 정보가 없습니다. 먼저 교회를 등록해주세요.");
      return;
    }

    setIsLoading(true);

    try {
      // 포트원 SDK 동적 로드
      const PortOne = await import("@portone/browser-sdk/v2");

      const response = await PortOne.requestIssueBillingKey({
        storeId: process.env.NEXT_PUBLIC_PORTONE_STORE_ID!,
        channelKey: process.env.NEXT_PUBLIC_PORTONE_CHANNEL_KEY!,
        billingKeyMethod: "EASY_PAY",
        issueName: "프리미엄 정기결제",
        orderName: "프리미엄 정기결제 (빌링키)",
        issueId: `issue-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        // @ts-ignore
        amount: 0,
        customer: {
          customerId: user.church_id,
          email: user.email || undefined,
          fullName: user.name || undefined,
          phoneNumber: "01012345678", // 하이픈 제거
        },
        windowType: {
          pc: "IFRAME",
          mobile: "REDIRECTION",
        },
        redirectUrl: `${window.location.origin}/subscription/callback`,
      });

      console.log("PortOne Response:", response); // 디버깅용 로그

      if (!response) {
        onError?.("결제 요청이 취소되었거나 실패했습니다.");
        return;
      }

      if (response.code !== undefined) {
        // V2 응답 구조가 다를 수 있음
      }

      if (response.code === "SUCCESS" && response.billingKey) {
        // 서버에 빌링키 저장 및 첫 결제 실행
        const apiResponse = await fetch("/api/subscription/activate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
          body: JSON.stringify({
            billing_key: response.billingKey,
            tier: "basic",
            church_id: user.church_id,
          }),
        });

        const result = await apiResponse.json();

        if (result.success) {
          onSuccess?.();
        } else {
          onError?.(result.message || "구독 활성화에 실패했습니다.");
        }
      } else {
        onError?.(response.message || "결제 요청에 실패했습니다.");
      }
    } catch (error) {
      console.error("결제 오류:", error);
      onError?.("결제 처리 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleSubscribe}
      disabled={isLoading}
      className={`
        px-6 py-3 rounded-lg font-medium transition-all
        ${isLoading
          ? "bg-gray-400 cursor-not-allowed"
          : "bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg hover:shadow-xl"
        }
        ${className}
      `}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          처리 중...
        </span>
      ) : (
        <span className="flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
            />
          </svg>
          프리미엄 구독하기
        </span>
      )}
    </button>
  );
}
