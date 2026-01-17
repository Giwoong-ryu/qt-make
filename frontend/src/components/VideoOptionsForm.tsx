"use client";

import { useState } from "react";
import { Settings, ChevronDown, ChevronUp } from "lucide-react";
import ClipSelector from "./ClipSelector";
import BGMSelector from "./BGMSelector";

interface VideoOptionsFormProps {
  title: string;
  onTitleChange: (title: string) => void;
  selectedClips: string[];
  onClipsChange: (clips: string[]) => void;
  selectedBGM: string | null;
  onBGMChange: (bgmId: string | null) => void;
  bgmVolume: number;
  onBGMVolumeChange: (volume: number) => void;
  disabled?: boolean;
}

export default function VideoOptionsForm({
  title,
  onTitleChange,
  selectedClips,
  onClipsChange,
  selectedBGM,
  onBGMChange,
  bgmVolume,
  onBGMVolumeChange,
  disabled = false,
}: VideoOptionsFormProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      {/* 헤더 - 클릭하면 확장/축소 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-700 dark:text-gray-300">
            영상 옵션 설정
          </span>
          <span className="text-xs text-gray-400">
            (배경, BGM, 제목)
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {/* 확장된 내용 */}
      {isExpanded && (
        <div className="p-4 space-y-6 bg-white dark:bg-gray-800">
          {/* 제목 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              영상 제목
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="영상 제목을 입력하세요 (선택)"
              disabled={disabled}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <p className="mt-1 text-xs text-gray-400">
              비워두면 파일명이 제목으로 사용됩니다.
            </p>
          </div>

          {/* 구분선 */}
          <hr className="border-gray-200 dark:border-gray-700" />

          {/* 배경 클립 선택 */}
          <ClipSelector
            selectedClips={selectedClips}
            onSelectionChange={onClipsChange}
            disabled={disabled}
          />

          {/* 구분선 */}
          <hr className="border-gray-200 dark:border-gray-700" />

          {/* BGM 선택 */}
          <BGMSelector
            selectedBGM={selectedBGM}
            onSelectionChange={onBGMChange}
            bgmVolume={bgmVolume}
            onVolumeChange={onBGMVolumeChange}
            disabled={disabled}
          />
        </div>
      )}

      {/* 축소 상태에서 요약 표시 */}
      {!isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>
              배경: {selectedClips.length > 0 ? `${selectedClips.length}개 선택` : "자동"}
            </span>
            <span>
              BGM: {selectedBGM ? "선택됨" : "기본값"}
            </span>
            <span>
              볼륨: {Math.round(bgmVolume * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
