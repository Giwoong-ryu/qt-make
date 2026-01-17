'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import {
    Move,
    Type,
    Palette,
    Download,
    RotateCcw,
    Save,
    Loader2,
    Bookmark,
    BookmarkCheck,
    Star,
    PlayCircle,
    Clock,
    Image as ImageIcon,
    StopCircle,
} from 'lucide-react';

// 텍스트 박스 타입
interface TextBox {
    id: string;
    label: string;
    text: string;
    x: number;  // 0-100 (퍼센트)
    y: number;  // 0-100 (퍼센트)
    fontSize: number;  // px
    fontFamily: string;
    color: string;
    visible: boolean;
}

// 인트로 설정
export interface IntroSettings {
    useAsIntro: boolean;      // 썸네일을 인트로로도 사용
    introDuration: number;    // 인트로 길이 (초)
    separateIntro: boolean;   // 별도 인트로 사용 여부
    separateIntroImageUrl?: string;  // 별도 인트로 이미지 URL
    useAsOutro?: boolean;     // 배경 이미지를 아웃트로로 사용
    outroDuration?: number;   // 아웃트로 길이 (초)
}

// 저장되는 레이아웃 설정
export interface ThumbnailLayout {
    textBoxes: TextBox[];
    backgroundImageUrl?: string;
    introSettings?: IntroSettings;  // 인트로 설정 추가
}

interface ThumbnailEditorProps {
    backgroundImageUrl: string;
    initialLayout?: ThumbnailLayout;
    mainTitle?: string;
    subTitle?: string;
    dateText?: string;
    bibleVerse?: string;
    onSave?: (layout: ThumbnailLayout) => void;
    onGenerate?: (layout: ThumbnailLayout) => void;
    onChangeBackground?: () => void;  // 배경 변경 콜백
    // 인트로 관련
    introSettings?: IntroSettings;
    onIntroSettingsChange?: (settings: IntroSettings) => void;
}

// 폰트 옵션 (20개) - 카테고리별 분류
const FONT_OPTIONS = [
    // 고딕 계열
    { value: 'Nanum Gothic', label: '나눔고딕', category: 'gothic', preview: '가나다ABC' },
    { value: 'Noto Sans KR', label: 'Noto Sans', category: 'gothic', preview: '가나다ABC' },
    { value: 'Pretendard', label: 'Pretendard', category: 'gothic', preview: '가나다ABC' },
    { value: 'Spoqa Han Sans Neo', label: '스포카 한 산스', category: 'gothic', preview: '가나다ABC' },
    { value: 'IBM Plex Sans KR', label: 'IBM Plex Sans', category: 'gothic', preview: '가나다ABC' },
    { value: 'Gothic A1', label: 'Gothic A1', category: 'gothic', preview: '가나다ABC' },
    { value: 'Do Hyeon', label: '도현', category: 'gothic', preview: '가나다ABC' },
    { value: 'Jua', label: '주아', category: 'gothic', preview: '가나다ABC' },
    // 명조/세리프 계열
    { value: 'Nanum Myeongjo', label: '나눔명조', category: 'serif', preview: '가나다ABC' },
    { value: 'Noto Serif KR', label: 'Noto Serif', category: 'serif', preview: '가나다ABC' },
    { value: 'Gowun Batang', label: '고운바탕', category: 'serif', preview: '가나다ABC' },
    { value: 'Hahmlet', label: '함렛', category: 'serif', preview: '가나다ABC' },
    // 손글씨/캘리 계열
    { value: 'Nanum Pen Script', label: '나눔펜', category: 'handwriting', preview: '가나다ABC' },
    { value: 'Nanum Brush Script', label: '나눔붓', category: 'handwriting', preview: '가나다ABC' },
    { value: 'Gamja Flower', label: '감자꽃', category: 'handwriting', preview: '가나다ABC' },
    { value: 'Hi Melody', label: '하이멜로디', category: 'handwriting', preview: '가나다ABC' },
    { value: 'Poor Story', label: '푸어스토리', category: 'handwriting', preview: '가나다ABC' },
    { value: 'Gaegu', label: '개구', category: 'handwriting', preview: '가나다ABC' },
    // 디스플레이/타이틀용
    { value: 'Black Han Sans', label: '검정 한 산스', category: 'display', preview: '가나다ABC' },
    { value: 'Gugi', label: '구기', category: 'display', preview: '가나다ABC' },
];

// 폰트 카테고리
const FONT_CATEGORIES = [
    { id: 'all', label: '전체' },
    { id: 'bookmarked', label: '즐겨찾기', icon: Star },
];

// 로컬 스토리지 키
const BOOKMARKED_FONTS_KEY = 'thumbnail-editor-bookmarked-fonts';

// 인트로 길이 옵션
const INTRO_DURATION_OPTIONS = [
    { value: 2, label: '2초' },
    { value: 3, label: '3초 (권장)' },
    { value: 4, label: '4초' },
    { value: 5, label: '5초' },
];

// 아웃트로 길이 옵션
const OUTRO_DURATION_OPTIONS = [
    { value: 2, label: '2초' },
    { value: 3, label: '3초 (권장)' },
    { value: 4, label: '4초' },
    { value: 5, label: '5초' },
];

// 기본 인트로 설정
const DEFAULT_INTRO_SETTINGS: IntroSettings = {
    useAsIntro: true,
    introDuration: 3,
    separateIntro: false,
    separateIntroImageUrl: undefined,
    useAsOutro: true,
    outroDuration: 3,
};

// 기본 텍스트 박스 설정
const createDefaultTextBoxes = (
    mainTitle = '',
    subTitle = '',
    dateText = '',
    bibleVerse = ''
): TextBox[] => [
        {
            id: 'main',
            label: '메인 제목',
            text: mainTitle,
            x: 50,
            y: 15,
            fontSize: 48,
            fontFamily: 'Nanum Gothic',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'sub',
            label: '서브 제목',
            text: subTitle,
            x: 50,
            y: 30,
            fontSize: 32,
            fontFamily: 'Nanum Gothic',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'date',
            label: '날짜',
            text: dateText,
            x: 50,
            y: 42,
            fontSize: 24,
            fontFamily: 'Nanum Gothic',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'verse',
            label: '성경 구절',
            text: bibleVerse,
            x: 85,
            y: 88,
            fontSize: 28,
            fontFamily: 'Nanum Gothic',
            color: '#FFFFFF',
            visible: true,
        },
    ];

export default function ThumbnailEditor({
    backgroundImageUrl,
    initialLayout,
    mainTitle = '',
    subTitle = '',
    dateText = '',
    bibleVerse = '',
    onSave,
    onGenerate,
    onChangeBackground,
    introSettings: externalIntroSettings,
    onIntroSettingsChange,
}: ThumbnailEditorProps) {
    const canvasRef = useRef<HTMLDivElement>(null);
    const [textBoxes, setTextBoxes] = useState<TextBox[]>(
        initialLayout?.textBoxes || createDefaultTextBoxes(mainTitle, subTitle, dateText, bibleVerse)
    );
    const [selectedBox, setSelectedBox] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [generating, setGenerating] = useState(false);

    // 폰트 선택 UI 상태
    const [fontCategory, setFontCategory] = useState<string>('all');
    const [bookmarkedFonts, setBookmarkedFonts] = useState<string[]>([]);

    // 인트로 설정 상태 (외부에서 전달받거나 기본값 사용)
    const [localIntroSettings, setLocalIntroSettings] = useState<IntroSettings>(
        externalIntroSettings || initialLayout?.introSettings || DEFAULT_INTRO_SETTINGS
    );

    // 북마크 로드
    useEffect(() => {
        const saved = localStorage.getItem(BOOKMARKED_FONTS_KEY);
        if (saved) {
            setBookmarkedFonts(JSON.parse(saved));
        }
    }, []);

    // 북마크 토글
    const toggleBookmark = useCallback((fontValue: string) => {
        setBookmarkedFonts(prev => {
            const newBookmarks = prev.includes(fontValue)
                ? prev.filter(f => f !== fontValue)
                : [...prev, fontValue];
            localStorage.setItem(BOOKMARKED_FONTS_KEY, JSON.stringify(newBookmarks));
            return newBookmarks;
        });
    }, []);

    // 인트로 설정 업데이트
    const updateIntroSettings = useCallback((updates: Partial<IntroSettings>) => {
        setLocalIntroSettings(prev => {
            const newSettings = { ...prev, ...updates };
            // setState 호출 완료 후 다음 틱에서 부모에게 알림 (React 오류 방지)
            requestAnimationFrame(() => {
                onIntroSettingsChange?.(newSettings);
            });
            return newSettings;
        });
    }, [onIntroSettingsChange]);

    // 필터된 폰트 목록
    const filteredFonts = FONT_OPTIONS.filter(font => {
        if (fontCategory === 'all') return true;
        if (fontCategory === 'bookmarked') return bookmarkedFonts.includes(font.value);
        return font.category === fontCategory;
    });

    // 텍스트가 변경되면 박스 업데이트 (initialLayout이 있으면 props 텍스트 무시)
    useEffect(() => {
        // initialLayout이 있으면 저장된 텍스트를 유지
        if (initialLayout?.textBoxes) return;

        setTextBoxes(prev => prev.map(box => {
            switch (box.id) {
                case 'main': return { ...box, text: mainTitle };
                case 'sub': return { ...box, text: subTitle };
                case 'date': return { ...box, text: dateText };
                case 'verse': return { ...box, text: bibleVerse };
                default: return box;
            }
        }));
    }, [mainTitle, subTitle, dateText, bibleVerse, initialLayout]);

    // 드래그 시작
    const handleMouseDown = useCallback((e: React.MouseEvent, boxId: string) => {
        e.preventDefault();
        setSelectedBox(boxId);
        setIsDragging(true);

        const box = textBoxes.find(b => b.id === boxId);
        if (!box || !canvasRef.current) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const boxX = (box.x / 100) * rect.width;
        const boxY = (box.y / 100) * rect.height;

        setDragOffset({
            x: e.clientX - rect.left - boxX,
            y: e.clientY - rect.top - boxY,
        });
    }, [textBoxes]);

    // 드래그 중
    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (!isDragging || !selectedBox || !canvasRef.current) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const newX = ((e.clientX - rect.left - dragOffset.x) / rect.width) * 100;
        const newY = ((e.clientY - rect.top - dragOffset.y) / rect.height) * 100;

        // 범위 제한 (0-100)
        const clampedX = Math.max(0, Math.min(100, newX));
        const clampedY = Math.max(0, Math.min(100, newY));

        setTextBoxes(prev => prev.map(box =>
            box.id === selectedBox ? { ...box, x: clampedX, y: clampedY } : box
        ));
    }, [isDragging, selectedBox, dragOffset]);

    // 드래그 종료
    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    // 텍스트 박스 속성 업데이트
    const updateTextBox = useCallback((boxId: string, updates: Partial<TextBox>) => {
        setTextBoxes(prev => prev.map(box =>
            box.id === boxId ? { ...box, ...updates } : box
        ));
    }, []);

    // 레이아웃 초기화
    const resetLayout = useCallback(() => {
        setTextBoxes(createDefaultTextBoxes(mainTitle, subTitle, dateText, bibleVerse));
        setSelectedBox(null);
    }, [mainTitle, subTitle, dateText, bibleVerse]);

    // 레이아웃 저장
    const handleSave = useCallback(() => {
        const layout: ThumbnailLayout = {
            textBoxes,
            backgroundImageUrl,
            introSettings: localIntroSettings,
        };
        onSave?.(layout);
    }, [textBoxes, backgroundImageUrl, localIntroSettings, onSave]);

    // 기본 템플릿으로 저장 (localStorage)
    const handleSaveAsDefault = useCallback(() => {
        const layout: ThumbnailLayout = {
            textBoxes,
            backgroundImageUrl,
            introSettings: localIntroSettings,
        };
        localStorage.setItem('qt_default_thumbnail_layout', JSON.stringify(layout));
        alert('기본 템플릿으로 저장되었습니다!\n새 영상에서 자동으로 이 레이아웃이 적용됩니다.');
    }, [textBoxes, backgroundImageUrl, localIntroSettings]);

    // 기본 템플릿 불러오기
    const handleLoadDefault = useCallback(() => {
        const saved = localStorage.getItem('qt_default_thumbnail_layout');
        if (saved) {
            try {
                const layout = JSON.parse(saved) as ThumbnailLayout;
                if (layout.textBoxes) {
                    setTextBoxes(layout.textBoxes);
                }
                if (layout.introSettings) {
                    setLocalIntroSettings(layout.introSettings);
                    onIntroSettingsChange?.(layout.introSettings);
                }
                alert('기본 템플릿을 불러왔습니다!');
            } catch (e) {
                console.error('Failed to load default layout:', e);
                alert('기본 템플릿 불러오기에 실패했습니다.');
            }
        } else {
            alert('저장된 기본 템플릿이 없습니다.');
        }
    }, [onIntroSettingsChange]);

    // 썸네일 생성
    const handleGenerate = useCallback(async () => {
        setGenerating(true);
        try {
            const layout: ThumbnailLayout = {
                textBoxes,
                backgroundImageUrl,
                introSettings: localIntroSettings,
            };
            await onGenerate?.(layout);
        } finally {
            setGenerating(false);
        }
    }, [textBoxes, backgroundImageUrl, localIntroSettings, onGenerate]);

    const selectedBoxData = textBoxes.find(b => b.id === selectedBox);

    return (
        <div className="flex gap-6 items-start">
            {/* 왼쪽: 캔버스 + 액션 버튼 - 960x540px 고정 크기 */}
            <div className="flex flex-col space-y-4">
                {/* 캔버스 영역 - 960x540px 고정 (1920x1080의 50%) */}
                <div
                    ref={canvasRef}
                    className="relative bg-black rounded-xl overflow-hidden cursor-crosshair select-none"
                    style={{ width: '960px', height: '540px' }}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                >
                    {/* 배경 이미지 */}
                    <img
                        src={backgroundImageUrl}
                        alt="Background"
                        className="absolute inset-0 w-full h-full object-contain pointer-events-none bg-black"
                        draggable={false}
                    />

                    {/* 어두운 오버레이 */}
                    <div className="absolute inset-0 bg-black/30 pointer-events-none" />

                    {/* 텍스트 박스들 */}
                    {textBoxes.filter(box => box.visible && box.text).map((box) => (
                        <div
                            key={box.id}
                            className={`absolute cursor-move transition-shadow ${selectedBox === box.id
                                    ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-transparent'
                                    : 'hover:ring-2 hover:ring-white/50'
                                }`}
                            style={{
                                left: `${box.x}%`,
                                top: `${box.y}%`,
                                transform: 'translate(-50%, -50%)',
                                fontSize: `${box.fontSize * 0.5}px`,  // 미리보기 스케일
                                fontFamily: box.fontFamily,
                                color: box.color,
                                textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                                whiteSpace: 'nowrap',
                                padding: selectedBox === box.id ? '4px 8px' : '0',
                                borderRadius: selectedBox === box.id ? '4px' : '0',
                                backgroundColor: selectedBox === box.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                            }}
                            onMouseDown={(e) => handleMouseDown(e, box.id)}
                        >
                            {box.text}
                        </div>
                    ))}

                    {/* 드래그 힌트 */}
                    {!selectedBox && (
                        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 bg-black/60 rounded-full text-white text-xs">
                            <Move className="w-3 h-3" />
                            텍스트를 드래그하여 위치 조정
                        </div>
                    )}
                </div>

                {/* 액션 버튼 */}
                <div className="flex flex-col gap-2">
                    <div className="flex gap-2">
                        <button
                            onClick={resetLayout}
                            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg hover:bg-accent transition-colors text-sm"
                        >
                            <RotateCcw className="w-4 h-4" />
                            초기화
                        </button>
                        <button
                            onClick={handleSave}
                            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg hover:bg-accent transition-colors text-sm"
                        >
                            <Save className="w-4 h-4" />
                            레이아웃 저장
                        </button>
                        <button
                            onClick={handleGenerate}
                            disabled={generating}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                        >
                            {generating ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    생성 중...
                                </>
                            ) : (
                                <>
                                    <Download className="w-4 h-4" />
                                    썸네일 생성
                                </>
                            )}
                        </button>
                    </div>
                    {/* 기본 템플릿 버튼 */}
                    <div className="flex gap-2">
                        <button
                            onClick={handleLoadDefault}
                            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-amber-300 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors text-sm"
                        >
                            <Bookmark className="w-4 h-4" />
                            기본 템플릿 불러오기
                        </button>
                        <button
                            onClick={handleSaveAsDefault}
                            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-green-300 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-colors text-sm"
                        >
                            <BookmarkCheck className="w-4 h-4" />
                            기본 템플릿으로 저장
                        </button>
                    </div>
                    {/* 다른 배경 선택 버튼 */}
                    {onChangeBackground && (
                        <button
                            onClick={onChangeBackground}
                            className="w-full py-2 text-sm text-muted-foreground hover:text-foreground border border-dashed border-border rounded-lg hover:border-primary transition-colors"
                        >
                            다른 배경 이미지 선택
                        </button>
                    )}
                </div>

                {/* 영상 인트로/아웃트로 설정 (가로 배치) */}
                <div className="mt-4 grid grid-cols-2 gap-4">
                    {/* 영상 인트로 설정 */}
                    <div className="p-4 bg-card border border-border rounded-xl space-y-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                            <PlayCircle className="w-4 h-4 text-primary" />
                            영상 시작 인트로 설정
                        </div>

                        {/* 썸네일을 인트로로 사용 */}
                        <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:border-primary/50 cursor-pointer transition-colors">
                            <input
                                type="checkbox"
                                checked={localIntroSettings.useAsIntro}
                                onChange={(e) => updateIntroSettings({
                                    useAsIntro: e.target.checked,
                                    separateIntro: e.target.checked ? false : localIntroSettings.separateIntro
                                })}
                                className="w-4 h-4 mt-0.5 rounded accent-primary"
                            />
                            <div className="flex-1">
                                <span className="text-sm font-medium text-foreground">
                                    썸네일을 영상 시작 인트로로 사용
                                </span>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    위에서 편집한 썸네일 이미지가 영상 시작 시 보여집니다
                                </p>
                            </div>
                        </label>

                        {/* 인트로 길이 선택 (썸네일을 인트로로 사용할 때만) */}
                        {localIntroSettings.useAsIntro && (
                            <div className="ml-7 flex items-center gap-3">
                                <Clock className="w-4 h-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">인트로 길이:</span>
                                <select
                                    value={localIntroSettings.introDuration}
                                    onChange={(e) => updateIntroSettings({ introDuration: parseInt(e.target.value) })}
                                    className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background"
                                >
                                    {INTRO_DURATION_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* 구분선 */}
                        <div className="relative py-2">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-border"></div>
                            </div>
                            <div className="relative flex justify-center text-xs">
                                <span className="px-2 bg-card text-muted-foreground">또는</span>
                            </div>
                        </div>

                        {/* 별도 인트로 이미지 사용 */}
                        <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:border-primary/50 cursor-pointer transition-colors">
                            <input
                                type="checkbox"
                                checked={localIntroSettings.separateIntro}
                                onChange={(e) => updateIntroSettings({
                                    separateIntro: e.target.checked,
                                    useAsIntro: e.target.checked ? false : localIntroSettings.useAsIntro
                                })}
                                className="w-4 h-4 mt-0.5 rounded accent-primary"
                            />
                            <div className="flex-1">
                                <span className="text-sm font-medium text-foreground">
                                    별도 인트로 이미지 사용
                                </span>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    썸네일과 다른 이미지를 영상 시작에 사용합니다 (추후 지원 예정)
                                </p>
                            </div>
                        </label>

                        {/* 별도 인트로 설정 영역 (추후 구현) */}
                        {localIntroSettings.separateIntro && (
                            <div className="ml-7 p-3 bg-muted/30 rounded-lg">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <ImageIcon className="w-4 h-4" />
                                    별도 인트로 편집 기능은 추후 업데이트 예정입니다
                                </div>
                                <div className="mt-2 flex items-center gap-3">
                                    <Clock className="w-4 h-4 text-muted-foreground" />
                                    <span className="text-sm text-muted-foreground">인트로 길이:</span>
                                    <select
                                        value={localIntroSettings.introDuration}
                                        onChange={(e) => updateIntroSettings({ introDuration: parseInt(e.target.value) })}
                                        className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background"
                                    >
                                        {INTRO_DURATION_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        )}

                        {/* 인트로 미사용 안내 */}
                        {!localIntroSettings.useAsIntro && !localIntroSettings.separateIntro && (
                            <p className="text-xs text-muted-foreground text-center py-2">
                                인트로 없이 바로 영상이 시작됩니다
                            </p>
                        )}
                    </div>

                    {/* 영상 아웃트로 설정 */}
                    <div className="p-4 bg-card border border-border rounded-xl space-y-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                            <StopCircle className="w-4 h-4 text-primary" />
                            영상 종료 아웃트로 설정
                        </div>

                        {/* 배경 이미지를 아웃트로로 사용 */}
                        <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:border-primary/50 cursor-pointer transition-colors">
                            <input
                                type="checkbox"
                                checked={localIntroSettings.useAsOutro ?? true}
                                onChange={(e) => updateIntroSettings({ useAsOutro: e.target.checked })}
                                className="w-4 h-4 mt-0.5 rounded accent-primary"
                            />
                            <div className="flex-1">
                                <span className="text-sm font-medium text-foreground">
                                    배경 이미지를 영상 종료 아웃트로로 사용
                                </span>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    썸네일 배경 이미지가 영상 끝에 페이드되며 보여집니다 (텍스트 없이 배경만)
                                </p>
                            </div>
                        </label>

                        {/* 아웃트로 길이 선택 */}
                        {(localIntroSettings.useAsOutro ?? true) && (
                            <div className="ml-7 flex items-center gap-3">
                                <Clock className="w-4 h-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">아웃트로 길이:</span>
                                <select
                                    value={localIntroSettings.outroDuration ?? 3}
                                    onChange={(e) => updateIntroSettings({ outroDuration: parseInt(e.target.value) })}
                                    className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background"
                                >
                                    {OUTRO_DURATION_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* 아웃트로 미사용 안내 */}
                        {!(localIntroSettings.useAsOutro ?? true) && (
                            <p className="text-xs text-muted-foreground text-center py-2">
                                아웃트로 없이 영상이 종료됩니다
                            </p>
                        )}
                    </div>
                </div>

            </div>

            {/* 오른쪽: 편집 컨트롤 */}
            <div className="flex-1 bg-card border border-border rounded-xl p-4 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto">
                {/* 텍스트 박스 선택 탭 */}
                <div>
                    <label className="block text-sm font-medium text-foreground mb-2">텍스트 선택</label>
                    <div className="flex flex-wrap gap-2">
                        {textBoxes.map((box) => (
                            <button
                                key={box.id}
                                onClick={() => setSelectedBox(selectedBox === box.id ? null : box.id)}
                                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${selectedBox === box.id
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-accent text-foreground hover:bg-accent/80'
                                    }`}
                            >
                                {box.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* 선택된 박스 설정 */}
                {selectedBoxData ? (
                    <div className="space-y-4 pt-4 border-t border-border">
                        {/* 텍스트 입력 */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1.5">
                                <Type className="inline w-4 h-4 mr-1" />
                                텍스트
                            </label>
                            <input
                                type="text"
                                value={selectedBoxData.text}
                                onChange={(e) => updateTextBox(selectedBoxData.id, { text: e.target.value })}
                                className="w-full px-3 py-2 border border-border rounded-lg bg-background"
                            />
                        </div>

                        {/* 폰트 선택 - 미리보기 그리드 */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1.5">
                                폰트
                            </label>

                            {/* 카테고리 탭 */}
                            <div className="flex flex-wrap gap-1 mb-2">
                                {FONT_CATEGORIES.map(cat => (
                                    <button
                                        key={cat.id}
                                        type="button"
                                        onClick={() => setFontCategory(cat.id)}
                                        className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${fontCategory === cat.id
                                            ? 'bg-primary text-primary-foreground'
                                            : 'bg-accent text-foreground hover:bg-accent/80'
                                            }`}
                                    >
                                        {cat.id === 'bookmarked' && <Star className="w-3 h-3" />}
                                        {cat.label}
                                    </button>
                                ))}
                            </div>

                            {/* 폰트 그리드 */}
                            <div className="max-h-56 overflow-y-auto border border-border rounded-lg p-2 space-y-1">
                                {filteredFonts.length === 0 ? (
                                    <p className="text-sm text-muted-foreground text-center py-4">
                                        {fontCategory === 'bookmarked' ? '즐겨찾기한 폰트가 없습니다' : '폰트가 없습니다'}
                                    </p>
                                ) : (
                                    filteredFonts.map(font => (
                                        <div
                                            key={font.value}
                                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${selectedBoxData.fontFamily === font.value
                                                ? 'bg-primary/20 border border-primary'
                                                : 'hover:bg-accent border border-transparent'
                                                }`}
                                            onClick={() => updateTextBox(selectedBoxData.id, { fontFamily: font.value })}
                                        >
                                            {/* 북마크 버튼 */}
                                            <button
                                                type="button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleBookmark(font.value);
                                                }}
                                                className="p-1 hover:bg-accent rounded"
                                            >
                                                {bookmarkedFonts.includes(font.value) ? (
                                                    <BookmarkCheck className="w-4 h-4 text-primary" />
                                                ) : (
                                                    <Bookmark className="w-4 h-4 text-muted-foreground" />
                                                )}
                                            </button>

                                            {/* 폰트 정보 */}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-muted-foreground">{font.label}</p>
                                                <p
                                                    className="text-lg truncate"
                                                    style={{ fontFamily: font.value }}
                                                >
                                                    {selectedBoxData.text || font.preview}
                                                </p>
                                            </div>

                                            {/* 선택 표시 */}
                                            {selectedBoxData.fontFamily === font.value && (
                                                <div className="w-2 h-2 rounded-full bg-primary" />
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* 폰트 크기 */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1.5">
                                크기: {selectedBoxData.fontSize}px
                            </label>
                            <input
                                type="range"
                                min="12"
                                max="150"
                                value={selectedBoxData.fontSize}
                                onChange={(e) => updateTextBox(selectedBoxData.id, { fontSize: parseInt(e.target.value) })}
                                className="w-full"
                            />
                        </div>

                        {/* 색상 */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1.5">
                                <Palette className="inline w-4 h-4 mr-1" />
                                색상
                            </label>
                            {/* 프리셋 색상 */}
                            <div className="flex flex-wrap gap-1.5 mb-2">
                                {['#FFFFFF', '#000000', '#FF0000', '#FF6B00', '#FFD700', '#00FF00', '#00BFFF', '#0066FF', '#8B00FF', '#FF1493'].map((color) => (
                                    <button
                                        key={color}
                                        type="button"
                                        onClick={() => updateTextBox(selectedBoxData.id, { color })}
                                        className={`w-7 h-7 rounded-md border-2 transition-all ${selectedBoxData.color.toUpperCase() === color ? 'border-primary scale-110 ring-2 ring-primary/50' : 'border-border hover:scale-105'}`}
                                        style={{ backgroundColor: color }}
                                        title={color}
                                    />
                                ))}
                            </div>
                            {/* 커스텀 색상 */}
                            <div className="flex gap-2">
                                <input
                                    type="color"
                                    value={selectedBoxData.color}
                                    onChange={(e) => updateTextBox(selectedBoxData.id, { color: e.target.value })}
                                    className="w-16 h-10 rounded cursor-pointer border border-border"
                                />
                                <input
                                    type="text"
                                    value={selectedBoxData.color}
                                    onChange={(e) => updateTextBox(selectedBoxData.id, { color: e.target.value })}
                                    placeholder="#FFFFFF"
                                    className="w-24 px-3 py-2 border border-border rounded-lg bg-background text-sm"
                                />
                            </div>
                        </div>

                        {/* 표시 여부 */}
                        <div className="flex items-center pt-2">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={selectedBoxData.visible}
                                    onChange={(e) => updateTextBox(selectedBoxData.id, { visible: e.target.checked })}
                                    className="w-4 h-4 rounded"
                                />
                                <span className="text-sm text-foreground">텍스트 표시</span>
                            </label>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center py-12 text-muted-foreground">
                        위에서 텍스트를 선택하세요
                    </div>
                )}
            </div>
        </div>
    );
}
