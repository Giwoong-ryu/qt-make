"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Download,
  CheckCircle,
  Clock,
  AlertCircle,
  Trash2,
  Search,
  Filter,
  X,
} from "lucide-react";
import { DashboardLayout, VideoEditModal } from "@/components";
import { getVideos, deleteVideo } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { VideoItem } from "@/types";

export default function VideosPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();

  // 인증 체크
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const churchId = user?.church_id || "demo-church";

  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [editingVideoId, setEditingVideoId] = useState<string | null>(null);
  const [selectedVideoIds, setSelectedVideoIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // 영상 목록 로드
  const loadVideos = useCallback(async () => {
    if (!churchId) return;
    try {
      setLoadingVideos(true);
      const videosData = await getVideos(churchId);
      setVideos(videosData);
    } catch (error) {
      console.error("Failed to load videos:", error);
    } finally {
      setLoadingVideos(false);
    }
  }, [churchId]);

  useEffect(() => {
    if (isAuthenticated) {
      loadVideos();
    }
  }, [loadVideos, isAuthenticated]);

  // 영상 삭제 (단일)
  const handleDeleteVideo = useCallback(async (videoId: string) => {
    if (!confirm("정말 삭제하시겠습니까?")) return;
    try {
      await deleteVideo(videoId, churchId);
      loadVideos();
    } catch (error) {
      console.error("Delete error:", error);
    }
  }, [loadVideos, churchId]);

  // 체크박스 토글
  const toggleVideoSelection = useCallback((videoId: string) => {
    setSelectedVideoIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(videoId)) {
        newSet.delete(videoId);
      } else {
        newSet.add(videoId);
      }
      return newSet;
    });
  }, []);

  // 필터링된 영상 목록
  const filteredVideos = videos.filter((video) => {
    const matchesSearch = video.title?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
    const matchesStatus = statusFilter === "all" || video.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // 전체 선택/해제
  const toggleSelectAll = useCallback(() => {
    if (selectedVideoIds.size === filteredVideos.length) {
      setSelectedVideoIds(new Set());
    } else {
      setSelectedVideoIds(new Set(filteredVideos.map((v) => v.id)));
    }
  }, [filteredVideos, selectedVideoIds.size]);

  // 일괄 삭제
  const handleBatchDelete = useCallback(async () => {
    if (selectedVideoIds.size === 0) {
      alert("삭제할 영상을 선택해주세요.");
      return;
    }

    if (!confirm(`선택한 ${selectedVideoIds.size}개의 영상을 삭제하시겠습니까?`)) {
      return;
    }

    setIsDeleting(true);
    try {
      // API 호출
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/videos/delete-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_ids: Array.from(selectedVideoIds),
          church_id: churchId,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "삭제 실패");
      }

      const result = await response.json();
      alert(`${result.deleted_count}개 영상이 삭제되었습니다.`);

      setSelectedVideoIds(new Set());
      loadVideos();
    } catch (error) {
      console.error("Batch delete error:", error);
      alert("일괄 삭제 중 오류가 발생했습니다.");
    } finally {
      setIsDeleting(false);
    }
  }, [selectedVideoIds, churchId, loadVideos]);

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
            <h1 className="text-2xl font-bold text-foreground">내 영상</h1>
            <p className="text-sm text-muted-foreground mt-1">
              홈 / 내 영상
            </p>
          </div>
          <button
            onClick={loadVideos}
            disabled={loadingVideos}
            className="flex items-center gap-2 px-4 py-2.5 bg-card border border-border text-foreground rounded-lg hover:bg-accent transition-colors font-medium"
          >
            <RefreshCw className={`w-4 h-4 ${loadingVideos ? "animate-spin" : ""}`} />
            새로고침
          </button>
        </div>
      </header>

      <div className="p-8 space-y-6">
        {/* 검색 및 필터 */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="영상 제목으로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-border rounded-lg bg-card text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2.5 border border-border rounded-lg bg-card text-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
            >
              <option value="all">전체 상태</option>
              <option value="completed">완료</option>
              <option value="processing">처리중</option>
              <option value="failed">실패</option>
            </select>
          </div>
        </div>

        {/* 영상 목록 */}
        <section className="bg-card rounded-xl border border-border">
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">영상 목록</h2>
                <p className="text-sm text-muted-foreground">
                  총 {filteredVideos.length}개의 영상
                </p>
              </div>
            </div>
          </div>

          {/* 일괄 삭제 버튼 */}
          {selectedVideoIds.size > 0 && (
            <div className="mb-4 flex items-center justify-between bg-accent/50 border border-border rounded-lg px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">
                  {selectedVideoIds.size}개 선택됨
                </span>
                <button
                  onClick={() => setSelectedVideoIds(new Set())}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  <X className="w-3 h-3" />
                  선택 해제
                </button>
              </div>
              <button
                onClick={handleBatchDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                {isDeleting ? "삭제 중..." : "선택 항목 삭제"}
              </button>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-6 py-4 w-12">
                    <input
                      type="checkbox"
                      checked={filteredVideos.length > 0 && selectedVideoIds.size === filteredVideos.length}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary"
                    />
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">상태</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">썸네일</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">파일명</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">생성일</th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">재생시간</th>
                  <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-6 py-4">작업</th>
                </tr>
              </thead>
              <tbody>
                {loadingVideos ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-muted-foreground">로딩 중...</td>
                  </tr>
                ) : filteredVideos.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-muted-foreground">
                      {searchQuery || statusFilter !== "all" ? "검색 결과가 없습니다." : "아직 생성된 영상이 없습니다."}
                    </td>
                  </tr>
                ) : (
                  filteredVideos.map((video) => (
                    <tr key={video.id} className="border-b border-border hover:bg-accent/50 transition-colors">
                      <td className="px-6 py-4">
                        <input
                          type="checkbox"
                          checked={selectedVideoIds.has(video.id)}
                          onChange={() => toggleVideoSelection(video.id)}
                          className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                            video.status === "completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                            video.status === "processing" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                            video.status === "failed" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 cursor-pointer" :
                            "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
                          }`}
                          title={video.status === "failed" && video.error_message ? `실패 원인: ${video.error_message}` : undefined}
                          onClick={video.status === "failed" && video.error_message ? () => {
                            alert(`영상 생성 실패\n\n원인: ${video.error_message}\n\n문제가 지속되면 관리자에게 문의해주세요.`);
                          } : undefined}
                        >
                          {video.status === "completed" ? <CheckCircle className="w-3 h-3" /> :
                           video.status === "processing" ? <Clock className="w-3 h-3" /> :
                           video.status === "failed" ? <AlertCircle className="w-3 h-3" /> : null}
                          {video.status === "completed" ? "완료" :
                           video.status === "processing" ? "처리중" :
                           video.status === "failed" ? "실패 (클릭)" : "대기중"}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {video.thumbnail_url ? (
                          <div className="relative w-20 h-12 rounded overflow-hidden bg-muted">
                            <img
                              src={video.thumbnail_url}
                              alt={video.title || "썸네일"}
                              className="w-full h-full object-cover"
                            />
                          </div>
                        ) : (
                          <div className="w-20 h-12 rounded bg-muted flex items-center justify-center">
                            <span className="text-xs text-muted-foreground">없음</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm font-medium text-foreground">{video.title || "제목 없음"}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-muted-foreground">
                          {new Date(video.created_at).toLocaleDateString("ko-KR", { year: "numeric", month: "short", day: "numeric" })}
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
                            onClick={() => setEditingVideoId(video.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-border text-foreground text-sm font-medium rounded-lg hover:bg-accent transition-colors"
                          >
                            수정
                          </button>
                          <button
                            onClick={() => handleDeleteVideo(video.id)}
                            className="inline-flex items-center gap-1.5 p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
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
