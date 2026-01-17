"use client";

import { Sidebar } from "./Sidebar";

interface DashboardLayoutProps {
    children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    return (
        <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 bg-background overflow-auto">
                {children}
            </main>
        </div>
    );
}
