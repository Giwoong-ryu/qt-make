"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function SubscriptionCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();

    useEffect(() => {
        const handleCallback = async () => {
            // 포트원 리다이렉션 결과 처리
            const billingKey = searchParams.get("billingKey");
            const code = searchParams.get("code");

            if (code === "SUCCESS" && billingKey) {
                try {
                    const token = localStorage.getItem("access_token");
                    const response = await fetch(
                        `${process.env.NEXT_PUBLIC_API_URL}/api/subscription/activate`,
                        {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                Authorization: `Bearer ${token}`,
                            },
                            body: JSON.stringify({
                                billing_key: billingKey,
                                tier: "basic",
                            }),
                        }
                    );

                    const result = await response.json();

                    if (result.success) {
                        // 성공 시 구독 페이지로 이동
                        router.push("/subscription?success=true");
                    } else {
                        router.push("/subscription?error=" + encodeURIComponent(result.message));
                    }
                } catch (error) {
                    console.error("콜백 처리 오류:", error);
                    router.push("/subscription?error=처리 중 오류가 발생했습니다");
                }
            } else {
                // 실패 또는 취소
                const message = searchParams.get("message") || "결제가 취소되었습니다";
                router.push("/subscription?error=" + encodeURIComponent(message));
            }
        };

        handleCallback();
    }, [searchParams, router]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500 mx-auto mb-4"></div>
                <p className="text-white">결제 결과 처리 중...</p>
            </div>
        </div>
    );
}
