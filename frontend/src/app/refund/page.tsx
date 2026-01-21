import Footer from '@/components/Footer';

export default function RefundPage() {
    return (
        <div className="min-h-screen flex flex-col bg-stone-50">
            <main className="flex-1 max-w-4xl mx-auto px-6 py-12">
                <h1 className="text-3xl font-bold text-stone-800 mb-8">환불정책</h1>

                <div className="prose prose-stone max-w-none space-y-8">
                    <p className="text-stone-600 leading-relaxed text-lg">
                        이지픽의 QT Video 서비스는 고객 만족을 최우선으로 생각합니다.
                        아래 환불 정책을 참고하여 주시기 바랍니다.
                    </p>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제1조 (정기구독 환불)</h2>
                        <div className="bg-indigo-50 border border-indigo-200 p-4 rounded-lg mb-4">
                            <p className="text-indigo-800 font-medium">
                                💡 정기구독은 언제든지 해지할 수 있으며, 해지 시점까지 사용한 기간에 대한 요금만 청구됩니다.
                            </p>
                        </div>
                        <ol className="list-decimal list-inside text-stone-600 space-y-3">
                            <li>
                                <strong>첫 결제 후 7일 이내:</strong> 서비스 이용 크레딧을 1회 이하 사용한 경우,
                                전액 환불이 가능합니다.
                            </li>
                            <li>
                                <strong>첫 결제 후 7일 이후:</strong> 정기구독 해지만 가능하며,
                                남은 기간에 대한 환불은 제공되지 않습니다. 단, 해지 시점까지 서비스는
                                정상적으로 이용 가능합니다.
                            </li>
                            <li>
                                <strong>자동 갱신:</strong> 정기구독은 매월 자동으로 갱신됩니다.
                                갱신을 원치 않으시면 다음 결제일 최소 1일 전까지 해지해 주세요.
                            </li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제2조 (환불 불가 사유)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            다음의 경우에는 환불이 제한됩니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2">
                            <li>이미 사용한 크레딧(영상 생성 완료)에 해당하는 금액</li>
                            <li>회원 본인의 실수로 인한 중복 결제 (결제 후 24시간 이내 고객센터 문의 시 예외)</li>
                            <li>약관을 위반하여 서비스 이용이 제한된 경우</li>
                            <li>프로모션 또는 할인 적용 상품 (별도 명시된 경우 제외)</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제3조 (환불 절차)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-3">
                            <li>
                                <strong>환불 신청:</strong> 고객센터 이메일{' '}
                                <a href="mailto:eazypick.service@gmail.com" className="text-indigo-600 hover:underline">
                                    eazypick.service@gmail.com
                                </a>
                                으로 환불 요청
                            </li>
                            <li>
                                <strong>필요 정보:</strong> 가입 이메일, 결제일, 환불 사유
                            </li>
                            <li>
                                <strong>검토 및 승인:</strong> 영업일 기준 3일 이내 검토 후 회신
                            </li>
                            <li>
                                <strong>환불 처리:</strong> 승인 후 영업일 기준 5~7일 이내 원결제 수단으로 환불
                            </li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제4조 (구독 해지 방법)</h2>
                        <div className="bg-stone-100 p-4 rounded-lg">
                            <ol className="list-decimal list-inside text-stone-600 space-y-2">
                                <li>QT Video 서비스 로그인</li>
                                <li>설정 → 구독 관리 메뉴 이동</li>
                                <li>&quot;구독 해지&quot; 버튼 클릭</li>
                                <li>해지 사유 선택 후 확인</li>
                            </ol>
                            <p className="text-stone-500 text-sm mt-4">
                                * 해지 후에도 결제 기간이 남아있다면 해당 기간까지는 서비스를 정상 이용할 수 있습니다.
                            </p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제5조 (결제 취소)</h2>
                        <ul className="list-disc list-inside text-stone-600 space-y-2">
                            <li>
                                <strong>신용카드:</strong> 취소 후 카드사에 따라 3~7 영업일 소요
                            </li>
                            <li>
                                <strong>간편결제:</strong> 취소 후 결제 서비스에 따라 1~5 영업일 소요
                            </li>
                        </ul>
                        <p className="text-stone-500 text-sm mt-4">
                            * 환불 일정은 카드사 및 결제 서비스 사업자의 정책에 따라 달라질 수 있습니다.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제6조 (문의)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            환불 및 결제와 관련하여 궁금한 사항이 있으시면 언제든지 고객센터로 연락해 주세요.
                        </p>
                        <div className="bg-indigo-50 border border-indigo-200 p-4 rounded-lg mt-4">
                            <p className="text-stone-700">
                                <strong>고객센터</strong><br />
                                이메일:{' '}
                                <a href="mailto:eazypick.service@gmail.com" className="text-indigo-600 hover:underline">
                                    eazypick.service@gmail.com
                                </a><br />
                                운영시간: 평일 10:00 ~ 18:00 (주말/공휴일 휴무)
                            </p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">부칙</h2>
                        <p className="text-stone-600">
                            본 환불정책은 2025년 8월 3일부터 시행합니다.
                        </p>
                    </section>
                </div>
            </main>

            <Footer />
        </div>
    );
}
