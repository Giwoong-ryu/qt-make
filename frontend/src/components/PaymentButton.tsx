"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

import { API_URL } from "@/lib/api-config";

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

      // PC: IFRAME (결과를 직접 받음), Mobile: REDIRECTION (callback 페이지로 이동)
      const response = await PortOne.requestIssueBillingKey({
        storeId: process.env.NEXT_PUBLIC_PORTONE_STORE_ID!,
        channelKey: process.env.NEXT_PUBLIC_PORTONE_CHANNEL_KEY!,
        billingKeyMethod: "EASY_PAY",
        issueName: "프리미엄 정기결제",
        issueId: `issue-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        customer: {
          customerId: user.church_id,
          email: user.email || undefined,
          fullName: user.name || undefined,
          phoneNumber: "01012345678",
        },
        windowType: {
          pc: "IFRAME",          // ✅ PC: IFRAME (가장 안정적)
          mobile: "REDIRECTION", // ✅ Mobile: REDIRECTION (callback으로 이동)
        },
        redirectUrl: `${window.location.origin}/subscription/callback?customerId=${user.church_id}`,
      });

      // PC IFRAME 모드: 결과를 직접 받아서 처리
      if (response && response.code === undefined) {
        // 빌링키 발급 성공
        const billingKey = response.billingKey;

        // 백엔드에 빌링키 저장 및 구독 활성화
        const backendResponse = await fetch(`${API_URL}/api/subscription/activate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("qt_access_token")}`,
          },
          body: JSON.stringify({
            billing_key: billingKey,
            church_id: user.church_id,
            tier: "basic",
          }),
        });

        if (!backendResponse.ok) {
          const errorData = await backendResponse.json().catch(() => ({}));
          const errorMessage = errorData.detail || errorData.message || "빌링키 저장 실패";
          console.error("Backend error:", errorData);
          throw new Error(errorMessage);
        }

        const result = await backendResponse.json();
        console.log("구독 활성화 성공:", result);
        onSuccess?.();
      } else if (response && response.code) {
        // 에러 발생
        throw new Error(response.message || "빌링키 발급 실패");
      }
      // Mobile REDIRECTION: 이 코드는 실행되지 않고 callback 페이지로 이동
    } catch (error) {
      console.error("결제 오류:", error);
      onError?.("결제 처리 중 오류가 발생했습니다.");
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
