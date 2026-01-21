"use client";

import { Sidebar } from "./Sidebar";
import Footer from "./Footer";

interface DashboardLayoutProps {
    children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    return (
        <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col min-h-screen bg-background">
                <main className="flex-1 overflow-auto">
                    {children}
                </main>
                <Footer />
            </div>
        </div>
    );
}
