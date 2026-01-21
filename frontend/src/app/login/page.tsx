"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Mail, Lock, Loader2, AlertCircle } from "lucide-react";
import Footer from "@/components/Footer";

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading: authLoading, isAuthenticated } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // 이미 로그인된 상태면 메인 페이지로 리다이렉트
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [authLoading, isAuthenticated, router]);

  // 로딩 중이거나 이미 인증된 경우 로딩 표시
  if (authLoading || isAuthenticated) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </main>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("이메일과 비밀번호를 입력해주세요.");
      return;
    }

    setIsLoading(true);
    try {
      await login(email, password);
      // 로그인 성공 시 리다이렉트 (브라우저 경고창 처리 후)
      setTimeout(() => {
        window.location.href = "/";
      }, 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인에 실패했습니다.");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          {/* 로고/타이틀 */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              QT Video
            </h1>
            <p className="text-gray-500 mt-2">
              교회 묵상 영상 자동화 서비스
            </p>
          </div>

          {/* 로그인 폼 */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
              로그인
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* 에러 메시지 */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* 이메일 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  이메일
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* 비밀번호 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  비밀번호
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    name="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="********"
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* 로그인 버튼 */}
              <button
                type="submit"
                disabled={isLoading || authLoading}
                className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    로그인 중...
                  </>
                ) : (
                  "로그인"
                )}
              </button>
            </form>

            {/* 회원가입 링크 */}
            <div className="mt-6 text-center text-sm text-gray-500">
              계정이 없으신가요?{" "}
              <Link
                href="/signup"
                className="text-blue-500 hover:text-blue-600 font-medium"
              >
                회원가입
              </Link>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
