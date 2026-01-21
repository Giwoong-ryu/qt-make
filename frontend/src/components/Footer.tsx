'use client';

import Link from 'next/link';

export default function Footer() {
    return (
        <footer className="bg-stone-100 border-t border-stone-200 mt-auto">
            <div className="max-w-6xl mx-auto px-6 py-10">
                {/* 상단: 링크 영역 */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
                    {/* 로고/서비스명 */}
                    <div>
                        <h3 className="text-lg font-bold text-stone-800">QT Video</h3>
                        <p className="text-sm text-stone-500 mt-1">
                            교회 묵상 영상 자동화 서비스
                        </p>
                    </div>

                    {/* 링크들 */}
                    <div className="flex flex-wrap gap-6 text-sm">
                        <Link
                            href="/terms"
                            className="text-stone-600 hover:text-indigo-600 transition-colors"
                        >
                            이용약관
                        </Link>
                        <Link
                            href="/privacy"
                            className="text-stone-600 hover:text-indigo-600 transition-colors"
                        >
                            개인정보처리방침
                        </Link>
                        <Link
                            href="/refund"
                            className="text-stone-600 hover:text-indigo-600 transition-colors"
                        >
                            환불정책
                        </Link>
                        <a
                            href="mailto:eazypick.service@gmail.com"
                            className="text-stone-600 hover:text-indigo-600 transition-colors"
                        >
                            고객문의
                        </a>
                    </div>
                </div>

                {/* 구분선 */}
                <div className="border-t border-stone-200 pt-6">
                    {/* 사업자 정보 */}
                    <div className="text-xs text-stone-500 space-y-1">
                        <p>
                            <span className="font-medium">상호:</span> 이지픽 |
                            <span className="font-medium ml-2">대표:</span> 유기웅 |
                            <span className="font-medium ml-2">사업자등록번호:</span> 780-06-03347
                        </p>
                        <p>
                            <span className="font-medium">주소:</span> 부산광역시 연제구 연수로240번길 8(연산동)
                        </p>
                        <p>
                            <span className="font-medium">이메일:</span>{' '}
                            <a
                                href="mailto:eazypick.service@gmail.com"
                                className="hover:text-indigo-600 transition-colors"
                            >
                                eazypick.service@gmail.com
                            </a>
                        </p>
                    </div>

                    {/* 저작권 */}
                    <p className="text-xs text-stone-400 mt-4">
                        © {new Date().getFullYear()} 이지픽. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    );
}
