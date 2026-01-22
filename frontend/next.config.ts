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


};

export default nextConfig;
