import Footer from '@/components/Footer';

export default function PrivacyPage() {
    return (
        <div className="min-h-screen flex flex-col bg-stone-50">
            <main className="flex-1 max-w-4xl mx-auto px-6 py-12">
                <h1 className="text-3xl font-bold text-stone-800 mb-8">개인정보처리방침</h1>

                <div className="prose prose-stone max-w-none space-y-8">
                    <p className="text-stone-600 leading-relaxed">
                        이지픽(이하 &quot;회사&quot;)은 개인정보보호법에 따라 이용자의 개인정보 보호 및 권익을
                        보호하고 개인정보와 관련한 이용자의 고충을 원활하게 처리할 수 있도록 다음과 같은
                        처리방침을 두고 있습니다.
                    </p>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제1조 (개인정보의 수집 항목 및 수집 방법)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            회사는 서비스 제공을 위해 다음과 같은 개인정보를 수집하고 있습니다:
                        </p>
                        <div className="bg-stone-100 p-4 rounded-lg">
                            <h4 className="font-medium text-stone-700 mb-2">필수 수집 항목</h4>
                            <ul className="list-disc list-inside text-stone-600 space-y-1">
                                <li>이메일 주소</li>
                                <li>비밀번호 (암호화 저장)</li>
                                <li>서비스 이용 기록</li>
                            </ul>
                        </div>
                        <div className="bg-stone-100 p-4 rounded-lg mt-4">
                            <h4 className="font-medium text-stone-700 mb-2">결제 시 수집 항목</h4>
                            <ul className="list-disc list-inside text-stone-600 space-y-1">
                                <li>결제 정보 (카드사명, 카드번호 일부)</li>
                                <li>결제 내역</li>
                            </ul>
                        </div>
                        <p className="text-stone-600 mt-4">
                            <strong>수집 방법:</strong> 회원가입, 서비스 이용, 결제
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제2조 (개인정보의 수집 및 이용 목적)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            회사는 수집한 개인정보를 다음의 목적을 위해 활용합니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2">
                            <li><strong>서비스 제공:</strong> 영상 생성, 콘텐츠 저장 및 제공</li>
                            <li><strong>회원 관리:</strong> 회원 식별, 불량회원 제재, 고지사항 전달</li>
                            <li><strong>결제 처리:</strong> 유료 서비스 결제 및 정산</li>
                            <li><strong>서비스 개선:</strong> 서비스 이용 통계 분석 및 개선</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제3조 (개인정보의 보유 및 이용 기간)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            회사는 개인정보 수집 및 이용목적이 달성된 후에는 해당 정보를 지체 없이 파기합니다.
                            단, 관계법령에 따라 보존할 필요가 있는 경우 아래와 같이 보관합니다:
                        </p>
                        <div className="overflow-x-auto">
                            <table className="min-w-full border border-stone-200 text-sm">
                                <thead className="bg-stone-100">
                                    <tr>
                                        <th className="border border-stone-200 px-4 py-2 text-left">보존 항목</th>
                                        <th className="border border-stone-200 px-4 py-2 text-left">보존 근거</th>
                                        <th className="border border-stone-200 px-4 py-2 text-left">보존 기간</th>
                                    </tr>
                                </thead>
                                <tbody className="text-stone-600">
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">계약 또는 청약철회 등에 관한 기록</td>
                                        <td className="border border-stone-200 px-4 py-2">전자상거래법</td>
                                        <td className="border border-stone-200 px-4 py-2">5년</td>
                                    </tr>
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">대금결제 및 재화 등의 공급에 관한 기록</td>
                                        <td className="border border-stone-200 px-4 py-2">전자상거래법</td>
                                        <td className="border border-stone-200 px-4 py-2">5년</td>
                                    </tr>
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">소비자의 불만 또는 분쟁처리에 관한 기록</td>
                                        <td className="border border-stone-200 px-4 py-2">전자상거래법</td>
                                        <td className="border border-stone-200 px-4 py-2">3년</td>
                                    </tr>
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">웹사이트 방문기록</td>
                                        <td className="border border-stone-200 px-4 py-2">통신비밀보호법</td>
                                        <td className="border border-stone-200 px-4 py-2">3개월</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제4조 (개인정보의 제3자 제공)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            회사는 원칙적으로 이용자의 개인정보를 외부에 제공하지 않습니다.
                            다만, 아래의 경우에는 예외로 합니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2 mt-2">
                            <li>이용자가 사전에 동의한 경우</li>
                            <li>법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제5조 (개인정보 처리의 위탁)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            회사는 서비스 향상을 위해 다음과 같이 개인정보 처리 업무를 위탁하고 있습니다:
                        </p>
                        <div className="overflow-x-auto">
                            <table className="min-w-full border border-stone-200 text-sm">
                                <thead className="bg-stone-100">
                                    <tr>
                                        <th className="border border-stone-200 px-4 py-2 text-left">수탁업체</th>
                                        <th className="border border-stone-200 px-4 py-2 text-left">위탁업무 내용</th>
                                    </tr>
                                </thead>
                                <tbody className="text-stone-600">
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">Supabase</td>
                                        <td className="border border-stone-200 px-4 py-2">데이터베이스 호스팅, 인증 서비스</td>
                                    </tr>
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">PortOne (구 아임포트)</td>
                                        <td className="border border-stone-200 px-4 py-2">결제 처리</td>
                                    </tr>
                                    <tr>
                                        <td className="border border-stone-200 px-4 py-2">Cloudflare</td>
                                        <td className="border border-stone-200 px-4 py-2">콘텐츠 저장 및 전송</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제6조 (이용자의 권리와 그 행사방법)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            이용자는 언제든지 다음 각 호의 개인정보 보호 관련 권리를 행사할 수 있습니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2 mt-2">
                            <li>개인정보 열람 요구</li>
                            <li>오류 등이 있을 경우 정정 요구</li>
                            <li>삭제 요구</li>
                            <li>처리정지 요구</li>
                        </ul>
                        <p className="text-stone-600 mt-4">
                            위 권리 행사는 <a href="mailto:eazypick.service@gmail.com" className="text-indigo-600 hover:underline">eazypick.service@gmail.com</a>으로
                            연락 주시면 지체 없이 조치하겠습니다.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제7조 (개인정보의 파기)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            회사는 개인정보 보유기간의 경과, 처리목적 달성 등 개인정보가 불필요하게 되었을 때에는
                            지체 없이 해당 개인정보를 파기합니다.
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2 mt-2">
                            <li><strong>전자적 파일 형태:</strong> 복구 및 재생이 불가능하도록 안전하게 삭제</li>
                            <li><strong>종이 문서:</strong> 분쇄기로 분쇄하거나 소각</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제8조 (개인정보 보호책임자)</h2>
                        <div className="bg-stone-100 p-4 rounded-lg">
                            <p className="text-stone-600">
                                <strong>개인정보 보호책임자</strong><br />
                                성명: 유기웅<br />
                                직책: 대표<br />
                                이메일: <a href="mailto:eazypick.service@gmail.com" className="text-indigo-600 hover:underline">eazypick.service@gmail.com</a>
                            </p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제9조 (개인정보 처리방침 변경)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            이 개인정보처리방침은 시행일로부터 적용되며, 법령 및 방침에 따른 변경내용의
                            추가, 삭제 및 정정이 있을 경우에는 변경사항의 시행 7일 전부터 공지사항을 통하여
                            고지할 것입니다.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">부칙</h2>
                        <p className="text-stone-600">
                            본 방침은 2025년 8월 3일부터 시행합니다.
                        </p>
                    </section>
                </div>
            </main>

            <Footer />
        </div>
    );
}
