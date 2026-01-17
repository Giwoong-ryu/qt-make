'use client';

import { useState, useEffect } from 'react';
import { Calendar, Book, ChevronDown } from 'lucide-react';

// 성경 66권 목록
const BIBLE_BOOKS = [
    // 구약 39권
    '창세기', '출애굽기', '레위기', '민수기', '신명기',
    '여호수아', '사사기', '룻기', '사무엘상', '사무엘하',
    '열왕기상', '열왕기하', '역대상', '역대하', '에스라',
    '느헤미야', '에스더', '욥기', '시편', '잠언',
    '전도서', '아가', '이사야', '예레미야', '예레미야애가',
    '에스겔', '다니엘', '호세아', '요엘', '아모스',
    '오바댜', '요나', '미가', '나훔', '하박국',
    '스바냐', '학개', '스가랴', '말라기',
    // 신약 27권
    '마태복음', '마가복음', '누가복음', '요한복음', '사도행전',
    '로마서', '고린도전서', '고린도후서', '갈라디아서', '에베소서',
    '빌립보서', '골로새서', '데살로니가전서', '데살로니가후서', '디모데전서',
    '디모데후서', '디도서', '빌레몬서', '히브리서', '야고보서',
    '베드로전서', '베드로후서', '요한1서', '요한2서', '요한3서',
    '유다서', '요한계시록'
];

export interface ThumbnailSettings {
    mainTitle: string;
    subTitle: string;
    date: string;
    bibleBook: string;
    chapterStart: string;
    verseStart: string;
    verseEnd: string;
    templateId?: string;
    backgroundImageUrl?: string;
}

interface ThumbnailSettingsFormProps {
    value: ThumbnailSettings;
    onChange: (settings: ThumbnailSettings) => void;
    onSaveAsDefault?: () => void;
}

export function ThumbnailSettingsForm({
    value,
    onChange,
    onSaveAsDefault
}: ThumbnailSettingsFormProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    // 오늘 날짜 기본값
    useEffect(() => {
        if (!value.date) {
            const today = new Date();
            const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
            const dateStr = `${today.getMonth() + 1}월 ${today.getDate()}일(${dayNames[today.getDay()]})`;
            onChange({ ...value, date: dateStr });
        }
    }, []);

    const updateField = (field: keyof ThumbnailSettings, val: string) => {
        onChange({ ...value, [field]: val });
    };

    // 성경 구절 문자열 생성
    const getBibleVerseString = () => {
        if (!value.bibleBook) return '';
        let verse = `${value.bibleBook} ${value.chapterStart || '1'}장`;
        if (value.verseStart) {
            verse += ` ${value.verseStart}`;
            if (value.verseEnd && value.verseEnd !== value.verseStart) {
                verse += `~${value.verseEnd}`;
            }
            verse += '절';
        }
        return verse;
    };

    return (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
            <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Book className="w-5 h-5 text-primary" />
                    </div>
                    <div className="text-left">
                        <h3 className="font-medium text-foreground">썸네일 설정</h3>
                        <p className="text-sm text-muted-foreground">
                            {value.mainTitle || getBibleVerseString() || '성경 구절, 제목, 날짜 입력'}
                        </p>
                    </div>
                </div>
                <ChevronDown className={`w-5 h-5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
            </button>

            {isExpanded && (
                <div className="p-4 border-t border-border space-y-4">
                    {/* 메인 제목 */}
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">
                            메인 제목
                        </label>
                        <input
                            type="text"
                            value={value.mainTitle}
                            onChange={(e) => updateField('mainTitle', e.target.value)}
                            placeholder="예: 말씀 좋아"
                            className="w-full px-4 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                        />
                    </div>

                    {/* 서브 제목 */}
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">
                            서브 제목
                        </label>
                        <input
                            type="text"
                            value={value.subTitle}
                            onChange={(e) => updateField('subTitle', e.target.value)}
                            placeholder="예: 말씀으로, 좋은 아침"
                            className="w-full px-4 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                        />
                    </div>

                    {/* 날짜 */}
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">
                            날짜
                        </label>
                        <div className="relative">
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                            <input
                                type="text"
                                value={value.date}
                                onChange={(e) => updateField('date', e.target.value)}
                                placeholder="예: 1월 12일(월)"
                                className="w-full pl-10 pr-4 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            />
                        </div>
                    </div>

                    {/* 성경 구절 */}
                    <div className="space-y-3">
                        <label className="block text-sm font-medium text-foreground">
                            성경 구절
                        </label>

                        <div className="grid grid-cols-4 gap-2">
                            {/* 성경 책 */}
                            <select
                                value={value.bibleBook}
                                onChange={(e) => updateField('bibleBook', e.target.value)}
                                className="col-span-2 px-3 py-2.5 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            >
                                <option value="">성경 선택</option>
                                {BIBLE_BOOKS.map((book) => (
                                    <option key={book} value={book}>{book}</option>
                                ))}
                            </select>

                            {/* 장 */}
                            <input
                                type="number"
                                value={value.chapterStart}
                                onChange={(e) => updateField('chapterStart', e.target.value)}
                                placeholder="장"
                                min="1"
                                className="px-3 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            />

                            {/* 시작 절 */}
                            <input
                                type="number"
                                value={value.verseStart}
                                onChange={(e) => updateField('verseStart', e.target.value)}
                                placeholder="시작절"
                                min="1"
                                className="px-3 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            />
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">~</span>
                            <input
                                type="number"
                                value={value.verseEnd}
                                onChange={(e) => updateField('verseEnd', e.target.value)}
                                placeholder="끝절 (선택)"
                                min="1"
                                className="w-32 px-3 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                            />
                            <span className="text-sm text-muted-foreground">절</span>
                        </div>

                        {/* 미리보기 */}
                        {getBibleVerseString() && (
                            <div className="p-3 bg-accent/50 rounded-lg">
                                <p className="text-sm text-muted-foreground">미리보기:</p>
                                <p className="font-medium text-foreground">{getBibleVerseString()}</p>
                            </div>
                        )}
                    </div>

                    {/* 기본값으로 저장 버튼 */}
                    {onSaveAsDefault && (
                        <button
                            type="button"
                            onClick={onSaveAsDefault}
                            className="w-full py-2.5 border border-border text-foreground rounded-lg hover:bg-accent transition-colors text-sm"
                        >
                            이 설정을 기본값으로 저장
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

export default ThumbnailSettingsForm;
