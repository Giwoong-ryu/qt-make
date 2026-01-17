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
        } h-screen bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300`}
    >
      {/* 로고 영역 */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-sidebar-border">
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

      {/* 네비게이션 */}
      <nav className="flex-1 px-2 py-4 space-y-1">
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

      {/* 유저 프로필 영역 */}
      <div className="border-t border-sidebar-border p-3">
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
