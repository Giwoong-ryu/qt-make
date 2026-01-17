"use client";

import { Music, CheckCircle, XCircle, Loader2, Download } from "lucide-react";
import type { UploadFile } from "@/types";

interface ProgressCardProps {
  file: UploadFile;
}

export default function ProgressCard({ file }: ProgressCardProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusIcon = () => {
    switch (file.status) {
      case "uploading":
      case "processing":
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Music className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    switch (file.status) {
      case "uploading":
      case "processing":
        return "bg-blue-500";
      case "completed":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
      default:
        return "bg-gray-300";
    }
  };

  const getStatusText = () => {
    switch (file.status) {
      case "pending":
        return "대기 중";
      case "uploading":
        return "업로드 중...";
      case "processing":
        return file.step || "처리 중...";
      case "completed":
        return "완료!";
      case "failed":
        return file.error || "실패";
      default:
        return "";
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-start gap-3">
        {/* 아이콘 */}
        <div className="flex-shrink-0 mt-1">{getStatusIcon()}</div>

        {/* 내용 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <p className="text-sm font-medium truncate">{file.name}</p>
            <span className="text-xs text-gray-400 ml-2">
              {formatFileSize(file.size)}
            </span>
          </div>

          {/* 진행률 바 */}
          {(file.status === "uploading" || file.status === "processing") && (
            <div className="mb-2">
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getStatusColor()} transition-all duration-300`}
                  style={{ width: `${file.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* 상태 텍스트 */}
          <p
            className={`text-xs ${
              file.status === "failed"
                ? "text-red-500"
                : file.status === "completed"
                ? "text-green-500"
                : "text-gray-500"
            }`}
          >
            {getStatusText()}
            {(file.status === "uploading" || file.status === "processing") && (
              <span className="ml-1">({file.progress}%)</span>
            )}
          </p>

          {/* 다운로드 버튼 */}
          {file.status === "completed" && file.videoUrl && (
            <a
              href={file.videoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium rounded-lg transition-colors"
            >
              <Download className="w-3 h-3" />
              다운로드
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
