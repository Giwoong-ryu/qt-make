"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import PaymentButton from "@/components/PaymentButton";
import UsageBar from "@/components/UsageBar";

interface SubscriptionInfo {
    tier: "free" | "basic" | "premium";
    status: string | null;
    current_period_end: string | null;
}

interface UsageInfo {
    video_count: number;
    limit: number;
    remaining: number;
    year_month: string;
}

interface PaymentRecord {
    id: string;
    amount: number;
    status: string;
    paid_at: string | null;
    created_at: string;
}

export default function SubscriptionPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();

    const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
    const [usage, setUsage] = useState<UsageInfo | null>(null);
    const [payments, setPayments] = useState<PaymentRecord[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push("/login");
            return;
        }

        if (isAuthenticated && user?.church_id) {
            fetchSubscriptionData();
        }
    }, [authLoading, isAuthenticated, user]);

    const fetchSubscriptionData = async () => {
        try {
            const token = localStorage.getItem("access_token");
            const headers = {
                Authorization: `Bearer ${token}`,
            };

            // 병렬로 데이터 fetch
            const [subRes, usageRes, paymentRes] = await Promise.all([
                fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/subscription/status?church_id=${user?.church_id}`, { headers }),
                fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/subscription/usage?church_id=${user?.church_id}`, { headers }),
                fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/subscription/payments?church_id=${user?.church_id}`, { headers }),
            ]);

            if (subRes.ok) {
                const subData = await subRes.json();
                setSubscription(subData);
            }

            if (usageRes.ok) {
                const usageData = await usageRes.json();
                setUsage(usageData);
            }

            if (paymentRes.ok) {
                const paymentData = await paymentRes.json();
                setPayments(paymentData);
            }
        } catch (error) {
            console.error("구독 정보 로드 실패:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handlePaymentSuccess = () => {
        setMessage({ type: "success", text: "🎉 프리미엄 구독이 활성화되었습니다!" });
        fetchSubscriptionData();
    };

    const handlePaymentError = (error: string) => {
        setMessage({ type: "error", text: error });
    };

    const handleCancelSubscription = async () => {
        if (!confirm("정말 구독을 취소하시겠습니까?\n현재 결제 기간이 끝나면 무료 플랜으로 전환됩니다.")) {
            return;
        }

        try {
            const token = localStorage.getItem("access_token");
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/subscription/cancel`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ church_id: user?.church_id }),
            });

            const data = await res.json();
            if (data.success) {
                setMessage({ type: "success", text: "구독이 취소되었습니다." });
                fetchSubscriptionData();
            } else {
                setMessage({ type: "error", text: data.message || "취소에 실패했습니다." });
            }
        } catch (error) {
            setMessage({ type: "error", text: "오류가 발생했습니다." });
        }
    };

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
            </div>
        );
    }

    const isPremium = subscription?.tier === "basic" || subscription?.tier === "premium";

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 py-12 px-4">
            <div className="max-w-4xl mx-auto">
                {/* 헤더 */}
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-white mb-4">구독 관리</h1>
                    <p className="text-gray-400">QT Video SaaS 구독 상태를 관리하세요</p>
                </div>

                {/* 알림 메시지 */}
                {message && (
                    <div
                        className={`mb-6 p-4 rounded-lg ${message.type === "success"
                                ? "bg-green-500/20 border border-green-500 text-green-400"
                                : "bg-red-500/20 border border-red-500 text-red-400"
                            }`}
                    >
                        {message.text}
                    </div>
                )}

                {/* 현재 플랜 */}
                <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10 mb-8">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-2">현재 플랜</h2>
                            <div className="flex items-center gap-3">
                                <span
                                    className={`px-4 py-2 rounded-full text-sm font-bold ${isPremium
                                            ? "bg-gradient-to-r from-yellow-500 to-orange-500 text-white"
                                            : "bg-gray-700 text-gray-300"
                                        }`}
                                >
                                    {isPremium ? "⭐ 프리미엄" : "무료"}
                                </span>
                                {subscription?.status === "cancelled" && (
                                    <span className="px-3 py-1 rounded-full text-xs bg-red-500/20 text-red-400 border border-red-500">
                                        취소됨
                                    </span>
                                )}
                            </div>
                        </div>

                        {isPremium && subscription?.current_period_end && (
                            <div className="text-right">
                                <p className="text-sm text-gray-400">다음 결제일</p>
                                <p className="text-white font-medium">
                                    {new Date(subscription.current_period_end).toLocaleDateString("ko-KR")}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* 사용량 */}
                    {usage && (
                        <UsageBar
                            current={usage.video_count}
                            limit={usage.limit}
                            showUpgrade={!isPremium}
                        />
                    )}
                </div>

                {/* 플랜 비교 */}
                <div className="grid md:grid-cols-2 gap-6 mb-8">
                    {/* 무료 플랜 */}
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
                        <h3 className="text-xl font-bold text-white mb-2">무료</h3>
                        <p className="text-3xl font-bold text-white mb-6">
                            0원<span className="text-sm font-normal text-gray-400">/월</span>
                        </p>
                        <ul className="space-y-3 mb-6">
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 월 7개 영상 생성
                            </li>
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 기본 배경팩
                            </li>
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 썸네일 템플릿 5개
                            </li>
                            <li className="flex items-center gap-2 text-gray-500">
                                <span className="text-red-400">✗</span> 커스텀 썸네일 편집
                            </li>
                        </ul>
                        {!isPremium && (
                            <button
                                disabled
                                className="w-full py-3 rounded-lg bg-gray-700 text-gray-400 cursor-not-allowed"
                            >
                                현재 플랜
                            </button>
                        )}
                    </div>

                    {/* 프리미엄 플랜 */}
                    <div className="bg-gradient-to-br from-purple-500/20 to-blue-500/20 backdrop-blur-lg rounded-2xl p-6 border border-purple-500/50 relative">
                        <div className="absolute -top-3 right-4 px-3 py-1 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full text-xs font-bold text-white">
                            추천
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">프리미엄</h3>
                        <p className="text-3xl font-bold text-white mb-6">
                            30,000원<span className="text-sm font-normal text-gray-400">/월</span>
                        </p>
                        <ul className="space-y-3 mb-6">
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> <strong>무제한</strong> 영상 생성
                            </li>
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 모든 배경팩
                            </li>
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 모든 썸네일 템플릿
                            </li>
                            <li className="flex items-center gap-2 text-gray-300">
                                <span className="text-green-400">✓</span> 커스텀 썸네일 편집
                            </li>
                        </ul>
                        {isPremium ? (
                            <button
                                onClick={handleCancelSubscription}
                                className="w-full py-3 rounded-lg bg-red-500/20 text-red-400 border border-red-500 hover:bg-red-500/30 transition-all"
                            >
                                구독 취소
                            </button>
                        ) : (
                            <PaymentButton
                                onSuccess={handlePaymentSuccess}
                                onError={handlePaymentError}
                                className="w-full"
                            />
                        )}
                    </div>
                </div>

                {/* 결제 내역 */}
                {payments.length > 0 && (
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
                        <h3 className="text-xl font-bold text-white mb-4">결제 내역</h3>
                        <div className="space-y-3">
                            {payments.map((payment) => (
                                <div
                                    key={payment.id}
                                    className="flex items-center justify-between py-3 border-b border-white/10 last:border-0"
                                >
                                    <div>
                                        <p className="text-white font-medium">
                                            {payment.amount.toLocaleString()}원
                                        </p>
                                        <p className="text-sm text-gray-400">
                                            {payment.paid_at
                                                ? new Date(payment.paid_at).toLocaleDateString("ko-KR")
                                                : new Date(payment.created_at).toLocaleDateString("ko-KR")}
                                        </p>
                                    </div>
                                    <span
                                        className={`px-3 py-1 rounded-full text-xs ${payment.status === "paid"
                                                ? "bg-green-500/20 text-green-400"
                                                : payment.status === "failed"
                                                    ? "bg-red-500/20 text-red-400"
                                                    : "bg-gray-500/20 text-gray-400"
                                            }`}
                                    >
                                        {payment.status === "paid"
                                            ? "결제 완료"
                                            : payment.status === "failed"
                                                ? "결제 실패"
                                                : payment.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 뒤로가기 */}
                <div className="mt-8 text-center">
                    <button
                        onClick={() => router.push("/")}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        ← 대시보드로 돌아가기
                    </button>
                </div>
            </div>
        </div>
    );
}
