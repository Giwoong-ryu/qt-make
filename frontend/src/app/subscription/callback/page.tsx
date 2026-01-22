"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL } from "@/lib/api-config";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<"processing" | "success" | "error">("processing");
  const [message, setMessage] = useState("결제 정보를 처리 중입니다...");

  useEffect(() => {
    const processCallback = async () => {
      try {
        // 포트원 V2 REDIRECTION 응답 파라미터 추출
        const code = searchParams.get("code");
        const billingKey = searchParams.get("billingKey");
        const errorMessage = searchParams.get("message");
        const customerId = searchParams.get("customerId");

        console.log("Callback params:", { code, billingKey, errorMessage, customerId });

        // 성공 여부 확인 (code === "0" 또는 code === null이면 성공)
        if (code && code !== "0") {
          throw new Error(errorMessage || "결제 요청이 실패했습니다.");
        }

        if (!billingKey) {
          throw new Error("빌링키를 받지 못했습니다.");
        }

        // 백엔드에 빌링키 전달 및 구독 활성화
        const token = localStorage.getItem("qt_access_token");
        if (!token) {
          throw new Error("로그인 정보가 없습니다. 다시 로그인해주세요.");
        }

        if (!customerId) {
          throw new Error("교회 정보를 찾을 수 없습니다.");
        }

        const response = await fetch(`${API_URL}/api/subscription/activate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({
            billing_key: billingKey,
            tier: "basic",
            church_id: customerId,
          }),
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
          throw new Error(result.message || "구독 활성화에 실패했습니다.");
        }

        // 사용자 정보 갱신
        await refreshUser();

        setStatus("success");
        setMessage("구독이 성공적으로 활성화되었습니다!");

        // 3초 후 구독 페이지로 이동
        setTimeout(() => {
          router.push("/subscription");
        }, 3000);

      } catch (error: any) {
        console.error("Callback processing error:", error);
        setStatus("error");
        setMessage(error.message || "처리 중 오류가 발생했습니다.");
      }
    };

    processCallback();
  }, [searchParams, refreshUser, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="max-w-md w-full bg-gray-800 rounded-lg shadow-xl p-8">
        {status === "processing" && (
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-white mb-2">처리 중...</h2>
            <p className="text-gray-400">{message}</p>
          </div>
        )}

        {status === "success" && (
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-16 w-16 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">결제 성공!</h2>
            <p className="text-gray-400">{message}</p>
            <p className="text-sm text-gray-500 mt-4">잠시 후 자동으로 이동합니다...</p>
          </div>
        )}

        {status === "error" && (
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-16 w-16 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">결제 실패</h2>
            <p className="text-gray-400 mb-4">{message}</p>
            <button
              onClick={() => router.push("/subscription")}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              다시 시도하기
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SubscriptionCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500"></div>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
