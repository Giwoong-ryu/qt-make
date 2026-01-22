"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

import { API_URL } from "@/lib/api-config";

interface TestPaymentButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

export default function TestPaymentButton({
  onSuccess,
  onError,
  className = "",
}: TestPaymentButtonProps) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleTestSubscribe = async () => {
    if (!user?.church_id) {
      onError?.("교회 정보가 없습니다. 먼저 교회를 등록해주세요.");
      return;
    }

    setIsLoading(true);

    try {
      // 포트원 SDK 동적 로드
      const PortOne = await import("@portone/browser-sdk/v2");

      // 테스트 모드: 테스트 채널 키 사용
      const TEST_CHANNEL_KEY = process.env.NEXT_PUBLIC_PORTONE_TEST_CHANNEL_KEY
        || process.env.NEXT_PUBLIC_PORTONE_CHANNEL_KEY; // fallback to live

      const response = await PortOne.requestIssueBillingKey({
        storeId: process.env.NEXT_PUBLIC_PORTONE_STORE_ID!,
        channelKey: TEST_CHANNEL_KEY!,
        billingKeyMethod: "EASY_PAY",
        issueName: "[테스트] 프리미엄 정기결제",
        issueId: `test-issue-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        customer: {
          customerId: `test-${user.church_id}`,
          email: user.email || "test@example.com",
          fullName: user.name || "테스트 사용자",
          phoneNumber: "01012345678",
        },
        windowType: {
          pc: "IFRAME",
          mobile: "REDIRECTION",
        },
        redirectUrl: `${window.location.origin}/subscription/callback?customerId=${user.church_id}&test=true`,
      });

      if (response && response.code === undefined) {
        const billingKey = response.billingKey;

        // 백엔드에 빌링키 저장 (테스트 모드 표시)
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
          console.error("[테스트] Backend error:", errorData);
          throw new Error(errorMessage);
        }

        const result = await backendResponse.json();
        console.log("[테스트] 구독 활성화 성공:", result);
        onSuccess?.();
      } else if (response && response.code) {
        throw new Error(response.message || "빌링키 발급 실패");
      }
    } catch (error) {
      console.error("[테스트] 결제 오류:", error);
      onError?.(error instanceof Error ? error.message : "결제 처리 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  // 개발 환경에서만 표시
  if (process.env.NODE_ENV === "production") {
    return null;
  }

  return (
    <button
      onClick={handleTestSubscribe}
      disabled={isLoading}
      className={`
        px-6 py-3 rounded-lg font-medium transition-all border-2 border-dashed
        ${isLoading
          ? "bg-gray-400 cursor-not-allowed border-gray-500"
          : "bg-yellow-100 hover:bg-yellow-200 text-yellow-800 border-yellow-400 shadow-md hover:shadow-lg"
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
          테스트 처리 중...
        </span>
      ) : (
        <span className="flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          [테스트] 결제 테스트
        </span>
      )}
    </button>
  );
}
