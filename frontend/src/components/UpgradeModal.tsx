"use client";

import { useRouter } from "next/navigation";

interface UpgradeModalProps {
    isOpen: boolean;
    onClose: () => void;
    title?: string;
    message?: string;
}

export default function UpgradeModal({
    isOpen,
    onClose,
    title = "업그레이드가 필요합니다",
    message = "이 기능을 사용하려면 프리미엄 플랜으로 업그레이드하세요.",
}: UpgradeModalProps) {
    const router = useRouter();

    if (!isOpen) return null;

    const handleUpgrade = () => {
        onClose();
        router.push("/subscription");
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* 배경 오버레이 */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* 모달 */}
            <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl p-8 max-w-md w-full mx-4 border border-white/20 shadow-2xl animate-in fade-in zoom-in duration-200">
                {/* 닫기 버튼 */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
                >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>

                {/* 아이콘 */}
                <div className="flex justify-center mb-6">
                    <div className="w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full flex items-center justify-center">
                        <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                    </div>
                </div>

                {/* 텍스트 */}
                <h2 className="text-2xl font-bold text-white text-center mb-3">
                    {title}
                </h2>
                <p className="text-gray-400 text-center mb-6">
                    {message}
                </p>

                {/* 혜택 목록 */}
                <div className="bg-white/5 rounded-xl p-4 mb-6">
                    <p className="text-sm font-medium text-white mb-3">프리미엄 혜택</p>
                    <ul className="space-y-2 text-sm text-gray-300">
                        <li className="flex items-center gap-2">
                            <span className="text-green-400">✓</span> 무제한 영상 생성
                        </li>
                        <li className="flex items-center gap-2">
                            <span className="text-green-400">✓</span> 모든 배경팩 & BGM
                        </li>
                        <li className="flex items-center gap-2">
                            <span className="text-green-400">✓</span> 커스텀 썸네일 편집
                        </li>
                    </ul>
                </div>

                {/* 가격 */}
                <p className="text-center text-white mb-6">
                    <span className="text-3xl font-bold">30,000원</span>
                    <span className="text-gray-400">/월</span>
                </p>

                {/* 버튼 */}
                <div className="flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 py-3 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
                    >
                        나중에
                    </button>
                    <button
                        onClick={handleUpgrade}
                        className="flex-1 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all shadow-lg"
                    >
                        업그레이드
                    </button>
                </div>
            </div>
        </div>
    );
}
