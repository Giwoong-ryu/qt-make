import Footer from '@/components/Footer';

export default function TermsPage() {
    return (
        <div className="min-h-screen flex flex-col bg-stone-50">
            <main className="flex-1 max-w-4xl mx-auto px-6 py-12">
                <h1 className="text-3xl font-bold text-stone-800 mb-8">이용약관</h1>

                <div className="prose prose-stone max-w-none space-y-8">
                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제1조 (목적)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            본 약관은 이지픽(이하 &quot;회사&quot;)이 제공하는 QT Video 서비스(이하 &quot;서비스&quot;)의
                            이용조건 및 절차, 회사와 이용자의 권리, 의무 및 책임사항 등을 규정함을 목적으로 합니다.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제2조 (정의)</h2>
                        <ul className="list-disc list-inside text-stone-600 space-y-2">
                            <li>&quot;서비스&quot;란 회사가 제공하는 교회 묵상 영상 자동 생성 서비스를 말합니다.</li>
                            <li>&quot;이용자&quot;란 본 약관에 동의하고 서비스를 이용하는 자를 말합니다.</li>
                            <li>&quot;회원&quot;이란 회사에 개인정보를 제공하여 회원등록을 한 자를 말합니다.</li>
                            <li>&quot;콘텐츠&quot;란 회원이 서비스를 통해 생성하거나 업로드한 영상, 음성, 텍스트 등을 말합니다.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제3조 (약관의 효력 및 변경)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>본 약관은 서비스 화면에 게시하거나 기타의 방법으로 이용자에게 공지함으로써 효력이 발생합니다.</li>
                            <li>회사는 필요한 경우 관련 법령을 위배하지 않는 범위에서 본 약관을 변경할 수 있습니다.</li>
                            <li>약관이 변경될 경우 회사는 변경 내용을 시행일 7일 전부터 공지합니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제4조 (서비스의 제공)</h2>
                        <p className="text-stone-600 leading-relaxed mb-4">
                            회사는 다음과 같은 서비스를 제공합니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2">
                            <li>음성 파일(MP3) 기반 자동 자막 생성</li>
                            <li>AI 기반 배경 영상 자동 매칭</li>
                            <li>썸네일 자동 생성 및 편집</li>
                            <li>영상 편집 및 다운로드</li>
                            <li>기타 회사가 정하는 서비스</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제5조 (이용요금 및 결제)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>서비스 이용요금은 서비스 내 가격표에 따릅니다.</li>
                            <li>유료 서비스의 결제는 신용카드, 간편결제 등 회사가 정한 방법으로 합니다.</li>
                            <li>정기결제(구독)는 매월 자동으로 갱신되며, 해지 전까지 계속됩니다.</li>
                            <li>결제와 관련된 상세 내용은 환불정책을 참고하시기 바랍니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제6조 (회원의 의무)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>회원은 관계 법령, 본 약관의 규정, 이용안내 등을 준수하여야 합니다.</li>
                            <li>회원은 타인의 저작권을 침해하는 콘텐츠를 업로드하지 않아야 합니다.</li>
                            <li>회원은 계정 정보를 안전하게 관리할 책임이 있습니다.</li>
                            <li>회원은 불법적이거나 부적절한 목적으로 서비스를 이용하지 않아야 합니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제7조 (회사의 의무)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>회사는 관련 법령을 준수하며, 지속적이고 안정적인 서비스를 제공하기 위해 노력합니다.</li>
                            <li>회사는 회원의 개인정보를 보호하며, 개인정보처리방침에 따라 관리합니다.</li>
                            <li>회사는 서비스 이용과 관련하여 회원으로부터 제기된 의견이나 불만을 적극 처리합니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제8조 (서비스 이용 제한)</h2>
                        <p className="text-stone-600 leading-relaxed">
                            회사는 다음 각 호에 해당하는 경우 서비스 이용을 제한하거나 회원 자격을
                            상실시킬 수 있습니다:
                        </p>
                        <ul className="list-disc list-inside text-stone-600 space-y-2 mt-2">
                            <li>가입 시 허위 정보를 기재한 경우</li>
                            <li>타인의 서비스 이용을 방해하거나 정보를 도용한 경우</li>
                            <li>법령 또는 공서양속에 반하는 행위를 한 경우</li>
                            <li>기타 본 약관을 위반한 경우</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제9조 (저작권)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>서비스에서 제공하는 배경 영상, 음악 등의 저작권은 해당 원저작자에게 있습니다.</li>
                            <li>회원이 서비스를 통해 생성한 콘텐츠의 저작권은 회원에게 있습니다.</li>
                            <li>회원은 생성된 콘텐츠를 교회 내 비영리 목적으로 사용할 수 있습니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제10조 (면책조항)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>회사는 천재지변, 전쟁 등 불가항력적 사유로 서비스를 제공할 수 없는 경우 책임이 면제됩니다.</li>
                            <li>회사는 회원의 귀책사유로 인한 서비스 이용 장애에 대해 책임을 지지 않습니다.</li>
                            <li>회사는 회원이 서비스를 이용하여 기대하는 결과를 보장하지 않습니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">제11조 (분쟁해결)</h2>
                        <ol className="list-decimal list-inside text-stone-600 space-y-2">
                            <li>회사와 회원 간 분쟁이 발생할 경우, 양 당사자는 분쟁 해결을 위해 성실히 협의합니다.</li>
                            <li>협의가 이루어지지 않을 경우, 관할 법원은 회사 소재지 법원으로 합니다.</li>
                        </ol>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-stone-700 mb-4">부칙</h2>
                        <p className="text-stone-600">
                            본 약관은 2025년 8월 3일부터 시행합니다.
                        </p>
                    </section>
                </div>
            </main>

            <Footer />
        </div>
    );
}
