import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 프로덕션 빌드 최적화
  output: "standalone", // Docker 배포용

  // 이미지 최적화
  images: {
    domains: [
      "supabase.co",
      "r2.cloudflarestorage.com",
    ],
  },

  // 환경변수 검증
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_PORTONE_STORE_ID: process.env.NEXT_PUBLIC_PORTONE_STORE_ID,
    NEXT_PUBLIC_PORTONE_CHANNEL_KEY: process.env.NEXT_PUBLIC_PORTONE_CHANNEL_KEY,
  },
};

export default nextConfig;
