"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Music, X } from "lucide-react";
import type { UploadFile } from "@/types";

interface FileUploaderProps {
  files: UploadFile[];
  onFilesAdd: (files: File[]) => void;
  onFileRemove: (fileId: string) => void;
  disabled?: boolean;
  maxFiles?: number;
}

export default function FileUploader({
  files,
  onFilesAdd,
  onFileRemove,
  disabled = false,
  maxFiles = 7,
}: FileUploaderProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      // 최대 파일 수 제한
      const remainingSlots = maxFiles - files.length;
      const filesToAdd = acceptedFiles.slice(0, remainingSlots);

      if (filesToAdd.length > 0) {
        onFilesAdd(filesToAdd);
      }
    },
    [files.length, maxFiles, onFilesAdd]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "audio/mpeg": [".mp3"],
      "audio/mp3": [".mp3"],
      "audio/mp4": [".m4a"],
      "audio/x-m4a": [".m4a"],
      "audio/wav": [".wav"],
    },
    disabled: disabled || files.length >= maxFiles,
    multiple: true,
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const pendingFiles = files.filter((f) => f.status === "pending");

  return (
    <div className="space-y-4">
      {/* 드롭존 */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 dark:border-gray-600 hover:border-blue-400"
          }
          ${disabled || files.length >= maxFiles
            ? "opacity-50 cursor-not-allowed"
            : ""
          }
        `}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />

        {isDragActive ? (
          <p className="text-blue-600 dark:text-blue-400 font-medium">
            파일을 여기에 놓으세요
          </p>
        ) : (
          <>
            <p className="text-gray-600 dark:text-gray-300 font-medium mb-1">
              MP3 파일을 드래그하거나 클릭하여 선택
            </p>
            <p className="text-xs text-gray-400 mb-1">
              MP3, M4A, WAV 지원
            </p>
            <p className="text-sm text-gray-400">
              최대 {maxFiles}개 파일, 각 10MB 이하
            </p>
          </>
        )}
      </div>

      {/* 대기 중인 파일 목록 */}
      {pendingFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
            업로드 대기 ({pendingFiles.length}개)
          </p>

          {pendingFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <Music className="w-5 h-5 text-blue-500 flex-shrink-0" />

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-gray-400">
                  {formatFileSize(file.size)}
                </p>
              </div>

              <button
                onClick={() => onFileRemove(file.id)}
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                disabled={disabled}
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
