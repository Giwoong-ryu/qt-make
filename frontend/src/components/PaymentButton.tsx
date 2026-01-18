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

      // REDIRECTION 모드: 페이지 이동 후 callback 페이지에서 처리
      await PortOne.requestIssueBillingKey({
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
          pc: "REDIRECTION",     // ✅ IFRAME → REDIRECTION 변경
          mobile: "REDIRECTION",
        },
        redirectUrl: `${window.location.origin}/subscription/callback?customerId=${user.church_id}`, // ✅ customerId 추가
      });

      // 이 줄 이후는 실행되지 않음 (페이지가 리다이렉트됨)
      // 모든 후속 처리는 /subscription/callback 페이지에서 수행
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
