"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Play,
  RefreshCw,
  Upload,
  Video,
  CreditCard,
  HardDrive,
  Plus,
  Download,
  MoreVertical,
  CheckCircle,
  Clock,
  AlertCircle,
  Trash2,
  Layers,
  ChevronDown,
} from "lucide-react";
import {
  ProgressCard,
  VideoEditModal,
  DashboardLayout,
} from "@/components";
import { createVideoWithOptions, getTaskStatus, getVideos, deleteVideo, getStats, type ChurchStats } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import UsageBar from "@/components/UsageBar";
import type { UploadFile, VideoItem, VideoOptions, ResourceTemplate } from "@/types";

const TEMPLATE_STORAGE_KEY = "qt_resource_templates";

export default function Home() {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();

  // 인증 체크 - 로그인 안 됐으면 로그인 페이지로
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // 교회 ID (사용자의 church_id 또는 기본값)
  const churchId = user?.church_id || "demo-church";
  // 상태
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [stats, setStats] = useState<ChurchStats | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [loadingVideos, setLoadingVideos] = useState(true);

  // 영상 옵션 상태
  const [videoTitle, setVideoTitle] = useState("");
  const [selectedClips, setSelectedClips] = useState<string[]>([]);
  const [selectedBGM, setSelectedBGM] = useState<string | null>(null);
  const [bgmVolume, setBgmVolume] = useState(0.12);
  const [generationMode, setGenerationMode] = useState<"default" | "natural">("natural"); // 생성 방식

  // 영상 편집 모달 상태
  const [editingVideoId, setEditingVideoId] = useState<string | null>(null);

  // 템플릿 상태
  const [templates, setTemplates] = useState<ResourceTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // Polling 관리
  const pollingIntervals = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // 영상 목록 로드
  const loadVideos = useCallback(async () => {
    if (!churchId) return;
    try {
      setLoadingVideos(true);
      const [videosData, statsData] = await Promise.all([
        getVideos(churchId),
        getStats(churchId).catch(() => null)
      ]);
      setVideos(videosData);
      if (statsData) setStats(statsData);
    } catch (error) {
      console.error("Failed to load videos:", error);
    } finally {
      setLoadingVideos(false);
    }
  }, [churchId]);

  // 초기 로드
  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // 템플릿 로드 (localStorage)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(TEMPLATE_STORAGE_KEY);
      if (saved) {
        try {
          setTemplates(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse templates:", e);
        }
      }
    }
  }, []);

  // 템플릿 선택 시 설정 적용
  const handleTemplateSelect = useCallback((templateId: string | null) => {
    setSelectedTemplateId(templateId);
    if (templateId) {
      const template = templates.find((t) => t.id === templateId);
      if (template) {
        setSelectedClips(template.clipIds);
        setSelectedBGM(template.bgmId);
        setBgmVolume(template.bgmVolume);
      }
    } else {
      // 템플릿 해제 시 기본값으로
      setSelectedClips([]);
      setSelectedBGM(null);
      setBgmVolume(0.12);
    }
  }, [templates]);

  // Polling 정리
  useEffect(() => {
    return () => {
      pollingIntervals.current.forEach((interval) => clearInterval(interval));
    };
  }, []);

  // 파일 추가
  const handleFilesAdd = useCallback((newFiles: File[]) => {
    const uploadFiles: UploadFile[] = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      name: file.name,
      size: file.size,
      status: "pending",
      progress: 0,
      step: "",
    }));
    setFiles((prev) => [...prev, ...uploadFiles]);
  }, []);

  // 파일 제거
  const handleFileRemove = useCallback((fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  // 파일 상태 업데이트
  const updateFileStatus = useCallback(
    (fileId: string, updates: Partial<UploadFile>) => {
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? { ...f, ...updates } : f))
      );
    },
    []
  );

  // 태스크 상태 Polling
  const startPolling = useCallback(
    (fileId: string, taskId: string) => {
      const poll = async () => {
        try {
          const status = await getTaskStatus(taskId);
          updateFileStatus(fileId, {
            progress: status.progress,
            step: status.step,
          });

          if (status.status === "SUCCESS" && status.result) {
            updateFileStatus(fileId, {
              status: "completed",
              progress: 100,
              step: "완료!",
              videoId: status.result.video_id,
              videoUrl: status.result.video_url,
            });
            const interval = pollingIntervals.current.get(fileId);
            if (interval) {
              clearInterval(interval);
              pollingIntervals.current.delete(fileId);
            }
            loadVideos();
          } else if (status.status === "FAILURE") {
            updateFileStatus(fileId, {
              status: "failed",
              error: status.error || "처리 실패",
            });
            const interval = pollingIntervals.current.get(fileId);
            if (interval) {
              clearInterval(interval);
              pollingIntervals.current.delete(fileId);
            }
          }
        } catch (error) {
          console.error("Polling error:", error);
        }
      };
      poll();
      const interval = setInterval(poll, 3000);
      pollingIntervals.current.set(fileId, interval);
    },
    [updateFileStatus, loadVideos]
  );

  // 업로드 시작
  const handleStartUpload = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === "pending");
    if (pendingFiles.length === 0) return;

    setIsUploading(true);

    for (const uploadFile of pendingFiles) {
      try {
        updateFileStatus(uploadFile.id, {
          status: "uploading",
          progress: 10,
          step: "업로드 중...",
        });

        const options: VideoOptions = {
          title: videoTitle || uploadFile.name.replace(/\.[^/.]+$/, ""),
          clipIds: selectedClips.length > 0 ? selectedClips : undefined,
          bgmId: selectedBGM || undefined,
          bgmVolume: bgmVolume,
          generateThumbnail: true, // 자연생성/기본설정 모두 썸네일 생성
          generationMode: generationMode,
        };

        const response = await createVideoWithOptions(
          uploadFile.file,
          options,
          churchId
        );

        updateFileStatus(uploadFile.id, {
          status: "processing",
          progress: 20,
          step: "영상 생성 시작...",
          taskId: response.task_id,
          videoId: response.video_ids[0],
        });

        startPolling(uploadFile.id, response.task_id);
      } catch (error) {
        console.error("Upload error:", error);
        updateFileStatus(uploadFile.id, {
          status: "failed",
          error: "업로드 실패",
        });
      }
    }

    setVideoTitle("");
    setSelectedClips([]);
    setSelectedBGM(null);
    setBgmVolume(0.12);
    setGenerationMode("natural");
    setSelectedTemplateId(null);
    setIsUploading(false);
  }, [files, updateFileStatus, startPolling, videoTitle, selectedClips, selectedBGM, bgmVolume, churchId]);

  // 영상 삭제 처리
  const handleDeleteVideo = useCallback(async (videoId: string) => {
    if (!confirm("정말 삭제하시겠습니까?")) return;
    try {
      await deleteVideo(videoId, churchId);
      loadVideos();
    } catch (error) {
      console.error("Delete error:", error);
    }
  }, [loadVideos, churchId]);

  // 영상 편집 모달 열기
  const handleEditVideo = useCallback((videoId: string) => {
    setEditingVideoId(videoId);
  }, []);

  // 처리 중인 파일들
  const processingFiles = files.filter(
    (f) => f.status === "uploading" || f.status === "processing"
  );

  // 대기 중인 파일들
  const pendingFiles = files.filter((f) => f.status === "pending");

  // 통계 계산
  const thisWeekVideos = videos.filter((v) => {
    const created = new Date(v.created_at);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return created >= weekAgo;
  }).length;

  // 로딩 중이면 로딩 표시
  if (authLoading) {
    return (
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-muted-foreground">로딩 중...</div>
        </div>
      </DashboardLayout>
    );
  }

  // 인증되지 않으면 빈 화면 (리다이렉트 중)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <DashboardLayout>
      {/* 헤더 */}
      <header className="bg-card border-b border-border px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">대시보드</h1>
            <p className="text-sm text-muted-foreground mt-1">
              홈 / 대시보드
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/subscription")}
              className="px-4 py-2.5 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium text-sm border border-border"
            >
              👑 구독 관리
            </button>
            <button
              onClick={() => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".mp3,.wav,.m4a";
                input.multiple = true;
                input.onchange = (e) => {
                  const files = Array.from((e.target as HTMLInputElement).files || []);
                  handleFilesAdd(files);
                };
                input.click();
              }}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
            >
              <Plus className="w-4 h-4" />
              새 업로드
            </button>
          </div>
        </div>
      </header>

      <div className="p-8 space-y-8">
        {/* Quick Upload 섹션 - 전체 영역 클릭 가능 */}
        <section
          className="bg-card rounded-xl border-2 border-dashed border-border hover:border-primary/50 p-10 cursor-pointer transition-all hover:bg-accent/30"
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.classList.remove("border-primary", "bg-primary/5");
            const droppedFiles = Array.from(e.dataTransfer.files);
            handleFilesAdd(droppedFiles);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.classList.add("border-primary", "bg-primary/5");
          }}
          onDragLeave={(e) => {
            e.currentTarget.classList.remove("border-primary", "bg-primary/5");
          }}
          onClick={() => {
            if (pendingFiles.length === 0) {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".mp3,.wav,.m4a";
              input.multiple = true;
              input.onchange = (e) => {
                const files = Array.from((e.target as HTMLInputElement).files || []);
                handleFilesAdd(files);
              };
              input.click();
            }
          }}
        >
          {pendingFiles.length > 0 ? (
            <div className="space-y-4" onClick={(e) => e.stopPropagation()}>
              <div className="text-center mb-4">
                <h2 className="text-lg font-semibold text-foreground">업로드할 파일</h2>
                <p className="text-sm text-muted-foreground">{pendingFiles.length}개 파일 선택됨</p>
              </div>

              {/* 통합된 생성 방식 & 템플릿 선택 */}
              <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
                <Layers className="w-5 h-5 text-muted-foreground" />
                <div className="flex-1">
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    생성 방식
                  </label>
                  <div className="relative">
                    <select
                      value={selectedTemplateId || generationMode}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value === "natural" || value === "default") {
                          setGenerationMode(value as "default" | "natural");
                          setSelectedTemplateId(null);
                        } else {
                          handleTemplateSelect(value);
                        }
                      }}
                      className="w-full appearance-none pl-3 pr-8 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="natural">자연 생성 (권장)</option>
                      <option value="default">기본 설정</option>
                      {templates.length > 0 && <option disabled>─────────────</option>}
                      {templates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name} (클립 {template.clipIds.length}개)
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
                {selectedTemplateId && (
                  <span className="text-xs text-primary font-medium">템플릿 적용됨</span>
                )}
              </div>

              {pendingFiles.map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 bg-background rounded-lg border border-border">
                  <span className="text-sm text-foreground">{file.name}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFileRemove(file.id);
                    }}
                    className="text-muted-foreground hover:text-destructive transition-colors"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleStartUpload();
                }}
                disabled={isUploading}
                className="w-full mt-4 flex items-center justify-center gap-2 px-6 py-3 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground font-medium rounded-lg transition-opacity"
              >
                <Play className="w-5 h-5" />
                {pendingFiles.length}개 파일 영상 생성 시작
              </button>
            </div>
          ) : (
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                <Upload className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Quick Upload</h2>
              <p className="text-muted-foreground mb-1">
                파일을 여기에 드래그하거나 클릭하여 선택하세요
              </p>
              <p className="text-sm text-muted-foreground">
                MP3, WAV, M4A 지원 (최대 100MB)
              </p>
            </div>
          )}
        </section>

        {/* 처리 중인 파일 표시 */}
        {processingFiles.length > 0 && (
          <section className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold mb-4">처리 중 ({processingFiles.length}개)</h2>
            <div className="space-y-3">
              {processingFiles.map((file) => (
                <ProgressCard key={file.id} file={file} />
              ))}
            </div>
          </section>
        )}

        {/* 사용량 표시 */}
        {user?.church_id && (
          <UsageBar
            current={user.monthly_usage || 0}
            limit={user.usage_limit || 7}
            onUpgradeClick={() => router.push("/subscription")}
          />
        )}

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">이번 주 영상</p>
                <p className="text-3xl font-bold text-foreground mt-2">{stats?.this_week_videos ?? 0}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  지난주 대비 {(stats?.this_week_videos ?? 0) - (stats?.last_week_videos ?? 0) >= 0 ? "+" : ""}
                  {(stats?.this_week_videos ?? 0) - (stats?.last_week_videos ?? 0)}개
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Video className="w-5 h-5 text-primary" />
              </div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">남은 크레딧</p>
                <p className="text-3xl font-bold text-foreground mt-2">{stats?.credits_remaining ?? 30}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.credits_reset_date ? `${stats.credits_reset_date.slice(5).replace("-", "/")} 갱신` : "매월 갱신"}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">사용 중인 저장공간</p>
                <p className="text-3xl font-bold text-foreground mt-2">{stats?.storage_used_percent ?? 0}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {((stats?.storage_limit_bytes ?? 0) / (1024 * 1024 * 1024)).toFixed(0)} GB 중{" "}
                  {((stats?.storage_used_bytes ?? 0) / (1024 * 1024)).toFixed(0)} MB 사용
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <HardDrive className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Recent Projects 섹션 */}
        <section className="bg-card rounded-xl border border-border">
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">최근 프로젝트</h2>
                <p className="text-sm text-muted-foreground">생성된 영상을 관리하고 다운로드하세요</p>
              </div>
              <button
                onClick={loadVideos}
                disabled={loadingVideos}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loadingVideos ? "animate-spin" : ""}`} />
                새로고침
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">상태</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">파일명</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">생성일</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">재생시간</th>
                  <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">작업</th>
                </tr>
              </thead>
              <tbody>
                {loadingVideos ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">로딩 중...</td>
                  </tr>
                ) : videos.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">아직 생성된 영상이 없습니다.</td>
                  </tr>
                ) : (
                  videos.slice(0, 10).map((video) => (
                    <tr key={video.id} className="border-b border-border hover:bg-accent/50 transition-colors">
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${video.status === "completed" ? "bg-green-100 text-green-700" :
                          video.status === "processing" ? "bg-yellow-100 text-yellow-700" :
                            video.status === "failed" ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-700"
                          }`}>
                          {video.status === "completed" ? <CheckCircle className="w-3 h-3" /> :
                            video.status === "processing" ? <Clock className="w-3 h-3" /> :
                              video.status === "failed" ? <AlertCircle className="w-3 h-3" /> : null}
                          {video.status === "completed" ? "완료" :
                            video.status === "processing" ? "처리중" :
                              video.status === "failed" ? "실패" : "대기중"}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm font-medium text-foreground">{video.title || "제목 없음"}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-muted-foreground">
                          {new Date(video.created_at).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-muted-foreground">
                          {video.duration ? `${Math.floor(video.duration / 60)}:${(video.duration % 60).toString().padStart(2, "0")}` : "-"}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-2">
                          {video.video_file_path && (
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/videos/${video.id}/download?file_type=video`}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                            >
                              <Download className="w-4 h-4" />
                              영상
                            </a>
                          )}
                          {video.srt_file_path && (
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/videos/${video.id}/download?file_type=srt`}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-border text-foreground text-sm font-medium rounded-lg hover:bg-accent transition-colors"
                            >
                              <Download className="w-4 h-4" />
                              자막
                            </a>
                          )}
                          <button
                            onClick={() => handleEditVideo(video.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-border text-foreground text-sm font-medium rounded-lg hover:bg-accent transition-colors"
                          >
                            수정
                          </button>
                          <button
                            onClick={() => handleDeleteVideo(video.id)}
                            className="inline-flex items-center gap-1.5 p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title="삭제"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* 영상 편집 모달 */}
      {editingVideoId && (
        <VideoEditModal
          videoId={editingVideoId}
          onClose={() => setEditingVideoId(null)}
          onUpdate={loadVideos}
          onDelete={loadVideos}
        />
      )}
    </DashboardLayout>
  );
}
