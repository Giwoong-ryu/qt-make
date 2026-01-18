'use client';

import { useState, useRef, useCallback, useEffect, forwardRef, useImperativeHandle } from 'react';
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
    X,
    Check,
    Eye,
} from 'lucide-react';

// 텍스트 박스 타입
interface TextBox {
    id: string;
    label: string;
    text: string;
    x: number;  // 0-100 (퍼센트)
    y: number;  // 0-100 (퍼센트)
    fontSize: number;  // px (1920x1080 기준)
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
    canvasImageData?: string;  // Canvas에서 직접 export한 이미지 데이터 (base64)
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
    // Canvas 이미지 변경 콜백 (영상 재생성 시 사용)
    onCanvasImageChange?: (imageData: string | null) => void;
}

// 외부에서 호출할 수 있는 메서드 타입
export interface ThumbnailEditorRef {
    exportCanvasImage: () => string | null;
}

// 폰트 옵션 - Canvas와 FFmpeg 모두 지원하는 폰트만
const FONT_OPTIONS = [
    // 고딕 계열
    { value: 'Nanum Gothic', label: '나눔고딕', category: 'gothic', preview: '가나다ABC' },
    { value: 'Noto Sans KR', label: 'Noto Sans', category: 'gothic', preview: '가나다ABC' },
    { value: 'Gothic A1', label: 'Gothic A1', category: 'gothic', preview: '가나다ABC' },
    { value: 'Do Hyeon', label: '도현', category: 'gothic', preview: '가나다ABC' },
    { value: 'Jua', label: '주아', category: 'gothic', preview: '가나다ABC' },
    // 명조/세리프 계열
    { value: 'Nanum Myeongjo', label: '나눔명조', category: 'serif', preview: '가나다ABC' },
    { value: 'Noto Serif KR', label: 'Noto Serif', category: 'serif', preview: '가나다ABC' },
    { value: 'Gowun Batang', label: '고운바탕', category: 'serif', preview: '가나다ABC' },
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

// Canvas 크기 (실제 출력 해상도)
const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;
// 미리보기 크기 (화면 표시용) - UI에 맞게 조정
const PREVIEW_WIDTH = 640;
const PREVIEW_HEIGHT = 360;
const SCALE = PREVIEW_WIDTH / CANVAS_WIDTH;  // 0.333

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
            fontSize: 96,  // 1920x1080 기준
            fontFamily: 'Noto Sans KR',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'sub',
            label: '서브 제목',
            text: subTitle,
            x: 50,
            y: 30,
            fontSize: 64,
            fontFamily: 'Noto Sans KR',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'date',
            label: '날짜',
            text: dateText,
            x: 50,
            y: 42,
            fontSize: 48,
            fontFamily: 'Noto Sans KR',
            color: '#FFFFFF',
            visible: true,
        },
        {
            id: 'verse',
            label: '성경 구절',
            text: bibleVerse,
            x: 85,
            y: 88,
            fontSize: 56,
            fontFamily: 'Noto Sans KR',
            color: '#FFFFFF',
            visible: true,
        },
    ];

const ThumbnailEditor = forwardRef<ThumbnailEditorRef, ThumbnailEditorProps>(function ThumbnailEditor({
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
    onCanvasImageChange,
}, ref) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [textBoxes, setTextBoxes] = useState<TextBox[]>(
        initialLayout?.textBoxes || createDefaultTextBoxes(mainTitle, subTitle, dateText, bibleVerse)
    );
    const [selectedBox, setSelectedBox] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [generating, setGenerating] = useState(false);
    const [bgImage, setBgImage] = useState<HTMLImageElement | null>(null);

    // 미리보기 모달 상태
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [showPreview, setShowPreview] = useState(false);

    // 폰트 선택 UI 상태
    const [fontCategory, setFontCategory] = useState<string>('all');
    const [bookmarkedFonts, setBookmarkedFonts] = useState<string[]>([]);

    // 인트로 설정 상태 (외부에서 전달받거나 기본값 사용)
    const [localIntroSettings, setLocalIntroSettings] = useState<IntroSettings>(
        externalIntroSettings || initialLayout?.introSettings || DEFAULT_INTRO_SETTINGS
    );

    // 배경 이미지 로드 (R2 URL은 프록시 사용)
    useEffect(() => {
        if (!backgroundImageUrl) {
            console.warn('ThumbnailEditor: backgroundImageUrl is empty');
            return;
        }

        // R2 URL인 경우 백엔드 프록시 사용 (CORS 우회)
        let imageUrl = backgroundImageUrl;
        if (backgroundImageUrl.includes('r2.dev') || backgroundImageUrl.includes('pub-')) {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            imageUrl = `${apiBase}/api/proxy/image?url=${encodeURIComponent(backgroundImageUrl)}`;
            console.log('ThumbnailEditor: Using proxy URL', imageUrl);
        }

        console.log('ThumbnailEditor: Loading image from', imageUrl);
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            console.log('ThumbnailEditor: Image loaded successfully', img.width, 'x', img.height);
            setBgImage(img);
        };
        img.onerror = (e) => {
            console.error('ThumbnailEditor: Failed to load image', imageUrl, e);
        };
        img.src = imageUrl;
    }, [backgroundImageUrl]);

    // Canvas 렌더링
    useEffect(() => {
        console.log('[ThumbnailEditor] Canvas 렌더링 useEffect 실행:', {
            canvasRef: canvasRef.current ? '있음' : '없음',
            bgImage: bgImage ? `${bgImage.width}x${bgImage.height}` : '없음',
            textBoxes: textBoxes.length,
            selectedBox
        });

        const canvas = canvasRef.current;
        if (!canvas || !bgImage) {
            console.log('[ThumbnailEditor] Canvas 렌더링 스킵 - canvas 또는 bgImage 없음');
            return;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // 배경 그리기 (cover 방식 - FFmpeg와 동일)
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // 이미지 비율 계산 (cover - 캔버스를 완전히 채움)
        const imgRatio = bgImage.width / bgImage.height;
        const canvasRatio = CANVAS_WIDTH / CANVAS_HEIGHT;
        let drawWidth, drawHeight, drawX, drawY;

        if (imgRatio > canvasRatio) {
            // 이미지가 더 넓음 → 높이 맞추고 좌우 잘림
            drawHeight = CANVAS_HEIGHT;
            drawWidth = CANVAS_HEIGHT * imgRatio;
            drawX = (CANVAS_WIDTH - drawWidth) / 2;
            drawY = 0;
        } else {
            // 이미지가 더 높음 → 너비 맞추고 상하 잘림
            drawWidth = CANVAS_WIDTH;
            drawHeight = CANVAS_WIDTH / imgRatio;
            drawX = 0;
            drawY = (CANVAS_HEIGHT - drawHeight) / 2;
        }

        ctx.drawImage(bgImage, drawX, drawY, drawWidth, drawHeight);

        // 어두운 오버레이
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // 텍스트 렌더링
        textBoxes.filter(box => box.visible && box.text).forEach(box => {
            const x = (box.x / 100) * CANVAS_WIDTH;
            const y = (box.y / 100) * CANVAS_HEIGHT;

            ctx.font = `bold ${box.fontSize}px "${box.fontFamily}", "Noto Sans KR", sans-serif`;
            ctx.fillStyle = box.color;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            // 텍스트 그림자
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
            ctx.shadowBlur = 8;
            ctx.shadowOffsetX = 4;
            ctx.shadowOffsetY = 4;

            ctx.fillText(box.text, x, y);

            // 그림자 리셋
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;

            // 선택된 박스 하이라이트
            if (selectedBox === box.id) {
                const metrics = ctx.measureText(box.text);
                const textWidth = metrics.width;
                const textHeight = box.fontSize;

                ctx.strokeStyle = '#3b82f6';
                ctx.lineWidth = 4;
                ctx.setLineDash([10, 5]);
                ctx.strokeRect(
                    x - textWidth / 2 - 20,
                    y - textHeight / 2 - 10,
                    textWidth + 40,
                    textHeight + 20
                );
                ctx.setLineDash([]);
            }
        });

        // Canvas 렌더링 완료 후 자동으로 이미지를 부모에게 전달
        // (선택 박스 하이라이트 없는 클린 버전)
        const exportCleanCanvas = () => {
            const exportCanvas = document.createElement('canvas');
            exportCanvas.width = CANVAS_WIDTH;
            exportCanvas.height = CANVAS_HEIGHT;
            const exportCtx = exportCanvas.getContext('2d');
            if (!exportCtx) return null;

            // 배경 그리기
            exportCtx.fillStyle = '#000000';
            exportCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

            const imgRatio = bgImage.width / bgImage.height;
            const canvasRatio = CANVAS_WIDTH / CANVAS_HEIGHT;
            let dw, dh, dx, dy;
            if (imgRatio > canvasRatio) {
                dh = CANVAS_HEIGHT;
                dw = CANVAS_HEIGHT * imgRatio;
                dx = (CANVAS_WIDTH - dw) / 2;
                dy = 0;
            } else {
                dw = CANVAS_WIDTH;
                dh = CANVAS_WIDTH / imgRatio;
                dx = 0;
                dy = (CANVAS_HEIGHT - dh) / 2;
            }
            exportCtx.drawImage(bgImage, dx, dy, dw, dh);

            // 어두운 오버레이
            exportCtx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            exportCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

            // 텍스트 렌더링 (하이라이트 없이)
            textBoxes.filter(b => b.visible && b.text).forEach(b => {
                const bx = (b.x / 100) * CANVAS_WIDTH;
                const by = (b.y / 100) * CANVAS_HEIGHT;
                exportCtx.font = `bold ${b.fontSize}px "${b.fontFamily}", "Noto Sans KR", sans-serif`;
                exportCtx.fillStyle = b.color;
                exportCtx.textAlign = 'center';
                exportCtx.textBaseline = 'middle';
                exportCtx.shadowColor = 'rgba(0, 0, 0, 0.8)';
                exportCtx.shadowBlur = 8;
                exportCtx.shadowOffsetX = 4;
                exportCtx.shadowOffsetY = 4;
                exportCtx.fillText(b.text, bx, by);
                exportCtx.shadowColor = 'transparent';
                exportCtx.shadowBlur = 0;
                exportCtx.shadowOffsetX = 0;
                exportCtx.shadowOffsetY = 0;
            });

            return exportCanvas.toDataURL('image/jpeg', 0.95);
        };

        // 렌더링 완료 후 부모에게 자동 전달 (debounce 효과)
        const timeoutId = setTimeout(() => {
            const imageData = exportCleanCanvas();
            if (imageData) {
                console.log('[ThumbnailEditor] Canvas 이미지 자동 업데이트:', imageData.length, 'bytes');
                onCanvasImageChange?.(imageData);
            }
        }, 100);

        return () => clearTimeout(timeoutId);
    }, [bgImage, textBoxes, selectedBox, onCanvasImageChange]);

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

    // 텍스트가 변경되면 박스 업데이트
    useEffect(() => {
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

    // 클릭으로 텍스트 박스 선택
    const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        if (isDragging) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = CANVAS_WIDTH / rect.width;
        const scaleY = CANVAS_HEIGHT / rect.height;
        const clickX = (e.clientX - rect.left) * scaleX;
        const clickY = (e.clientY - rect.top) * scaleY;

        // 클릭 위치와 가장 가까운 텍스트 박스 찾기
        let closestBox: string | null = null;
        let closestDist = Infinity;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        textBoxes.filter(box => box.visible && box.text).forEach(box => {
            const boxX = (box.x / 100) * CANVAS_WIDTH;
            const boxY = (box.y / 100) * CANVAS_HEIGHT;

            ctx.font = `bold ${box.fontSize}px "${box.fontFamily}", "Noto Sans KR", sans-serif`;
            const metrics = ctx.measureText(box.text);
            const textWidth = metrics.width;
            const textHeight = box.fontSize;

            // 텍스트 영역 내에 클릭했는지 확인
            if (
                clickX >= boxX - textWidth / 2 - 20 &&
                clickX <= boxX + textWidth / 2 + 20 &&
                clickY >= boxY - textHeight / 2 - 10 &&
                clickY <= boxY + textHeight / 2 + 10
            ) {
                const dist = Math.hypot(clickX - boxX, clickY - boxY);
                if (dist < closestDist) {
                    closestDist = dist;
                    closestBox = box.id;
                }
            }
        });

        setSelectedBox(closestBox);
    }, [textBoxes, isDragging]);

    // 드래그 시작
    const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = CANVAS_WIDTH / rect.width;
        const scaleY = CANVAS_HEIGHT / rect.height;
        const clickX = (e.clientX - rect.left) * scaleX;
        const clickY = (e.clientY - rect.top) * scaleY;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // 클릭한 텍스트 박스 찾기
        const visibleBoxes = textBoxes.filter(box => box.visible && box.text);
        let clickedBox: typeof visibleBoxes[number] | null = null;

        for (const box of visibleBoxes) {
            const boxX = (box.x / 100) * CANVAS_WIDTH;
            const boxY = (box.y / 100) * CANVAS_HEIGHT;

            ctx.font = `bold ${box.fontSize}px "${box.fontFamily}", "Noto Sans KR", sans-serif`;
            const metrics = ctx.measureText(box.text);
            const textWidth = metrics.width;
            const textHeight = box.fontSize;

            if (
                clickX >= boxX - textWidth / 2 - 20 &&
                clickX <= boxX + textWidth / 2 + 20 &&
                clickY >= boxY - textHeight / 2 - 10 &&
                clickY <= boxY + textHeight / 2 + 10
            ) {
                clickedBox = box;
                break;
            }
        }

        if (clickedBox) {
            setSelectedBox(clickedBox.id);
            setIsDragging(true);
            setDragOffset({
                x: clickX - (clickedBox.x / 100) * CANVAS_WIDTH,
                y: clickY - (clickedBox.y / 100) * CANVAS_HEIGHT,
            });
        }
    }, [textBoxes]);

    // 드래그 중
    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!isDragging || !selectedBox) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = CANVAS_WIDTH / rect.width;
        const scaleY = CANVAS_HEIGHT / rect.height;
        const mouseX = (e.clientX - rect.left) * scaleX;
        const mouseY = (e.clientY - rect.top) * scaleY;

        const newX = ((mouseX - dragOffset.x) / CANVAS_WIDTH) * 100;
        const newY = ((mouseY - dragOffset.y) / CANVAS_HEIGHT) * 100;

        const clampedX = Math.max(5, Math.min(95, newX));
        const clampedY = Math.max(5, Math.min(95, newY));

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

    // 기본 템플릿으로 저장
    const handleSaveAsDefault = useCallback(() => {
        const layout: ThumbnailLayout = {
            textBoxes,
            backgroundImageUrl,
            introSettings: localIntroSettings,
        };
        localStorage.setItem('qt_default_thumbnail_layout', JSON.stringify(layout));
        alert('기본 템플릿으로 저장되었습니다!');
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

    // Canvas에서 이미지를 export하는 함수 (선택 박스 표시 제거 버전)
    const exportCanvasImage = useCallback((): string | null => {
        const canvas = canvasRef.current;
        if (!canvas || !bgImage) return null;

        // 새로운 Canvas 생성 (선택 박스 없이 렌더링)
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = CANVAS_WIDTH;
        exportCanvas.height = CANVAS_HEIGHT;
        const ctx = exportCanvas.getContext('2d');
        if (!ctx) return null;

        // 배경 그리기 (cover 방식)
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        const imgRatio = bgImage.width / bgImage.height;
        const canvasRatio = CANVAS_WIDTH / CANVAS_HEIGHT;
        let drawWidth, drawHeight, drawX, drawY;

        if (imgRatio > canvasRatio) {
            drawHeight = CANVAS_HEIGHT;
            drawWidth = CANVAS_HEIGHT * imgRatio;
            drawX = (CANVAS_WIDTH - drawWidth) / 2;
            drawY = 0;
        } else {
            drawWidth = CANVAS_WIDTH;
            drawHeight = CANVAS_WIDTH / imgRatio;
            drawX = 0;
            drawY = (CANVAS_HEIGHT - drawHeight) / 2;
        }

        ctx.drawImage(bgImage, drawX, drawY, drawWidth, drawHeight);

        // 어두운 오버레이
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // 텍스트 렌더링 (선택 박스 하이라이트 없이)
        textBoxes.filter(box => box.visible && box.text).forEach(box => {
            const x = (box.x / 100) * CANVAS_WIDTH;
            const y = (box.y / 100) * CANVAS_HEIGHT;

            ctx.font = `bold ${box.fontSize}px "${box.fontFamily}", "Noto Sans KR", sans-serif`;
            ctx.fillStyle = box.color;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            // 텍스트 그림자
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
            ctx.shadowBlur = 8;
            ctx.shadowOffsetX = 4;
            ctx.shadowOffsetY = 4;

            ctx.fillText(box.text, x, y);

            // 그림자 리셋
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
        });

        // JPEG로 export (품질 95%)
        return exportCanvas.toDataURL('image/jpeg', 0.95);
    }, [bgImage, textBoxes]);

    // 외부에서 exportCanvasImage를 호출할 수 있도록 ref로 노출
    useImperativeHandle(ref, () => ({
        exportCanvasImage,
    }), [exportCanvasImage]);

    // 썸네일 미리보기 (Canvas에서 이미지 export 후 모달에 표시)
    const handleGenerate = useCallback(() => {
        // Canvas에서 직접 이미지 export
        const canvasImageData = exportCanvasImage();
        if (!canvasImageData) {
            alert('이미지를 생성할 수 없습니다. 배경 이미지가 로드되었는지 확인하세요.');
            return;
        }

        // 미리보기 모달 표시
        setPreviewImage(canvasImageData);
        setShowPreview(true);

        // 부모에게 Canvas 이미지 변경 알림 (영상 재생성 시 사용)
        onCanvasImageChange?.(canvasImageData);
    }, [exportCanvasImage, onCanvasImageChange]);

    // 미리보기에서 "적용" 버튼 클릭 시 실제 저장
    const handleConfirmGenerate = useCallback(async () => {
        if (!previewImage) return;

        setGenerating(true);
        try {
            const layout: ThumbnailLayout = {
                textBoxes,
                backgroundImageUrl,
                introSettings: localIntroSettings,
            };

            // onGenerate에 Canvas 이미지 데이터도 함께 전달
            await onGenerate?.({ ...layout, canvasImageData: previewImage });

            // 성공 시 모달 닫기
            setShowPreview(false);
            setPreviewImage(null);
        } finally {
            setGenerating(false);
        }
    }, [textBoxes, backgroundImageUrl, localIntroSettings, onGenerate, previewImage]);

    // 미리보기 취소
    const handleCancelPreview = useCallback(() => {
        setShowPreview(false);
        setPreviewImage(null);
    }, []);

    const selectedBoxData = textBoxes.find(b => b.id === selectedBox);

    return (
        <>
            {/* 미리보기 모달 */}
            {showPreview && previewImage && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
                    <div className="bg-card rounded-2xl shadow-2xl max-w-4xl w-full mx-4 overflow-hidden">
                        {/* 모달 헤더 */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <div className="flex items-center gap-2">
                                <Eye className="w-5 h-5 text-primary" />
                                <h3 className="text-lg font-semibold">썸네일 미리보기</h3>
                            </div>
                            <button
                                onClick={handleCancelPreview}
                                className="p-2 hover:bg-accent rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* 미리보기 이미지 */}
                        <div className="p-6 bg-muted/30">
                            <div className="relative mx-auto" style={{ maxWidth: '800px' }}>
                                <img
                                    src={previewImage}
                                    alt="썸네일 미리보기"
                                    className="w-full rounded-lg shadow-lg"
                                />
                                <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/60 rounded text-white text-xs">
                                    1920 x 1080
                                </div>
                            </div>
                        </div>

                        {/* 모달 푸터 */}
                        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-card">
                            <p className="text-sm text-muted-foreground">
                                이 썸네일을 영상에 적용하시겠습니까?
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={handleCancelPreview}
                                    className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-accent transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                    취소
                                </button>
                                <button
                                    onClick={handleConfirmGenerate}
                                    disabled={generating}
                                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                                >
                                    {generating ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            저장 중...
                                        </>
                                    ) : (
                                        <>
                                            <Check className="w-4 h-4" />
                                            적용하기
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex gap-6 items-start justify-center">
                {/* 왼쪽: 캔버스 + 액션 버튼 */}
            <div className="flex flex-col space-y-4">
                {/* Canvas 영역 */}
                <div
                    ref={containerRef}
                    className="relative bg-black rounded-xl overflow-hidden"
                    style={{ width: `${PREVIEW_WIDTH}px`, height: `${PREVIEW_HEIGHT}px` }}
                >
                    <canvas
                        ref={canvasRef}
                        width={CANVAS_WIDTH}
                        height={CANVAS_HEIGHT}
                        className="cursor-crosshair"
                        style={{
                            width: `${PREVIEW_WIDTH}px`,
                            height: `${PREVIEW_HEIGHT}px`,
                        }}
                        onClick={handleCanvasClick}
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                    />

                    {/* 드래그 힌트 */}
                    {!selectedBox && (
                        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 bg-black/60 rounded-full text-white text-xs pointer-events-none">
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

                {/* 영상 인트로/아웃트로 설정 */}
                <div className="mt-4 grid grid-cols-2 gap-4">
                    {/* 영상 인트로 설정 */}
                    <div className="p-4 bg-card border border-border rounded-xl space-y-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                            <PlayCircle className="w-4 h-4 text-primary" />
                            영상 시작 인트로 설정
                        </div>

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

                        <div className="relative py-2">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-border"></div>
                            </div>
                            <div className="relative flex justify-center text-xs">
                                <span className="px-2 bg-card text-muted-foreground">또는</span>
                            </div>
                        </div>

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

                        {!(localIntroSettings.useAsOutro ?? true) && (
                            <p className="text-xs text-muted-foreground text-center py-2">
                                아웃트로 없이 영상이 종료됩니다
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* 오른쪽: 편집 컨트롤 */}
            <div className="flex-1 min-w-[320px] bg-card border border-border rounded-xl p-4 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto">
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

                        {/* 폰트 선택 */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1.5">
                                폰트
                            </label>

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

                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-muted-foreground">{font.label}</p>
                                                <p
                                                    className="text-lg truncate"
                                                    style={{ fontFamily: font.value }}
                                                >
                                                    {selectedBoxData.text || font.preview}
                                                </p>
                                            </div>

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
                                min="24"
                                max="200"
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
        </>
    );
});

export default ThumbnailEditor;
