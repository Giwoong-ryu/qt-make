import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "QT Video - 교회 묵상 영상 자동화",
  description: "목사님 음성(MP3)을 업로드하면 10분 내 배경 영상이 자동 생성됩니다.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        {/* Google Fonts for Thumbnail Editor */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Do+Hyeon&family=Gaegu&family=Gamja+Flower&family=Gothic+A1:wght@400;700&family=Gowun+Batang&family=Gugi&family=Hahmlet:wght@400;700&family=Hi+Melody&family=IBM+Plex+Sans+KR:wght@400;700&family=Jua&family=Nanum+Brush+Script&family=Nanum+Gothic:wght@400;700&family=Nanum+Myeongjo:wght@400;700&family=Nanum+Pen+Script&family=Noto+Sans+KR:wght@400;700&family=Noto+Serif+KR:wght@400;700&family=Poor+Story&display=swap"
          rel="stylesheet"
        />
        {/* 나눔스퀘어라운드 폰트 (Naver CDN) */}
        <link
          href="https://hangeul.pstatic.net/hangeul_static/css/nanum-square-round.css"
          rel="stylesheet"
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
