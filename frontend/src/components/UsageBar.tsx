"use client";

interface UsageBarProps {
    current: number;
    limit: number;
    label?: string;
    showUpgrade?: boolean;
    onUpgradeClick?: () => void;
}

export default function UsageBar({
    current,
    limit,
    label = "이번 달 영상 생성",
    showUpgrade = true,
    onUpgradeClick,
}: UsageBarProps) {
    // 무제한 (-1)인 경우
    const isUnlimited = limit === -1;
    const percentage = isUnlimited ? 0 : Math.min((current / limit) * 100, 100);
    const isNearLimit = !isUnlimited && percentage >= 80;
    const isAtLimit = !isUnlimited && current >= limit;

    return (
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-200">{label}</span>
                <span className={`text-sm font-bold ${isAtLimit ? "text-red-400" : "text-white"}`}>
                    {isUnlimited ? (
                        <span className="flex items-center gap-1">
                            <svg className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                            무제한
                        </span>
                    ) : (
                        `${current} / ${limit}개`
                    )}
                </span>
            </div>

            {!isUnlimited && (
                <>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div
                            className={`h-full transition-all duration-500 rounded-full ${isAtLimit
                                    ? "bg-red-500"
                                    : isNearLimit
                                        ? "bg-yellow-500"
                                        : "bg-gradient-to-r from-blue-500 to-purple-500"
                                }`}
                            style={{ width: `${percentage}%` }}
                        />
                    </div>

                    {isAtLimit && showUpgrade && (
                        <div className="mt-3 flex items-center justify-between">
                            <span className="text-xs text-red-400">
                                한도에 도달했습니다
                            </span>
                            <button
                                onClick={onUpgradeClick}
                                className="text-xs px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full hover:from-blue-600 hover:to-purple-700 transition-all"
                            >
                                업그레이드
                            </button>
                        </div>
                    )}

                    {isNearLimit && !isAtLimit && (
                        <p className="mt-2 text-xs text-yellow-400">
                            한도가 거의 다 찼습니다 ({limit - current}개 남음)
                        </p>
                    )}
                </>
            )}
        </div>
    );
}
