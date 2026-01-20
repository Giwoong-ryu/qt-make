"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Upload,
  Play,
  X,
  Music,
  Film,
  FileAudio,
  Layers,
  ChevronDown,
} from "lucide-react";
import { DashboardLayout, ProgressCard } from "@/components";
import { createVideoWithOptions, getTaskStatus } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { UploadFile, VideoOptions } from "@/types";

export default function UploadPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();

  // 인증 체크
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const churchId = user?.church_id || "demo-church";

  // 상태
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // 영상 옵션
  const [videoTitle, setVideoTitle] = useState("");
  const [bgmVolume, setBgmVolume] = useState(0.12);
  const [generationMode, setGenerationMode] = useState<"default" | "natural">("natural"); // 기본설정 or 자연생성

  // Polling 관리
  const pollingIntervals = useRef<Map<string, NodeJS.Timeout>>(new Map());

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
    [updateFileStatus]
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
    setBgmVolume(0.12);
    setIsUploading(false);
  }, [files, updateFileStatus, startPolling, videoTitle, bgmVolume, churchId]);

  // 파일 분류
  const pendingFiles = files.filter((f) => f.status === "pending");
  const processingFiles = files.filter(
    (f) => f.status === "uploading" || f.status === "processing"
  );
  const completedFiles = files.filter((f) => f.status === "completed");
  const failedFiles = files.filter((f) => f.status === "failed");

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

  return (
    <DashboardLayout>
      {/* 헤더 */}
      <header className="bg-card border-b border-border px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">업로드</h1>
            <p className="text-sm text-muted-foreground mt-1">
              홈 / 업로드
            </p>
          </div>
        </div>
      </header>

      <div className="p-8 space-y-8">
        {/* 드래그 앤 드롭 영역 */}
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
        >
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-xl font-semibold text-foreground mb-2">파일 업로드</h2>
            <p className="text-muted-foreground mb-1">
              파일을 여기에 드래그하거나 클릭하여 선택하세요
            </p>
            <p className="text-sm text-muted-foreground">
              MP3, WAV, M4A 지원 (최대 100MB)
            </p>
          </div>
        </section>

        {/* 업로드 대기 파일 */}
        {pendingFiles.length > 0 && (
          <section className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-foreground">업로드 대기</h2>
                <p className="text-sm text-muted-foreground">{pendingFiles.length}개 파일 선택됨</p>
              </div>
            </div>

            {/* 파일 목록 */}
            <div className="space-y-3 mb-6">
              {pendingFiles.map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 bg-background rounded-lg border border-border">
                  <div className="flex items-center gap-3">
                    <FileAudio className="w-5 h-5 text-primary" />
                    <div>
                      <span className="text-sm font-medium text-foreground">{file.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        ({(file.size / 1024 / 1024).toFixed(1)} MB)
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFileRemove(file.id);
                    }}
                    className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            {/* 옵션 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  <Layers className="w-4 h-4 inline mr-1" />
                  생성 방식
                </label>
                <div className="relative">
                  <select
                    value={generationMode}
                    onChange={(e) => setGenerationMode(e.target.value as "default" | "natural")}
                    className="w-full appearance-none px-4 py-2.5 pr-10 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                  >
                    <option value="natural">자연 생성 (권장)</option>
                    <option value="default">기본 설정</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  <Film className="w-4 h-4 inline mr-1" />
                  영상 제목 (선택)
                </label>
                <input
                  type="text"
                  value={videoTitle}
                  onChange={(e) => setVideoTitle(e.target.value)}
                  placeholder="제목을 입력하세요 (비우면 파일명 사용)"
                  className="w-full px-4 py-2.5 border border-border rounded-lg bg-background text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  <Music className="w-4 h-4 inline mr-1" />
                  배경음악 볼륨: {Math.round(bgmVolume * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.01"
                  value={bgmVolume}
                  onChange={(e) => setBgmVolume(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-primary"
                />
              </div>
            </div>

            {/* 업로드 버튼 */}
            <button
              onClick={handleStartUpload}
              disabled={isUploading}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground font-medium rounded-lg transition-opacity"
            >
              <Play className="w-5 h-5" />
              {pendingFiles.length}개 파일 영상 생성 시작
            </button>
          </section>
        )}

        {/* 처리 중 파일 */}
        {processingFiles.length > 0 && (
          <section className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">
              처리 중 ({processingFiles.length}개)
            </h2>
            <div className="space-y-3">
              {processingFiles.map((file) => (
                <ProgressCard key={file.id} file={file} />
              ))}
            </div>
          </section>
        )}

        {/* 완료된 파일 */}
        {completedFiles.length > 0 && (
          <section className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">
              완료 ({completedFiles.length}개)
            </h2>
            <div className="space-y-3">
              {completedFiles.map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-3">
                    <FileAudio className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-medium text-foreground">{file.name}</span>
                    <span className="text-xs text-green-600">완료!</span>
                  </div>
                  <button
                    onClick={() => router.push("/videos")}
                    className="px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors"
                  >
                    영상 보기
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 실패한 파일 */}
        {failedFiles.length > 0 && (
          <section className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">
              실패 ({failedFiles.length}개)
            </h2>
            <div className="space-y-3">
              {failedFiles.map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-3">
                    <FileAudio className="w-5 h-5 text-red-600" />
                    <div>
                      <span className="text-sm font-medium text-foreground">{file.name}</span>
                      <p className="text-xs text-red-600">{file.error}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleFileRemove(file.id)}
                    className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </DashboardLayout>
  );
}
