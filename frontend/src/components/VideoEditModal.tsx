"use client";

import { useState, useEffect, useRef } from "react";
import {
  X,
  Save,
  Play,
  Pause,
  Download,
  Image,
  Edit3,
  Trash2,
  Plus,
  Loader2,
  Volume2,
  VolumeX,
  RefreshCw,
} from "lucide-react";
import type { VideoDetail, SubtitleSegment } from "@/types";
import {
  getVideoDetail,
  getSubtitles,
  updateVideoTitle,
  updateSubtitles,
  generateThumbnail,
  uploadThumbnail,
  deleteVideo,
  addReplacementEntries,
  generateQTThumbnail,
  saveThumbnailLayout,
  getThumbnailLayout,
  regenerateVideo,
} from "@/lib/api";
import ThumbnailConceptPicker from "./ThumbnailConceptPicker";
import ThumbnailEditor, { type IntroSettings } from "./ThumbnailEditor";
interface VideoEditModalProps {
  videoId: string;
  onClose: () => void;
  onUpdate?: () => void;
  onDelete?: () => void;
}

type Tab = "preview" | "subtitle" | "thumbnail";

export default function VideoEditModal({
  videoId,
  onClose,
  onUpdate,
  onDelete,
}: VideoEditModalProps) {
  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("preview");

  // 편집 상태
  const [title, setTitle] = useState("");
  const [subtitles, setSubtitles] = useState<SubtitleSegment[]>([]);
  const [originalSubtitles, setOriginalSubtitles] = useState<SubtitleSegment[]>([]); // 원본 자막 (수정 감지용)
  const [thumbnailTimestamp, setThumbnailTimestamp] = useState(5);
  const [selectedTemplateUrl, setSelectedTemplateUrl] = useState<string | null>(null);

  // 인트로 설정 상태
  const [introSettings, setIntroSettings] = useState<IntroSettings>({
    useAsIntro: true,
    introDuration: 3,
    separateIntro: false,
    useAsOutro: true,
    outroDuration: 3,
  });

  // 저장된 레이아웃 (텍스트 박스 포함)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [savedLayout, setSavedLayout] = useState<any>(null);

  // 비디오 플레이어
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // 데이터 로드
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const videoData = await getVideoDetail(videoId);
        setVideo(videoData);
        setTitle(videoData.title || "");

        // 자막 로드
        const subs = await getSubtitles(videoId);
        setSubtitles(subs);
        setOriginalSubtitles(JSON.parse(JSON.stringify(subs))); // 원본 깊은 복사 저장

        // 저장된 썸네일 레이아웃 로드
        try {
          const layoutData = await getThumbnailLayout(videoId);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const layout = layoutData.layout as any;
          if (layout) {
            // 전체 레이아웃 저장 (텍스트 박스 포함)
            setSavedLayout(layout);

            // 배경 이미지 URL 복원 (snake_case from backend)
            if (layout.background_image_url) {
              setSelectedTemplateUrl(layout.background_image_url);
            }
            // 인트로 설정 복원
            if (layout.intro_settings) {
              setIntroSettings({
                useAsIntro: layout.intro_settings.useAsIntro ?? true,
                introDuration: layout.intro_settings.introDuration ?? 3,
                separateIntro: layout.intro_settings.separateIntro ?? false,
                separateIntroImageUrl: layout.intro_settings.separateIntroImageUrl,
              });
            }
          } else {
            // 이 영상에 저장된 레이아웃이 없으면 기본 템플릿 확인
            const defaultLayout = localStorage.getItem('qt_default_thumbnail_layout');
            if (defaultLayout) {
              try {
                const parsed = JSON.parse(defaultLayout);
                setSavedLayout({
                  text_boxes: parsed.textBoxes,
                  background_image_url: parsed.backgroundImageUrl,
                  intro_settings: parsed.introSettings,
                });
                if (parsed.backgroundImageUrl) {
                  setSelectedTemplateUrl(parsed.backgroundImageUrl);
                }
                if (parsed.introSettings) {
                  setIntroSettings({
                    useAsIntro: parsed.introSettings.useAsIntro ?? true,
                    introDuration: parsed.introSettings.introDuration ?? 3,
                    separateIntro: parsed.introSettings.separateIntro ?? false,
                    separateIntroImageUrl: parsed.introSettings.separateIntroImageUrl,
                  });
                }
              } catch (e) {
                console.log("Failed to parse default layout:", e);
              }
            }
          }
        } catch (layoutError) {
          console.log("No saved layout found:", layoutError);
          // 서버에서 레이아웃 로드 실패 시에도 기본 템플릿 확인
          const defaultLayout = localStorage.getItem('qt_default_thumbnail_layout');
          if (defaultLayout) {
            try {
              const parsed = JSON.parse(defaultLayout);
              setSavedLayout({
                text_boxes: parsed.textBoxes,
                background_image_url: parsed.backgroundImageUrl,
                intro_settings: parsed.introSettings,
              });
              if (parsed.backgroundImageUrl) {
                setSelectedTemplateUrl(parsed.backgroundImageUrl);
              }
              if (parsed.introSettings) {
                setIntroSettings({
                  useAsIntro: parsed.introSettings.useAsIntro ?? true,
                  introDuration: parsed.introSettings.introDuration ?? 3,
                  separateIntro: parsed.introSettings.separateIntro ?? false,
                  separateIntroImageUrl: parsed.introSettings.separateIntroImageUrl,
                });
              }
            } catch (e) {
              console.log("Failed to parse default layout:", e);
            }
          }
        }
      } catch (error) {
        console.error("Failed to load video:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [videoId]);

  // 탭 전환 시 비디오 상태 초기화
  useEffect(() => {
    if (activeTab !== "preview") {
      setIsPlaying(false);
    }
  }, [activeTab]);

  // 제목 저장
  const handleSaveTitle = async () => {
    if (!video) return;
    setSaving(true);
    try {
      await updateVideoTitle(videoId, title, video.church_id);
      onUpdate?.();
    } catch (error) {
      console.error("Failed to save title:", error);
    } finally {
      setSaving(false);
    }
  };

  // 자막 수정 감지 및 사전 저장
  const detectAndSaveReplacements = async (churchId: string) => {
    const replacements: Array<{ original: string; replacement: string }> = [];

    // 원본과 수정된 자막 비교
    for (const currentSub of subtitles) {
      const originalSub = originalSubtitles.find((s) => s.id === currentSub.id);
      if (!originalSub) continue;

      // 텍스트가 변경된 경우
      if (originalSub.text !== currentSub.text && originalSub.text.trim() && currentSub.text.trim()) {
        // 단어 단위로 비교하여 변경된 부분 추출
        const originalWords = originalSub.text.split(/\s+/);
        const currentWords = currentSub.text.split(/\s+/);

        // 같은 위치의 단어가 다른 경우 치환 항목으로 추가
        const minLen = Math.min(originalWords.length, currentWords.length);
        for (let i = 0; i < minLen; i++) {
          if (originalWords[i] !== currentWords[i] && originalWords[i].length >= 2 && currentWords[i].length >= 2) {
            // 이미 추가된 항목인지 확인
            const exists = replacements.some(
              (r) => r.original === originalWords[i] && r.replacement === currentWords[i]
            );
            if (!exists) {
              replacements.push({
                original: originalWords[i],
                replacement: currentWords[i],
              });
            }
          }
        }
      }
    }

    // 치환 항목이 있으면 API 호출
    if (replacements.length > 0) {
      try {
        const result = await addReplacementEntries(churchId, replacements);
        console.log(`자동 치환 사전 업데이트: ${result.added}개 추가, ${result.updated}개 갱신`);
      } catch (error) {
        // 사전 저장 실패해도 자막 저장은 계속 진행
        console.error("Failed to save replacements to dictionary:", error);
      }
    }
  };

  // 자막 저장
  const handleSaveSubtitles = async () => {
    if (!video) return;
    setSaving(true);
    try {
      // 1. 수정 내용을 자동으로 사전에 저장
      await detectAndSaveReplacements(video.church_id);

      // 2. 자막 저장
      await updateSubtitles(videoId, subtitles, video.church_id);

      // 3. 원본 자막을 현재 자막으로 업데이트 (다음 수정 감지용)
      setOriginalSubtitles(JSON.parse(JSON.stringify(subtitles)));

      onUpdate?.();
    } catch (error) {
      console.error("Failed to save subtitles:", error);
    } finally {
      setSaving(false);
    }
  };

  // 썸네일 생성
  const handleGenerateThumbnail = async () => {
    setSaving(true);
    try {
      const result = await generateThumbnail(videoId, thumbnailTimestamp);
      setVideo((prev) =>
        prev ? { ...prev, thumbnail_url: result.thumbnail_url } : null
      );
      onUpdate?.();
    } catch (error) {
      console.error("Failed to generate thumbnail:", error);
    } finally {
      setSaving(false);
    }
  };

  // 썸네일 업로드
  const handleThumbnailUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSaving(true);
    try {
      const result = await uploadThumbnail(videoId, file);
      setVideo((prev) =>
        prev ? { ...prev, thumbnail_url: result.thumbnail_url } : null
      );
      onUpdate?.();
    } catch (error) {
      console.error("Failed to upload thumbnail:", error);
    } finally {
      setSaving(false);
    }
  };

  // 영상 재생성
  const handleRegenerate = async () => {
    if (!video) return;
    if (!confirm("현재 설정(자막, 배경 등)으로 영상을 다시 만드시겠습니까?\n이전 영상은 덮어씌워집니다.")) return;

    setRegenerating(true);
    try {
      // 1. 자막 저장 (선택 사항이지만 안전하게)
      await updateSubtitles(videoId, subtitles, video.church_id);

      // 2. 재생성 요청
      await regenerateVideo(videoId, {}, video.church_id);

      alert("영상 재생성이 시작되었습니다!\n완료되면 알림을 보내드리거나 목록에서 확인할 수 있습니다.");
      onClose(); // 모달 닫기 (백그라운드 작업이므로)
    } catch (error: unknown) {
      console.error("Failed to regenerate video:", error);

      // 상세 에러 메시지 파싱
      let errorMessage = "영상 재생성 요청에 실패했습니다.";
      let errorDetail = "";

      if (error instanceof Error) {
        errorDetail = error.message;
      }

      // API 응답에서 상세 에러 추출
      if (typeof error === 'object' && error !== null && 'response' in error) {
        const res = error as { response?: { data?: { detail?: string; error?: string } } };
        const detail = res.response?.data?.detail || res.response?.data?.error;
        if (detail) {
          errorDetail = detail;
        }
      }

      // 사용자 친화적 에러 메시지 매핑
      if (errorDetail.includes("audio") || errorDetail.includes("mp3") || errorDetail.includes("m4a")) {
        errorMessage = "음성 파일에 문제가 있습니다.\n\n확인사항:\n- 지원 형식: MP3, M4A, WAV\n- 파일이 손상되지 않았는지 확인";
      } else if (errorDetail.includes("clip") || errorDetail.includes("background")) {
        errorMessage = "배경 클립에 문제가 있습니다.\n\n확인사항:\n- 선택된 배경 클립이 유효한지 확인\n- 다른 배경 팩을 선택해보세요";
      } else if (errorDetail.includes("bgm") || errorDetail.includes("music")) {
        errorMessage = "BGM에 문제가 있습니다.\n\n확인사항:\n- 선택된 BGM이 유효한지 확인\n- 다른 BGM을 선택해보세요";
      } else if (errorDetail.includes("duration") || errorDetail.includes("length") || errorDetail.includes("too long")) {
        errorMessage = "영상 길이에 문제가 있습니다.\n\n확인사항:\n- 음성 파일 길이 확인 (최대 10분 권장)\n- 너무 긴 파일은 분할해주세요";
      } else if (errorDetail.includes("srt") || errorDetail.includes("subtitle")) {
        errorMessage = "자막 파일에 문제가 있습니다.\n\n확인사항:\n- 자막이 올바르게 생성되었는지 확인\n- 자막 편집기에서 오류가 없는지 확인";
      } else if (errorDetail.includes("thumbnail") || errorDetail.includes("intro")) {
        errorMessage = "썸네일/인트로 설정에 문제가 있습니다.\n\n확인사항:\n- 썸네일 레이아웃이 저장되었는지 확인\n- 인트로 설정을 다시 확인해주세요";
      } else if (errorDetail) {
        errorMessage += `\n\n상세: ${errorDetail}`;
      }

      alert(errorMessage + "\n\n문제가 지속되면 관리자에게 문의해주세요.");
    } finally {
      setRegenerating(false);
    }
  };

  // 영상 삭제
  const handleDelete = async () => {
    if (!video) return;
    if (!confirm("정말 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) return;

    try {
      await deleteVideo(videoId, video.church_id);
      onDelete?.();
      onClose();
    } catch (error) {
      console.error("Failed to delete video:", error);
    }
  };

  // 자막 편집 함수들
  const updateSubtitle = (id: number, updates: Partial<SubtitleSegment>) => {
    setSubtitles((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates } : s))
    );
  };

  const addSubtitle = () => {
    const lastSub = subtitles[subtitles.length - 1];
    const newSub: SubtitleSegment = {
      id: Date.now(),
      start: lastSub ? lastSub.end + 0.5 : 0,
      end: lastSub ? lastSub.end + 3 : 3,
      text: "",
    };
    setSubtitles([...subtitles, newSub]);
  };

  const removeSubtitle = (id: number) => {
    setSubtitles((prev) => prev.filter((s) => s.id !== id));
  };

  // 현재 시간의 자막 하이라이트
  const currentSubtitle = subtitles.find(
    (s) => currentTime >= s.start && currentTime <= s.end
  );

  // 시간 포맷팅
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "preview", label: "미리보기", icon: <Play className="w-4 h-4" /> },
    { id: "subtitle", label: "자막", icon: <Edit3 className="w-4 h-4" /> },
    { id: "thumbnail", label: "썸네일", icon: <Image className="w-4 h-4" /> },
  ];

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-8">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-8">
          <p className="text-red-500">영상을 불러올 수 없습니다.</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-100 rounded-lg"
          >
            닫기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold truncate">{video.title}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 disabled:bg-green-300 text-white rounded-lg text-sm transition-colors mr-2"
              title="현재 자막/설정으로 영상 다시 만들기"
            >
              {regenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              영상 재생성
            </button>
            <button
              onClick={handleDelete}
              className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg text-red-500 transition-colors"
              title="삭제"
            >
              <Trash2 className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${activeTab === tab.id
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
                }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* 콘텐츠 */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* 미리보기 탭 */}
          {activeTab === "preview" && (
            <div className="space-y-4">
              {/* 비디오 플레이어 */}
              <div className="relative aspect-video bg-black rounded-xl overflow-hidden">
                {video.video_file_path ? (
                  <>
                    <video
                      ref={videoRef}
                      src={video.video_file_path}
                      className="w-full h-full object-contain"
                      playsInline
                      onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => setIsPlaying(false)}
                    />
                    {/* 자막은 영상에 burn-in 되어 있으므로 별도 오버레이 불필요 */}
                  </>
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-500">
                    영상 없음
                  </div>
                )}
              </div>

              {/* 컨트롤 */}
              <div className="space-y-3">
                {/* 타임라인 바 */}
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16 text-right font-mono">
                    {formatTime(currentTime)}
                  </span>
                  <input
                    type="range"
                    min="0"
                    max={video.duration || 100}
                    step="0.1"
                    value={currentTime}
                    onChange={(e) => {
                      const time = parseFloat(e.target.value);
                      if (videoRef.current) {
                        videoRef.current.currentTime = time;
                      }
                      setCurrentTime(time);
                    }}
                    className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <span className="text-xs text-gray-500 w-16 font-mono">
                    {formatTime(video.duration || 0)}
                  </span>
                </div>

                {/* 재생 버튼 + 음량 + 다운로드 */}
                <div className="flex items-center gap-4">
                  <button
                    onClick={() =>
                      isPlaying ? videoRef.current?.pause() : videoRef.current?.play()
                    }
                    className="p-3 bg-blue-500 hover:bg-blue-600 text-white rounded-full transition-colors"
                  >
                    {isPlaying ? (
                      <Pause className="w-5 h-5" />
                    ) : (
                      <Play className="w-5 h-5" />
                    )}
                  </button>

                  {/* 음량 조절 */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const newMuted = !isMuted;
                        setIsMuted(newMuted);
                        if (videoRef.current) {
                          videoRef.current.muted = newMuted;
                        }
                      }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title={isMuted ? "음소거 해제" : "음소거"}
                    >
                      {isMuted ? (
                        <VolumeX className="w-5 h-5 text-gray-500" />
                      ) : (
                        <Volume2 className="w-5 h-5 text-gray-500" />
                      )}
                    </button>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={isMuted ? 0 : volume}
                      onChange={(e) => {
                        const newVolume = parseFloat(e.target.value);
                        setVolume(newVolume);
                        setIsMuted(newVolume === 0);
                        if (videoRef.current) {
                          videoRef.current.volume = newVolume;
                          videoRef.current.muted = newVolume === 0;
                        }
                      }}
                      className="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                  </div>

                  {video.video_file_path && (
                    <a
                      href={video.video_file_path}
                      download
                      className="ml-auto flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-sm transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      다운로드
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 자막 탭 */}
          {activeTab === "subtitle" && (
            <div className="space-y-4">
              {/* 영상 제목 */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-xl">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  영상 제목
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="영상 제목을 입력하세요"
                    className="flex-1 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleSaveTitle}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg transition-colors"
                  >
                    {saving ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* 자막 헤더 */}
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  {subtitles.length}개 자막 세그먼트
                </p>
                <button
                  onClick={addSubtitle}
                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-sm transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  추가
                </button>
              </div>

              {/* 자막 리스트 */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {subtitles.map((sub, index) => (
                  <div
                    key={sub.id}
                    className={`p-3 rounded-xl border transition-colors ${currentSubtitle?.id === sub.id
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      : "border-gray-200 dark:border-gray-700"
                      }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-gray-400">
                        #{index + 1}
                      </span>
                      <input
                        type="number"
                        value={sub.start}
                        onChange={(e) =>
                          updateSubtitle(sub.id, { start: parseFloat(e.target.value) })
                        }
                        step="0.1"
                        className="w-20 px-2 py-1 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded"
                      />
                      <span className="text-gray-400">~</span>
                      <input
                        type="number"
                        value={sub.end}
                        onChange={(e) =>
                          updateSubtitle(sub.id, { end: parseFloat(e.target.value) })
                        }
                        step="0.1"
                        className="w-20 px-2 py-1 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded"
                      />
                      <button
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = sub.start;
                          }
                        }}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                        title="이 자막으로 이동"
                      >
                        <Play className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => removeSubtitle(sub.id)}
                        className="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded text-red-500"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    <textarea
                      value={sub.text}
                      onChange={(e) =>
                        updateSubtitle(sub.id, { text: e.target.value })
                      }
                      rows={2}
                      className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="자막 텍스트..."
                    />
                  </div>
                ))}
              </div>

              <button
                onClick={handleSaveSubtitles}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg transition-colors"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                자막 저장
              </button>
            </div>
          )}

          {/* 썸네일 탭 */}
          {activeTab === "thumbnail" && (
            <div className="space-y-6">
              {/* 배경이 선택되면 에디터, 아니면 컨셉 선택 */}
              {selectedTemplateUrl ? (
                <>
                  {/* 드래그 에디터 */}
                  <ThumbnailEditor
                    backgroundImageUrl={selectedTemplateUrl}
                    initialLayout={savedLayout ? {
                      textBoxes: savedLayout.text_boxes,
                      backgroundImageUrl: savedLayout.background_image_url,
                      introSettings: savedLayout.intro_settings,
                    } : undefined}
                    mainTitle={video.title || "제목을 입력하세요"}
                    subTitle=""
                    dateText={new Date().toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" }).replace(",", "")}
                    bibleVerse=""
                    onGenerate={async (layout) => {
                      if (!layout.backgroundImageUrl) {
                        alert("배경 이미지를 선택해주세요.");
                        return;
                      }

                      setSaving(true);
                      try {
                        // API 호출하여 썸네일 생성 + DB 저장
                        const result = await generateQTThumbnail(
                          {
                            textBoxes: layout.textBoxes.map(box => ({
                              id: box.id,
                              text: box.text,
                              x: box.x,
                              y: box.y,
                              fontSize: box.fontSize,
                              fontFamily: box.fontFamily,
                              color: box.color,
                              visible: box.visible,
                            })),
                            backgroundImageUrl: layout.backgroundImageUrl,
                            introSettings: layout.introSettings,
                          },
                          { videoId }  // videoId 전달하여 DB에 저장
                        );

                        // 썸네일 URL 업데이트
                        setVideo((prev) =>
                          prev ? { ...prev, thumbnail_url: result.thumbnail_url } : null
                        );

                        alert("썸네일이 생성되어 저장되었습니다!");
                        onUpdate?.();
                      } catch (error) {
                        console.error("썸네일 생성 실패:", error);
                        alert("썸네일 생성에 실패했습니다. 다시 시도해주세요.");
                      } finally {
                        setSaving(false);
                      }
                    }}
                    onSave={async (layout) => {
                      setSaving(true);
                      try {
                        const saveData = {
                          textBoxes: layout.textBoxes.map(box => ({
                            id: box.id,
                            text: box.text,
                            x: box.x,
                            y: box.y,
                            fontSize: box.fontSize,
                            fontFamily: box.fontFamily,
                            color: box.color,
                            visible: box.visible,
                          })),
                          backgroundImageUrl: layout.backgroundImageUrl,
                          introSettings: layout.introSettings,
                        };

                        const result = await saveThumbnailLayout(videoId, saveData);

                        // 저장 결과 상세 표시
                        const introStatus = layout.introSettings?.useAsIntro
                          ? `인트로: ${layout.introSettings.introDuration}초`
                          : "인트로: 사용 안 함";
                        const textCount = layout.textBoxes.filter(b => b.visible).length;

                        alert(`레이아웃 저장 완료!\n\n- 텍스트 박스: ${textCount}개\n- 배경 이미지: ${layout.backgroundImageUrl ? "설정됨" : "없음"}\n- ${introStatus}`);

                        console.log("[썸네일 저장 성공]", { videoId, saveData, result });
                      } catch (error: unknown) {
                        console.error("레이아웃 저장 실패:", error);

                        // 상세 에러 메시지
                        let errorMessage = "레이아웃 저장에 실패했습니다.";
                        if (error instanceof Error) {
                          errorMessage += `\n\n원인: ${error.message}`;
                        }
                        if (typeof error === 'object' && error !== null && 'response' in error) {
                          const res = error as { response?: { data?: { detail?: string } } };
                          if (res.response?.data?.detail) {
                            errorMessage += `\n\n서버 응답: ${res.response.data.detail}`;
                          }
                        }

                        alert(errorMessage + "\n\n문제가 지속되면 관리자에게 문의해주세요.");
                      } finally {
                        setSaving(false);
                      }
                    }}
                    onChangeBackground={() => setSelectedTemplateUrl(null)}
                    introSettings={introSettings}
                    onIntroSettingsChange={setIntroSettings}
                  />
                </>
              ) : (
                <>
                  {/* 컨셉 선택 (배경만 선택, 제목 입력 없음) */}
                  <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      1단계: 배경 이미지 선택
                    </p>
                    <ThumbnailConceptPicker
                      onSelect={(url) => {
                        // 배경 선택하면 에디터로 전환
                        setSelectedTemplateUrl(url);
                      }}
                    />
                  </div>

                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="px-2 bg-white dark:bg-gray-800 text-gray-500">
                        또는
                      </span>
                    </div>
                  </div>

                  {/* 영상에서 추출 */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-xl">
                    <p className="text-sm font-medium mb-3">영상에서 배경 추출</p>
                    <div className="flex items-center gap-3">
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        시간 (초):
                      </label>
                      <input
                        type="number"
                        value={thumbnailTimestamp}
                        onChange={(e) => setThumbnailTimestamp(parseInt(e.target.value))}
                        min="0"
                        max={video.duration || 60}
                        className="w-20 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
                      />
                      <button
                        onClick={async () => {
                          setSaving(true);
                          try {
                            const result = await generateThumbnail(videoId, thumbnailTimestamp);
                            setSelectedTemplateUrl(result.thumbnail_url);
                            setVideo((prev) =>
                              prev ? { ...prev, thumbnail_url: result.thumbnail_url } : null
                            );
                          } catch (error) {
                            console.error("Failed to generate thumbnail:", error);
                          } finally {
                            setSaving(false);
                          }
                        }}
                        disabled={saving}
                        className="px-4 py-2 bg-gray-500 hover:bg-gray-600 disabled:bg-gray-300 text-white rounded-lg transition-colors"
                      >
                        {saving ? "추출 중..." : "추출 후 편집"}
                      </button>
                    </div>
                  </div>

                  {/* 직접 업로드 */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-xl">
                    <p className="text-sm font-medium mb-3">직접 업로드</p>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        setSaving(true);
                        try {
                          const result = await uploadThumbnail(videoId, file);
                          setSelectedTemplateUrl(result.thumbnail_url);
                          setVideo((prev) =>
                            prev ? { ...prev, thumbnail_url: result.thumbnail_url } : null
                          );
                        } catch (error) {
                          console.error("Failed to upload thumbnail:", error);
                        } finally {
                          setSaving(false);
                        }
                      }}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
