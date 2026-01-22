export const getApiUrl = () => {
    // 브라우저 환경에서 실행 시
    if (typeof window !== "undefined") {
        const hostname = window.location.hostname;

        // 로컬 개발 환경
        if (hostname === "localhost" || hostname === "127.0.0.1") {
            return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        }

        // 프로덕션 도메인 (www 포함)
        if (hostname.includes("qt-make.com")) {
            return "https://qt-make-production.up.railway.app";
        }

        // 그 외 모든 환경 (Vercel 프리뷰 등) -> Railway 프로덕션
        return "https://qt-make-production.up.railway.app";
    }

    // 서버 사이드 실행 시 (SSR)
    if (process.env.NODE_ENV === "production") {
        return "https://qt-make-production.up.railway.app";
    }

    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
};

// 상수로도 export (컴포넌트 등에서 바로 쓸 때)
export const API_URL = getApiUrl();
