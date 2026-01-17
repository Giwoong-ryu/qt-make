'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Mountain,
  BookOpen,
  Heart,
  Flower2,
  Sun,
  Leaf,
  Snowflake,
  Sunrise,
  Star,
  Wheat,
  Check,
  Loader2,
  ChevronDown,
  ChevronRight,
  Bookmark,
  BookmarkCheck,
} from 'lucide-react';
import type { ThumbnailCategory, ThumbnailTemplate } from '@/lib/api';
import {
  getThumbnailCategories,
  getThumbnailTemplates,
} from '@/lib/api';

interface ThumbnailConceptPickerProps {
  lastUsedTemplateId?: string; // 이전에 사용한 템플릿 ID
  onSelect?: (templateImageUrl: string) => void; // 배경 이미지 선택 시 콜백
}

// 아이콘 매핑
const iconMap: { [key: string]: React.ComponentType<{ className?: string }> } = {
  Mountain: Mountain,
  BookOpen: BookOpen,
  Heart: Heart,
  Flower2: Flower2,
  Sun: Sun,
  Leaf: Leaf,
  Snowflake: Snowflake,
  Sunrise: Sunrise,
  Star: Star,
  Wheat: Wheat,
};

// 로컬 스토리지 키
const BOOKMARKED_TEMPLATES_KEY = 'thumbnail-bookmarked-templates';

export default function ThumbnailConceptPicker({
  lastUsedTemplateId,
  onSelect,
}: ThumbnailConceptPickerProps) {
  const [categories, setCategories] = useState<ThumbnailCategory[]>([]);
  const [templatesByCategory, setTemplatesByCategory] = useState<Record<string, ThumbnailTemplate[]>>({});
  const [loadingCategories, setLoadingCategories] = useState<Record<string, boolean>>({});
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<ThumbnailTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [bookmarkedTemplates, setBookmarkedTemplates] = useState<string[]>([]);
  const [showBookmarked, setShowBookmarked] = useState(false);
  const [bookmarkedTemplateData, setBookmarkedTemplateData] = useState<ThumbnailTemplate[]>([]);
  const [loadingBookmarks, setLoadingBookmarks] = useState(false);

  // 북마크 로드
  useEffect(() => {
    const saved = localStorage.getItem(BOOKMARKED_TEMPLATES_KEY);
    if (saved) {
      setBookmarkedTemplates(JSON.parse(saved));
    }
  }, []);

  // 북마크 토글
  const toggleBookmark = useCallback((e: React.MouseEvent, templateId: string) => {
    e.stopPropagation();
    setBookmarkedTemplates(prev => {
      const newBookmarks = prev.includes(templateId)
        ? prev.filter(id => id !== templateId)
        : [...prev, templateId];
      localStorage.setItem(BOOKMARKED_TEMPLATES_KEY, JSON.stringify(newBookmarks));
      return newBookmarks;
    });
  }, []);

  // 즐겨찾기 탭 클릭 시 북마크된 템플릿 데이터 로드
  useEffect(() => {
    if (!showBookmarked || bookmarkedTemplates.length === 0) return;

    async function loadBookmarkedTemplates() {
      setLoadingBookmarks(true);
      try {
        // 전체 템플릿을 가져와서 북마크된 것만 필터링
        const allTemplates = await getThumbnailTemplates();
        const bookmarked = allTemplates.filter(t => bookmarkedTemplates.includes(t.id));
        setBookmarkedTemplateData(bookmarked);
      } catch (error) {
        console.error('Failed to load bookmarked templates:', error);
      } finally {
        setLoadingBookmarks(false);
      }
    }

    loadBookmarkedTemplates();
  }, [showBookmarked, bookmarkedTemplates]);

  // 카테고리 로드 (템플릿은 나중에)
  useEffect(() => {
    async function loadCategories() {
      try {
        const cats = await getThumbnailCategories();
        setCategories(cats);
      } catch (error) {
        console.error('Failed to load categories:', error);
      } finally {
        setLoading(false);
      }
    }
    loadCategories();
  }, []);

  // 이전에 사용한 템플릿 로드 (처음에 보여주기 위해)
  useEffect(() => {
    if (!lastUsedTemplateId) return;

    async function loadLastUsedTemplate() {
      try {
        // 모든 템플릿에서 마지막 사용 템플릿 찾기
        const allTemplates = await getThumbnailTemplates();
        const lastUsed = allTemplates.find(t => t.id === lastUsedTemplateId);
        if (lastUsed) {
          setSelectedTemplate(lastUsed);
        }
      } catch (error) {
        console.error('Failed to load last used template:', error);
      }
    }
    loadLastUsedTemplate();
  }, [lastUsedTemplateId]);

  // 카테고리 클릭 시 템플릿 로드 (lazy loading)
  const handleCategoryClick = useCallback(async (categoryId: string) => {
    // 이미 열려있으면 닫기
    if (expandedCategory === categoryId) {
      setExpandedCategory(null);
      return;
    }

    setExpandedCategory(categoryId);

    // 이미 로드된 경우 스킵
    if (templatesByCategory[categoryId]) {
      return;
    }

    // 로딩 시작
    setLoadingCategories(prev => ({ ...prev, [categoryId]: true }));

    try {
      const templates = await getThumbnailTemplates(categoryId);
      setTemplatesByCategory(prev => ({ ...prev, [categoryId]: templates }));
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoadingCategories(prev => ({ ...prev, [categoryId]: false }));
    }
  }, [expandedCategory, templatesByCategory]);

  // 템플릿 선택 시 바로 콜백 호출
  const handleTemplateSelect = useCallback((template: ThumbnailTemplate) => {
    setSelectedTemplate(template);
    setExpandedCategory(null);
    onSelect?.(template.image_url);
  }, [onSelect]);

  // 북마크된 템플릿 가져오기 (API에서 로드한 데이터 사용)
  const getBookmarkedTemplatesList = useCallback(() => {
    return bookmarkedTemplateData;
  }, [bookmarkedTemplateData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-foreground">
        배경 이미지 선택
      </p>

      {/* 즐겨찾기 탭 */}
      <div className="flex gap-2 mb-2">
        <button
          onClick={() => setShowBookmarked(false)}
          className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${!showBookmarked
            ? 'bg-primary text-primary-foreground'
            : 'bg-accent text-foreground hover:bg-accent/80'
            }`}
        >
          카테고리
        </button>
        <button
          onClick={() => setShowBookmarked(true)}
          className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${showBookmarked
            ? 'bg-primary text-primary-foreground'
            : 'bg-accent text-foreground hover:bg-accent/80'
            }`}
        >
          <Star className="w-3 h-3" />
          즐겨찾기 ({bookmarkedTemplates.length})
        </button>
      </div>

      {/* 즐겨찾기 모드 */}
      {showBookmarked ? (
        <div className="border border-border rounded-lg p-3 bg-card">
          {bookmarkedTemplates.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              즐겨찾기한 배경이 없습니다.<br />
              <span className="text-xs">이미지 우측 상단의 북마크 아이콘을 클릭하세요</span>
            </p>
          ) : loadingBookmarks ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-2">
              {getBookmarkedTemplatesList().map((temp) => (
                <div
                  key={temp.id}
                  onClick={() => handleTemplateSelect(temp)}
                  className={`relative aspect-video rounded-lg overflow-hidden border-2 transition-all group cursor-pointer ${selectedTemplate?.id === temp.id
                    ? 'border-primary ring-2 ring-primary/50'
                    : 'border-transparent hover:border-muted-foreground/30'
                    }`}
                >
                  <img
                    src={temp.image_url}
                    alt={temp.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  {/* 북마크 버튼 */}
                  <button
                    onClick={(e) => toggleBookmark(e, temp.id)}
                    className="absolute top-1 left-1 p-1 bg-black/50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <BookmarkCheck className="w-3 h-3 text-yellow-400" />
                  </button>
                  {selectedTemplate?.id === temp.id && (
                    <div className="absolute top-1 right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                      <Check className="w-2.5 h-2.5 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* 카테고리 목록 (아코디언) */
        <div className="space-y-2">

        {categories.map((cat) => {
          const IconComponent = iconMap[cat.icon] || Mountain;
          const isExpanded = expandedCategory === cat.id;
          const templates = templatesByCategory[cat.id] || [];
          const isLoading = loadingCategories[cat.id];

          return (
            <div key={cat.id} className="border border-border rounded-lg overflow-hidden">
              {/* 카테고리 헤더 */}
              <button
                onClick={() => handleCategoryClick(cat.id)}
                className={`w-full flex items-center justify-between p-3 transition-colors ${isExpanded ? 'bg-accent' : 'hover:bg-accent/50'
                  }`}
              >
                <div className="flex items-center gap-2">
                  <IconComponent className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">{cat.name}</span>
                  <span className="text-xs text-muted-foreground">{cat.description}</span>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </button>

              {/* 템플릿 그리드 (펼쳐진 경우만) */}
              {isExpanded && (
                <div className="p-3 border-t border-border bg-card">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="w-5 h-5 animate-spin text-primary" />
                    </div>
                  ) : templates.length > 0 ? (
                    <div className="grid grid-cols-4 gap-2">
                      {templates.map((temp) => (
                        <div
                          key={temp.id}
                          onClick={() => handleTemplateSelect(temp)}
                          className={`relative aspect-video rounded-lg overflow-hidden border-2 transition-all group cursor-pointer ${selectedTemplate?.id === temp.id
                              ? 'border-primary ring-2 ring-primary/50'
                              : 'border-transparent hover:border-muted-foreground/30'
                            }`}
                        >
                          <img
                            src={temp.image_url}
                            alt={temp.name}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                          {/* 북마크 버튼 */}
                          <button
                            onClick={(e) => toggleBookmark(e, temp.id)}
                            className={`absolute top-1 left-1 p-1 bg-black/50 rounded-md transition-opacity ${bookmarkedTemplates.includes(temp.id) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                          >
                            {bookmarkedTemplates.includes(temp.id) ? (
                              <BookmarkCheck className="w-3 h-3 text-yellow-400" />
                            ) : (
                              <Bookmark className="w-3 h-3 text-white" />
                            )}
                          </button>
                          {selectedTemplate?.id === temp.id && (
                            <div className="absolute top-1 right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                              <Check className="w-2.5 h-2.5 text-primary-foreground" />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      이 카테고리에 템플릿이 없습니다
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
}
