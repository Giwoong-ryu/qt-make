"use client";

import { Video, Download, Trash2, Clock, CheckCircle, XCircle, Loader2, Edit3, Play } from "lucide-react";
import type { VideoItem } from "@/types";

interface VideoListProps {
  videos: VideoItem[];
  onDelete?: (videoId: string) => void;
  onEdit?: (videoId: string) => void;
  loading?: boolean;
}

export default function VideoList({ videos = [], onDelete, onEdit, loading }: VideoListProps) {
  // 방어: videos가 배열이 아닌 경우 빈 배열로 처리
  const videoList = Array.isArray(videos) ? videos : [];
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (seconds: number | null): string => {
    if (!seconds) return "-";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getStatusBadge = (status: VideoItem["status"]) => {
    switch (status) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded-full">
            <Clock className="w-3 h-3" />
            대기
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 text-xs rounded-full">
            <Loader2 className="w-3 h-3 animate-spin" />
            처리 중
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 text-xs rounded-full">
            <CheckCircle className="w-3 h-3" />
            완료
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 text-xs rounded-full">
            <XCircle className="w-3 h-3" />
            실패
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (videoList.length === 0) {
    return (
      <div className="text-center py-12">
        <Video className="w-12 h-12 mx-auto mb-4 text-gray-300" />
        <p className="text-gray-500">아직 생성된 영상이 없습니다</p>
        <p className="text-sm text-gray-400 mt-1">
          MP3 파일을 업로드하면 자동으로 영상이 생성됩니다
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {videoList.map((video) => (
        <div
          key={video.id}
          className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4"
        >
          <div className="flex items-start gap-4">
            {/* 썸네일 영역 */}
            <div className="flex-shrink-0 w-20 h-14 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
              <Video className="w-8 h-8 text-gray-400" />
            </div>

            {/* 정보 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-medium truncate">
                  {video.title || `영상 ${video.id.slice(0, 8)}`}
                </p>
                {getStatusBadge(video.status)}
              </div>

              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{formatDate(video.created_at)}</span>
                <span>{formatDuration(video.duration)}</span>
              </div>
            </div>

            {/* 액션 버튼 */}
            <div className="flex items-center gap-1">
              {/* 편집 버튼 (완료된 영상만) */}
              {video.status === "completed" && onEdit && (
                <button
                  onClick={() => onEdit(video.id)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="편집"
                >
                  <Edit3 className="w-4 h-4 text-gray-500 hover:text-blue-500" />
                </button>
              )}

              {/* 다운로드 버튼 */}
              {video.status === "completed" && video.video_file_path && (
                <a
                  href={video.video_file_path}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="다운로드"
                >
                  <Download className="w-4 h-4 text-blue-500" />
                </a>
              )}

              {/* 삭제 버튼 */}
              {onDelete && (
                <button
                  onClick={() => onDelete(video.id)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="삭제"
                >
                  <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
