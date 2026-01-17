"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Film,
  Music,
  Layers,
  Play,
  Pause,
  Check,
  Plus,
  Trash2,
  Save,
  Volume2,
  VolumeX,
  ChevronDown,
  Shuffle,
  RefreshCw,
} from "lucide-react";
import { DashboardLayout } from "@/components";
import { getClips, getClipPacks, getBGMs } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { Clip, ClipPack, BGM, ResourceTemplate } from "@/types";

type TabType = "clips" | "bgm" | "templates";

const STORAGE_KEY = "qt_resource_templates";

export default function ResourcesPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // 인증 체크
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // 탭 상태
  const [activeTab, setActiveTab] = useState<TabType>("clips");

  // 클립 상태
  const [packs, setPacks] = useState<ClipPack[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedPack, setSelectedPack] = useState<string>("nature-1");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedClips, setSelectedClips] = useState<string[]>([]);
  const [loadingClips, setLoadingClips] = useState(true);
  const [previewClipId, setPreviewClipId] = useState<string | null>(null);

  // BGM 상태
  const [bgms, setBGMs] = useState<BGM[]>([]);
  const [selectedBGM, setSelectedBGM] = useState<string | null>(null);
  const [bgmVolume, setBgmVolume] = useState(0.12);
  const [loadingBGM, setLoadingBGM] = useState(true);
  const [playingBGMId, setPlayingBGMId] = useState<string | null>(null);

  // 템플릿 상태
  const [templates, setTemplates] = useState<ResourceTemplate[]>([]);
  const [newTemplateName, setNewTemplateName] = useState("");
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);

  // 팩 목록 로드
  useEffect(() => {
    async function loadPacks() {
      try {
        const data = await getClipPacks();
        setPacks(data);

        // moody 클립이 있는 nature-1 팩이 있으면 선택, 없으면 첫 번째 팩 선택
        if (data.length > 0) {
          const hasNature1 = data.some((p: ClipPack) => p.id === "nature-1");
          if (hasNature1) {
            setSelectedPack("nature-1");
          } else {
            setSelectedPack(data[0].id);
          }
        }
      } catch (error) {
        console.error("Failed to load packs:", error);
        setPacks([{
          id: "nature-1",
          name: "자연 기본팩",
          description: "자연/하늘 배경",
          thumbnail_url: "",
          clip_count: 5,
          is_free: true,
        }]);
      }
    }
    loadPacks();
  }, []);

  // 클립 목록 로드
  useEffect(() => {
    async function loadClips() {
      setLoadingClips(true);
      try {
        const data = await getClips(selectedPack);
        setClips(data);

        // moody 카테고리를 기본 선택
        if (data.length > 0) {
          const categories = [...new Set(data.map((c: Clip) => c.category))];
          const hasModdy = categories.includes("moody");
          setSelectedCategory(hasModdy ? "moody" : categories[0]);
        }
      } catch (error) {
        console.error("Failed to load clips:", error);
        setClips([]);
      } finally {
        setLoadingClips(false);
      }
    }
    loadClips();
  }, [selectedPack]);

  // BGM 목록 로드
  useEffect(() => {
    async function loadBGMs() {
      setLoadingBGM(true);
      try {
        const data = await getBGMs();
        setBGMs(data);
      } catch (error) {
        console.error("Failed to load BGMs:", error);
        setBGMs([
          { id: "bgm-peaceful", name: "평화로운 묵상", category: "peaceful", file_path: "", duration: 180 },
          { id: "bgm-hopeful", name: "소망의 빛", category: "hopeful", file_path: "", duration: 200 },
          { id: "bgm-grace", name: "은혜의 강", category: "graceful", file_path: "", duration: 240 },
        ]);
      } finally {
        setLoadingBGM(false);
      }
    }
    loadBGMs();
  }, []);

  // 템플릿 로드 (localStorage)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        try {
          setTemplates(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse templates:", e);
        }
      }
    }
  }, []);

  // 템플릿 저장
  const saveTemplates = useCallback((newTemplates: ResourceTemplate[]) => {
    setTemplates(newTemplates);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newTemplates));
    }
  }, []);

  // 카테고리 목록 추출
  const categories = ["all", ...new Set(clips.map((c) => c.category))];
  const filteredClips = selectedCategory === "all"
    ? clips
    : clips.filter((c) => c.category === selectedCategory);

  // 클립 선택/해제
  const toggleClip = (clipId: string) => {
    if (selectedClips.includes(clipId)) {
      setSelectedClips(selectedClips.filter((id) => id !== clipId));
    } else if (selectedClips.length < 10) {
      setSelectedClips([...selectedClips, clipId]);
    }
  };

  // BGM 재생/정지
  const togglePlayBGM = (bgm: BGM) => {
    if (!bgm.preview_url && !bgm.file_path) return;

    if (playingBGMId === bgm.id) {
      audioRef.current?.pause();
      setPlayingBGMId(null);
    } else {
      if (audioRef.current) {
        audioRef.current.src = bgm.preview_url || bgm.file_path;
        audioRef.current.volume = bgmVolume;
        audioRef.current.play();
        setPlayingBGMId(bgm.id);
      }
    }
  };

  // 새 템플릿 저장
  const createTemplate = () => {
    if (!newTemplateName.trim()) return;

    const newTemplate: ResourceTemplate = {
      id: `template-${Date.now()}`,
      name: newTemplateName.trim(),
      clipIds: selectedClips,
      bgmId: selectedBGM,
      bgmVolume: bgmVolume,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    saveTemplates([...templates, newTemplate]);
    setNewTemplateName("");
    setActiveTemplateId(newTemplate.id);
  };

  // 템플릿 불러오기
  const loadTemplate = (template: ResourceTemplate) => {
    setSelectedClips(template.clipIds);
    setSelectedBGM(template.bgmId);
    setBgmVolume(template.bgmVolume);
    setActiveTemplateId(template.id);
  };

  // 템플릿 삭제
  const deleteTemplate = (templateId: string) => {
    if (!confirm("이 템플릿을 삭제하시겠습니까?")) return;
    saveTemplates(templates.filter((t) => t.id !== templateId));
    if (activeTemplateId === templateId) {
      setActiveTemplateId(null);
    }
  };

  // 현재 설정을 활성 템플릿에 업데이트
  const updateActiveTemplate = () => {
    if (!activeTemplateId) return;

    const updated = templates.map((t) =>
      t.id === activeTemplateId
        ? {
            ...t,
            clipIds: selectedClips,
            bgmId: selectedBGM,
            bgmVolume: bgmVolume,
            updatedAt: new Date().toISOString(),
          }
        : t
    );
    saveTemplates(updated);
  };

  // 로딩 중
  if (authLoading) {
    return (
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-muted-foreground">로딩 중...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const bgmCategories = [...new Set(bgms.map((b) => b.category))];

  return (
    <DashboardLayout>
      {/* 숨겨진 오디오 엘리먼트 */}
      <audio ref={audioRef} onEnded={() => setPlayingBGMId(null)} className="hidden" />

      {/* 헤더 */}
      <header className="bg-card border-b border-border px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">배경 설정</h1>
            <p className="text-sm text-muted-foreground mt-1">
              배경 클립, BGM, 템플릿을 관리하세요
            </p>
          </div>
          {activeTemplateId && (
            <button
              onClick={updateActiveTemplate}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
            >
              <Save className="w-4 h-4" />
              변경사항 저장
            </button>
          )}
        </div>
      </header>

      <div className="p-8">
        {/* 탭 */}
        <div className="flex gap-1 p-1 bg-muted rounded-xl mb-6 w-fit">
          <button
            onClick={() => setActiveTab("clips")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === "clips"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Film className="w-4 h-4" />
            배경 클립
            {selectedClips.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-primary text-primary-foreground text-xs rounded-full">
                {selectedClips.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("bgm")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === "bgm"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Music className="w-4 h-4" />
            BGM
            {selectedBGM && (
              <span className="ml-1 w-2 h-2 bg-primary rounded-full" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("templates")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === "templates"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Layers className="w-4 h-4" />
            템플릿
            {templates.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-muted-foreground/20 text-muted-foreground text-xs rounded-full">
                {templates.length}
              </span>
            )}
          </button>
        </div>

        {/* 클립 탭 */}
        {activeTab === "clips" && (
          <section className="bg-card rounded-xl border border-border p-6 space-y-6">
            {/* 필터 */}
            <div className="flex items-center justify-between">
              <div className="flex gap-3">
                {/* 팩 선택 */}
                <div className="relative">
                  <select
                    value={selectedPack}
                    onChange={(e) => setSelectedPack(e.target.value)}
                    className="appearance-none pl-3 pr-8 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {packs.map((pack) => (
                      <option key={pack.id} value={pack.id}>
                        {pack.name} ({pack.clip_count})
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                </div>

                {/* 카테고리 필터 */}
                <div className="relative">
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="appearance-none pl-3 pr-8 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat === "all" ? "전체 카테고리" : cat}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  {selectedClips.length} / 10 선택됨
                </span>
                {selectedClips.length > 0 && (
                  <button
                    onClick={() => setSelectedClips([])}
                    className="text-sm text-red-500 hover:text-red-600"
                  >
                    선택 초기화
                  </button>
                )}
              </div>
            </div>

            {/* 클립 그리드 */}
            {loadingClips ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-6 h-6 text-muted-foreground animate-spin" />
              </div>
            ) : filteredClips.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Film className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>클립이 없습니다</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {filteredClips.map((clip, idx) => {
                  // 첫 번째 클립 디버그
                  if (idx === 0) {
                    console.log("[RENDER] First clip:", clip);
                    console.log("[RENDER] file_path:", clip.file_path);
                    console.log("[RENDER] file_path truthy?:", !!clip.file_path);
                  }
                  const isSelected = selectedClips.includes(clip.id);
                  const selectionIndex = selectedClips.indexOf(clip.id);

                  return (
                    <div
                      key={clip.id}
                      className={`relative aspect-video rounded-xl overflow-hidden cursor-pointer border-2 transition-all hover:scale-[1.02] ${
                        isSelected
                          ? "border-primary ring-2 ring-primary/30"
                          : "border-transparent hover:border-border"
                      }`}
                    >
                      {/* 비디오 미리보기 또는 플레이스홀더 */}
                      {clip.file_path ? (
                        <video
                          src={clip.file_path}
                          className="w-full h-full object-cover bg-muted"
                          muted
                          loop
                          playsInline
                          preload="auto"
                          onLoadedData={() => console.log("[VIDEO] Loaded:", clip.id)}
                          onError={(e) => console.error("[VIDEO] Error:", clip.id, e.currentTarget.error)}
                          onMouseEnter={(e) => {
                            setPreviewClipId(clip.id);
                            e.currentTarget.play();
                          }}
                          onMouseLeave={(e) => {
                            setPreviewClipId(null);
                            e.currentTarget.pause();
                            e.currentTarget.currentTime = 0;
                          }}
                          onClick={() => toggleClip(clip.id)}
                        />
                      ) : clip.thumbnail_url ? (
                        <img
                          src={clip.thumbnail_url}
                          alt={clip.name}
                          className="w-full h-full object-cover"
                          onClick={() => toggleClip(clip.id)}
                        />
                      ) : (
                        <div
                          className="w-full h-full bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center"
                          onClick={() => toggleClip(clip.id)}
                        >
                          <Film className="w-8 h-8 text-muted-foreground" />
                        </div>
                      )}

                      {/* 선택 번호 표시 */}
                      {isSelected && (
                        <div className="absolute top-2 right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center shadow-lg pointer-events-none">
                          <span className="text-xs text-primary-foreground font-bold">
                            {selectionIndex + 1}
                          </span>
                        </div>
                      )}

                      {/* 카테고리 뱃지 + 시간 */}
                      <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none">
                        <div className="px-2 py-1 bg-black/60 rounded-lg text-[11px] text-white font-medium">
                          {clip.category}
                        </div>
                        {clip.duration > 0 && (
                          <div className="px-2 py-1 bg-black/60 rounded-lg text-[11px] text-white font-medium">
                            {Math.floor(clip.duration / 60)}:{String(Math.floor(clip.duration % 60)).padStart(2, '0')}
                          </div>
                        )}
                      </div>

                      {/* 재생 중 표시 */}
                      {previewClipId === clip.id && (
                        <div className="absolute top-2 left-2 px-2 py-1 bg-red-500 rounded-lg text-[10px] text-white font-bold animate-pulse pointer-events-none">
                          LIVE
                        </div>
                      )}

                      {/* 호버 오버레이 (비디오 없을 때만) */}
                      {!clip.file_path && (
                        <div className="absolute inset-0 bg-black/0 hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 hover:opacity-100 pointer-events-none">
                          <Play className="w-10 h-10 text-white drop-shadow-lg" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* BGM 탭 */}
        {activeTab === "bgm" && (
          <section className="bg-card rounded-xl border border-border p-6 space-y-6">
            {/* 볼륨 조절 */}
            <div className="flex items-center gap-4 p-4 bg-muted rounded-xl">
              <button
                onClick={() => setBgmVolume(bgmVolume === 0 ? 0.12 : 0)}
                className="p-2 hover:bg-background rounded-lg transition-colors"
              >
                {bgmVolume === 0 ? (
                  <VolumeX className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <Volume2 className="w-5 h-5 text-primary" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="0.5"
                step="0.01"
                value={bgmVolume}
                onChange={(e) => setBgmVolume(parseFloat(e.target.value))}
                className="flex-1 h-2 bg-background rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <span className="text-sm text-muted-foreground w-12 text-right">
                {Math.round(bgmVolume * 100)}%
              </span>
            </div>

            {/* BGM 목록 */}
            {loadingBGM ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-6 h-6 text-muted-foreground animate-spin" />
              </div>
            ) : bgms.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Music className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>사용 가능한 BGM이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-6">
                {bgmCategories.map((category) => (
                  <div key={category}>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                      {category}
                    </h3>
                    <div className="space-y-2">
                      {bgms
                        .filter((b) => b.category === category)
                        .map((bgm) => {
                          const isSelected = selectedBGM === bgm.id;
                          const isPlaying = playingBGMId === bgm.id;

                          return (
                            <div
                              key={bgm.id}
                              onClick={() => setSelectedBGM(isSelected ? null : bgm.id)}
                              className={`flex items-center gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                                isSelected
                                  ? "border-primary bg-primary/5"
                                  : "border-border hover:border-primary/50"
                              }`}
                            >
                              {/* 재생 버튼 */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  togglePlayBGM(bgm);
                                }}
                                disabled={!bgm.preview_url && !bgm.file_path}
                                className={`p-3 rounded-full transition-colors ${
                                  isPlaying
                                    ? "bg-primary text-primary-foreground"
                                    : "bg-muted text-muted-foreground hover:bg-primary/20"
                                }`}
                              >
                                {isPlaying ? (
                                  <Pause className="w-4 h-4" />
                                ) : (
                                  <Play className="w-4 h-4" />
                                )}
                              </button>

                              {/* BGM 정보 */}
                              <div className="flex-1 min-w-0">
                                <p className="font-medium truncate">{bgm.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  {Math.floor(bgm.duration / 60)}:
                                  {(bgm.duration % 60).toString().padStart(2, "0")}
                                </p>
                              </div>

                              {/* 선택 표시 */}
                              {isSelected && (
                                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                                  <Check className="w-5 h-5 text-primary-foreground" />
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 템플릿 탭 */}
        {activeTab === "templates" && (
          <section className="space-y-6">
            {/* 새 템플릿 저장 */}
            <div className="bg-card rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4">현재 설정 저장</h3>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  placeholder="템플릿 이름 (예: 잔잔한 묵상)"
                  className="flex-1 px-4 py-2.5 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <button
                  onClick={createTemplate}
                  disabled={!newTemplateName.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  <Plus className="w-4 h-4" />
                  저장
                </button>
              </div>
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">
                  현재 설정: 클립 {selectedClips.length}개,
                  BGM {selectedBGM ? "선택됨" : "없음"},
                  볼륨 {Math.round(bgmVolume * 100)}%
                </p>
              </div>
            </div>

            {/* 저장된 템플릿 목록 */}
            <div className="bg-card rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4">저장된 템플릿</h3>

              {templates.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>저장된 템플릿이 없습니다</p>
                  <p className="text-sm mt-1">클립과 BGM을 선택한 후 템플릿으로 저장하세요</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {templates.map((template) => {
                    const isActive = activeTemplateId === template.id;

                    return (
                      <div
                        key={template.id}
                        className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                          isActive
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <div
                          onClick={() => loadTemplate(template)}
                          className="flex-1 cursor-pointer"
                        >
                          <div className="flex items-center gap-3">
                            <h4 className="font-medium">{template.name}</h4>
                            {isActive && (
                              <span className="px-2 py-0.5 bg-primary text-primary-foreground text-xs rounded-full">
                                활성
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            클립 {template.clipIds.length}개 /
                            BGM {template.bgmId ? "있음" : "없음"} /
                            볼륨 {Math.round(template.bgmVolume * 100)}%
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            수정: {new Date(template.updatedAt).toLocaleDateString("ko-KR")}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => loadTemplate(template)}
                            className="px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                          >
                            불러오기
                          </button>
                          <button
                            onClick={() => deleteTemplate(template.id)}
                            className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </DashboardLayout>
  );
}
