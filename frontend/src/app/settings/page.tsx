"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Mail,
  Building2,
  Lock,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  LogOut,
  ChevronDown,
  BookText,
  Trash2,
  ArrowRight,
} from "lucide-react";
import { DashboardLayout } from "@/components";
import { useAuth } from "@/contexts/AuthContext";
import {
  getReplacementDictionary,
  deleteReplacementEntry,
  clearReplacementDictionary,
  type ReplacementEntry,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Church {
  id: string;
  name: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated, logout, refreshUser } = useAuth();

  // 프로필 정보
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [churchId, setChurchId] = useState("");
  const [churchName, setChurchName] = useState("");
  const [useCustomChurch, setUseCustomChurch] = useState(false);
  const [churches, setChurches] = useState<Church[]>([]);

  // 비밀번호 변경
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // 상태
  const [isUpdating, setIsUpdating] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // 치환 사전 상태
  const [dictionaryEntries, setDictionaryEntries] = useState<ReplacementEntry[]>([]);
  const [loadingDictionary, setLoadingDictionary] = useState(false);
  const [deletingEntry, setDeletingEntry] = useState<string | null>(null);

  // 인증 체크
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // 사용자 정보 로드
  useEffect(() => {
    if (user) {
      setName(user.name || "");
      setEmail(user.email || "");
      setChurchId(user.church_id || "");
      setChurchName(user.church_name || "");
      // 기존 교회가 목록에 없으면 직접 입력 모드로
      if (user.church_name && churches.length > 0) {
        const found = churches.find(c => c.id === user.church_id);
        if (!found && user.church_name) {
          setUseCustomChurch(true);
        }
      }
    }
  }, [user, churches]);

  // 교회 목록 로드
  useEffect(() => {
    const fetchChurches = async () => {
      try {
        const response = await fetch(`${API_URL}/api/auth/churches`);
        if (response.ok) {
          const data = await response.json();
          setChurches(data.churches || []);
        }
      } catch (error) {
        console.error("교회 목록 로드 실패:", error);
      }
    };
    fetchChurches();
  }, []);

  // 치환 사전 로드
  useEffect(() => {
    if (!user?.church_id) return;

    const fetchDictionary = async () => {
      setLoadingDictionary(true);
      try {
        const entries = await getReplacementDictionary(user.church_id!);
        setDictionaryEntries(entries);
      } catch (error) {
        console.error("치환 사전 로드 실패:", error);
      } finally {
        setLoadingDictionary(false);
      }
    };
    fetchDictionary();
  }, [user?.church_id]);

  // 치환 사전 항목 삭제
  const handleDeleteEntry = async (entryId: string) => {
    if (!user?.church_id) return;
    setDeletingEntry(entryId);
    try {
      await deleteReplacementEntry(user.church_id, entryId);
      setDictionaryEntries((prev) => prev.filter((e) => e.id !== entryId));
    } catch (error) {
      console.error("항목 삭제 실패:", error);
    } finally {
      setDeletingEntry(null);
    }
  };

  // 치환 사전 전체 삭제
  const handleClearDictionary = async () => {
    if (!user?.church_id) return;
    if (!confirm("모든 자동 치환 항목을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) return;

    setLoadingDictionary(true);
    try {
      await clearReplacementDictionary(user.church_id);
      setDictionaryEntries([]);
    } catch (error) {
      console.error("사전 삭제 실패:", error);
    } finally {
      setLoadingDictionary(false);
    }
  };

  // 프로필 업데이트
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setIsUpdating(true);

    try {
      const token = localStorage.getItem("qt_access_token");
      const response = await fetch(`${API_URL}/api/auth/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name,
          church_id: useCustomChurch ? null : (churchId || null),
          church_name: useCustomChurch ? churchName : null
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "프로필 업데이트 실패");
      }

      await refreshUser();
      setMessage({ type: "success", text: "프로필이 업데이트되었습니다." });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "오류가 발생했습니다." });
    } finally {
      setIsUpdating(false);
    }
  };

  // 비밀번호 변경
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMessage(null);

    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: "error", text: "새 비밀번호가 일치하지 않습니다." });
      return;
    }

    // 비밀번호 유효성 검사: 8자 이상, 문자+숫자+기호 포함
    const hasLetter = /[a-zA-Z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);
    const hasSymbol = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPassword);

    if (newPassword.length < 8) {
      setPasswordMessage({ type: "error", text: "비밀번호는 8자 이상이어야 합니다." });
      return;
    }

    if (!hasLetter || !hasNumber || !hasSymbol) {
      setPasswordMessage({ type: "error", text: "비밀번호는 문자, 숫자, 기호를 모두 포함해야 합니다." });
      return;
    }

    setIsChangingPassword(true);

    try {
      const token = localStorage.getItem("qt_access_token");
      const response = await fetch(`${API_URL}/api/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "비밀번호 변경 실패");
      }

      setPasswordMessage({ type: "success", text: "비밀번호가 변경되었습니다." });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setPasswordMessage({ type: "error", text: error instanceof Error ? error.message : "오류가 발생했습니다." });
    } finally {
      setIsChangingPassword(false);
    }
  };

  // 로그아웃
  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  // 로딩 중
  if (authLoading) {
    return (
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-muted-foreground">로딩 중...</div>
        </div>
      </DashboardLayout>
    );
  }

  // 인증되지 않음
  if (!isAuthenticated) {
    return null;
  }

  return (
    <DashboardLayout>
      {/* 헤더 */}
      <header className="bg-card border-b border-border px-8 py-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">설정</h1>
          <p className="text-sm text-muted-foreground mt-1">
            계정 정보 및 보안 설정을 관리합니다
          </p>
        </div>
      </header>

      <div className="p-8 space-y-8 max-w-2xl">
        {/* 프로필 정보 섹션 */}
        <section className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <User className="w-5 h-5" />
            프로필 정보
          </h2>

          <form onSubmit={handleUpdateProfile} className="space-y-4">
            {/* 메시지 */}
            {message && (
              <div
                className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                  message.type === "success"
                    ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                }`}
              >
                {message.type === "success" ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <AlertCircle className="w-4 h-4" />
                )}
                {message.text}
              </div>
            )}

            {/* 이름 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                이름
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="이름을 입력하세요"
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* 이메일 (읽기 전용) */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                이메일
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <div className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 select-none">
                  {email}
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-1">이메일은 변경할 수 없습니다</p>
            </div>

            {/* 교회 선택/입력 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                교회
              </label>

              {/* 선택/입력 토글 */}
              <div className="flex gap-2 mb-2">
                <button
                  type="button"
                  onClick={() => setUseCustomChurch(false)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    !useCustomChurch
                      ? "bg-primary text-primary-foreground"
                      : "bg-gray-100 dark:bg-gray-800 text-muted-foreground hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  목록에서 선택
                </button>
                <button
                  type="button"
                  onClick={() => setUseCustomChurch(true)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    useCustomChurch
                      ? "bg-primary text-primary-foreground"
                      : "bg-gray-100 dark:bg-gray-800 text-muted-foreground hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  직접 입력
                </button>
              </div>

              {!useCustomChurch ? (
                /* 드롭다운 선택 */
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <select
                    value={churchId}
                    onChange={(e) => setChurchId(e.target.value)}
                    className="w-full pl-10 pr-10 py-3 border border-border rounded-xl bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all appearance-none cursor-pointer"
                  >
                    <option value="">교회를 선택하세요</option>
                    {churches.map((church) => (
                      <option key={church.id} value={church.id}>
                        {church.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
                </div>
              ) : (
                /* 직접 입력 */
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <input
                    type="text"
                    value={churchName}
                    onChange={(e) => setChurchName(e.target.value)}
                    placeholder="교회 이름을 입력하세요"
                    className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                  />
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                {useCustomChurch ? "교회 이름을 직접 입력해주세요" : "등록된 교회 목록에서 선택하세요"}
              </p>
            </div>

            {/* 저장 버튼 */}
            <button
              type="submit"
              disabled={isUpdating}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-primary text-primary-foreground font-medium rounded-xl hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {isUpdating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  저장 중...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  프로필 저장
                </>
              )}
            </button>
          </form>
        </section>

        {/* 자동 치환 사전 섹션 */}
        <section className="bg-card rounded-xl border border-border p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <BookText className="w-5 h-5" />
              자동 치환 사전
            </h2>
            {dictionaryEntries.length > 0 && (
              <button
                onClick={handleClearDictionary}
                disabled={loadingDictionary}
                className="text-sm text-red-500 hover:text-red-600 transition-colors"
              >
                전체 삭제
              </button>
            )}
          </div>

          <p className="text-sm text-muted-foreground mb-4">
            자막을 수정하면 자동으로 치환 사전에 저장됩니다. 이후 새 영상의 자막에서 동일한 오류가 자동으로 수정됩니다.
          </p>

          {loadingDictionary ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : dictionaryEntries.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <BookText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>저장된 치환 항목이 없습니다</p>
              <p className="text-xs mt-1">자막 편집 시 수정한 내용이 자동으로 저장됩니다</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {dictionaryEntries.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between p-3 bg-muted rounded-lg group"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-sm text-red-500 line-through truncate">
                      {entry.original}
                    </span>
                    <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm text-green-600 font-medium truncate">
                      {entry.replacement}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 ml-2">
                    <span className="text-xs text-muted-foreground">
                      {entry.use_count}회 적용
                    </span>
                    <button
                      onClick={() => handleDeleteEntry(entry.id)}
                      disabled={deletingEntry === entry.id}
                      className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                      {deletingEntry === entry.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 비밀번호 변경 섹션 */}
        <section className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <Lock className="w-5 h-5" />
            비밀번호 변경
          </h2>

          <form onSubmit={handleChangePassword} className="space-y-4">
            {/* 메시지 */}
            {passwordMessage && (
              <div
                className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                  passwordMessage.type === "success"
                    ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                }`}
              >
                {passwordMessage.type === "success" ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <AlertCircle className="w-4 h-4" />
                )}
                {passwordMessage.text}
              </div>
            )}

            {/* 현재 비밀번호 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                현재 비밀번호
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="현재 비밀번호"
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* 새 비밀번호 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                새 비밀번호
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="새 비밀번호 (8자 이상, 문자+숫자+기호)"
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* 비밀번호 확인 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                새 비밀번호 확인
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="새 비밀번호 확인"
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* 변경 버튼 */}
            <button
              type="submit"
              disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-primary text-primary-foreground font-medium rounded-xl hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {isChangingPassword ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  변경 중...
                </>
              ) : (
                <>
                  <Lock className="w-5 h-5" />
                  비밀번호 변경
                </>
              )}
            </button>
          </form>
        </section>

        {/* 계정 관리 섹션 */}
        <section className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold text-foreground mb-6">계정 관리</h2>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <div>
                <p className="font-medium text-foreground">로그아웃</p>
                <p className="text-sm text-muted-foreground">현재 기기에서 로그아웃합니다</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                로그아웃
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <p className="font-medium text-foreground">사용자 ID</p>
                <p className="text-sm text-muted-foreground font-mono">{user?.id}</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <p className="font-medium text-foreground">역할</p>
                <p className="text-sm text-muted-foreground">{user?.role === "admin" ? "관리자" : "일반 사용자"}</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
