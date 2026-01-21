"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Video,
  Layers,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  CreditCard,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { href: "/", label: "대시보드", icon: <LayoutDashboard className="w-5 h-5" /> },
  { href: "/videos", label: "내 영상", icon: <Video className="w-5 h-5" /> },
  { href: "/resources", label: "배경 설정", icon: <Layers className="w-5 h-5" /> },
  { href: "/settings", label: "설정", icon: <Settings className="w-5 h-5" /> },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <aside
      className={`${collapsed ? "w-16" : "w-56"
        } h-screen bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300 overflow-hidden`}
    >
      {/* 로고 영역 */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-sidebar-border shrink-0">
        {!collapsed && (
          <h1 className="text-lg font-bold text-sidebar-foreground">
            QT Video
          </h1>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-md hover:bg-sidebar-accent text-sidebar-foreground transition-colors"
          aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* 네비게이션 - 스크롤 가능 */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent"
                }`}
              title={collapsed ? item.label : undefined}
            >
              {item.icon}
              {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 구독 관리 영역 - 고정 */}
      {!collapsed && (
        <div className="px-3 py-3 border-t border-sidebar-border shrink-0">
          {user?.subscription_plan === "free" ? (
            <Link
              href="/subscription"
              className="block p-3 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium opacity-90">무료 플랜</span>
                <CreditCard className="w-4 h-4 opacity-90" />
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold">{user?.weekly_credits || 0}</span>
                <span className="text-sm opacity-90">/ 10</span>
              </div>
              <p className="text-xs opacity-75 mt-1">이번 주 남은 크레딧</p>
            </Link>
          ) : user?.subscription_plan === "enterprise" ? (
            <Link
              href="/subscription"
              className="block p-3 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium opacity-90">엔터프라이즈</span>
                <Zap className="w-4 h-4 opacity-90" />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">∞</span>
                <span className="text-sm opacity-90">무제한</span>
              </div>
              <p className="text-xs opacity-75 mt-1">제한 없이 사용 가능</p>
            </Link>
          ) : (
            <Link
              href="/subscription"
              className="block p-3 rounded-lg bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium opacity-90">
                  {user?.subscription_plan === "basic" ? "베이직" : "프로"}
                </span>
                <CreditCard className="w-4 h-4 opacity-90" />
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold">{user?.weekly_credits || 0}</span>
                <span className="text-sm opacity-90">
                  / {user?.subscription_plan === "basic" ? "50" : "200"}
                </span>
              </div>
              <p className="text-xs opacity-75 mt-1">이번 주 남은 크레딧</p>
            </Link>
          )}
        </div>
      )}

      {/* 유저 프로필 영역 - 고정 */}
      <div className="border-t border-sidebar-border p-3 shrink-0">
        <div className="flex items-center gap-3">
          {/* 아바타 - 클릭 시 설정으로 이동 */}
          <Link
            href="/settings"
            className="w-9 h-9 rounded-full bg-sidebar-accent flex items-center justify-center text-sidebar-foreground font-medium text-sm hover:ring-2 hover:ring-primary transition-all"
            title="설정"
          >
            {user?.name?.charAt(0) || user?.email?.charAt(0) || "U"}
          </Link>

          {!collapsed && (
            <Link href="/settings" className="flex-1 min-w-0 hover:opacity-80 transition-opacity">
              <p className="text-sm font-medium text-sidebar-foreground truncate">
                {user?.name || "사용자"}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {user?.email}
              </p>
            </Link>
          )}

          {!collapsed && (
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-sidebar-accent transition-colors"
              title="로그아웃"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
