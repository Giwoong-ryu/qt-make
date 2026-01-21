"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Mail, Lock, User, Loader2, AlertCircle, Church } from "lucide-react";
import Footer from "@/components/Footer";

export default function SignupPage() {
  const router = useRouter();
  const { signup, setChurch, churches, isLoading: authLoading } = useAuth();

  const [step, setStep] = useState<"account" | "church">("account");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [selectedChurch, setSelectedChurch] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("이메일과 비밀번호를 입력해주세요.");
      return;
    }

    // 비밀번호 강도 검증: 8자 이상, 영문, 숫자, 특수문자 포함
    if (password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.");
      return;
    }

    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSymbol = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

    if (!hasLetter || !hasNumber || !hasSymbol) {
      setError("비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다.");
      return;
    }

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setIsLoading(true);
    try {
      await signup(email, password, name || undefined);
      setStep("church");
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원가입에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChurchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!selectedChurch) {
      setError("교회를 선택해주세요.");
      return;
    }

    setIsLoading(true);
    try {
      await setChurch(selectedChurch);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "교회 설정에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkipChurch = () => {
    router.push("/");
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <main className="flex-1 flex items-center justify-center px-4 py-8">
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

          {/* 회원가입 폼 */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
            {/* 단계 표시 */}
            <div className="flex items-center justify-center gap-2 mb-6">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${step === "account"
                  ? "bg-blue-500 text-white"
                  : "bg-green-500 text-white"
                  }`}
              >
                1
              </div>
              <div className="w-8 h-1 bg-gray-200 dark:bg-gray-600" />
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${step === "church"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 dark:bg-gray-600 text-gray-500"
                  }`}
              >
                2
              </div>
            </div>

            {step === "account" ? (
              <>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 text-center">
                  계정 생성
                </h2>

                <form onSubmit={handleAccountSubmit} className="space-y-4">
                  {/* 에러 메시지 */}
                  {error && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* 이름 (선택) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      이름 <span className="text-gray-400">(선택)</span>
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="홍길동"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        disabled={isLoading}
                      />
                    </div>
                  </div>

                  {/* 이메일 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      이메일
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your@email.com"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        disabled={isLoading}
                        required
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
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="영문+숫자+특수문자 8자 이상"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        disabled={isLoading}
                        required
                      />
                    </div>
                  </div>

                  {/* 비밀번호 확인 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      비밀번호 확인
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="비밀번호 재입력"
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        disabled={isLoading}
                        required
                      />
                    </div>
                  </div>

                  {/* 회원가입 버튼 */}
                  <button
                    type="submit"
                    disabled={isLoading || authLoading}
                    className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        처리 중...
                      </>
                    ) : (
                      "다음"
                    )}
                  </button>
                </form>
              </>
            ) : (
              <>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 text-center">
                  교회 선택
                </h2>

                <form onSubmit={handleChurchSubmit} className="space-y-4">
                  {/* 에러 메시지 */}
                  {error && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* 교회 선택 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      소속 교회
                    </label>
                    <div className="relative">
                      <Church className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <select
                        value={selectedChurch}
                        onChange={(e) => setSelectedChurch(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all appearance-none"
                        disabled={isLoading}
                      >
                        <option value="">교회를 선택하세요</option>
                        {churches.map((church) => (
                          <option key={church.id} value={church.id}>
                            {church.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <p className="mt-2 text-xs text-gray-400">
                      교회 목록에 없으면 관리자에게 문의하세요.
                    </p>
                  </div>

                  {/* 버튼 그룹 */}
                  <div className="space-y-2">
                    <button
                      type="submit"
                      disabled={isLoading || authLoading}
                      className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          처리 중...
                        </>
                      ) : (
                        "완료"
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleSkipChurch}
                      disabled={isLoading}
                      className="w-full py-3 text-gray-500 hover:text-gray-700 font-medium transition-colors"
                    >
                      나중에 설정하기
                    </button>
                  </div>
                </form>
              </>
            )}

            {/* 로그인 링크 */}
            {step === "account" && (
              <div className="mt-6 text-center text-sm text-gray-500">
                이미 계정이 있으신가요?{" "}
                <Link
                  href="/login"
                  className="text-blue-500 hover:text-blue-600 font-medium"
                >
                  로그인
                </Link>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
