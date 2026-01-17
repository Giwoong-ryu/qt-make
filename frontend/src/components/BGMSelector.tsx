"use client";

import { useState, useEffect, useRef } from "react";
import { Music, Play, Pause, Volume2, VolumeX, Check } from "lucide-react";
import type { BGM } from "@/types";
import { getBGMs } from "@/lib/api";

interface BGMSelectorProps {
  selectedBGM: string | null;
  onSelectionChange: (bgmId: string | null) => void;
  bgmVolume: number;
  onVolumeChange: (volume: number) => void;
  disabled?: boolean;
}

export default function BGMSelector({
  selectedBGM,
  onSelectionChange,
  bgmVolume,
  onVolumeChange,
  disabled = false,
}: BGMSelectorProps) {
  const [bgms, setBGMs] = useState<BGM[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [useDefaultBGM, setUseDefaultBGM] = useState(true);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // BGM 목록 로드
  useEffect(() => {
    async function loadBGMs() {
      setLoading(true);
      try {
        const data = await getBGMs();
        setBGMs(data);
      } catch (error) {
        console.error("Failed to load BGMs:", error);
        // 기본 BGM 설정 (데모용)
        setBGMs([
          {
            id: "bgm-peaceful",
            name: "평화로운 묵상",
            category: "peaceful",
            file_path: "",
            duration: 180,
          },
          {
            id: "bgm-hopeful",
            name: "소망의 빛",
            category: "hopeful",
            file_path: "",
            duration: 200,
          },
          {
            id: "bgm-grace",
            name: "은혜의 강",
            category: "graceful",
            file_path: "",
            duration: 240,
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    loadBGMs();
  }, []);

  // 오디오 재생/정지
  const togglePlay = (bgm: BGM) => {
    if (!bgm.preview_url && !bgm.file_path) return;

    if (playingId === bgm.id) {
      // 정지
      audioRef.current?.pause();
      setPlayingId(null);
    } else {
      // 재생
      if (audioRef.current) {
        audioRef.current.src = bgm.preview_url || bgm.file_path;
        audioRef.current.volume = bgmVolume;
        audioRef.current.play();
        setPlayingId(bgm.id);
      }
    }
  };

  // BGM 선택
  const selectBGM = (bgmId: string) => {
    if (disabled || useDefaultBGM) return;
    onSelectionChange(selectedBGM === bgmId ? null : bgmId);
  };

  // 기본값 모드 토글
  const toggleDefaultMode = () => {
    setUseDefaultBGM(!useDefaultBGM);
    if (!useDefaultBGM) {
      onSelectionChange(null);
    }
  };

  // 카테고리별 그룹화
  const categories = [...new Set(bgms.map((b) => b.category))];

  return (
    <div className="space-y-4">
      {/* 숨겨진 오디오 엘리먼트 */}
      <audio
        ref={audioRef}
        onEnded={() => setPlayingId(null)}
        className="hidden"
      />

      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          배경 음악 (BGM)
        </h3>
        <button
          onClick={toggleDefaultMode}
          disabled={disabled}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg transition-colors ${
            useDefaultBGM
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
          }`}
        >
          <Music className="w-3 h-3" />
          {useDefaultBGM ? "기본 BGM 사용" : "직접 선택"}
        </button>
      </div>

      {/* 볼륨 조절 */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onVolumeChange(bgmVolume === 0 ? 0.12 : 0)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          {bgmVolume === 0 ? (
            <VolumeX className="w-4 h-4 text-gray-400" />
          ) : (
            <Volume2 className="w-4 h-4 text-blue-500" />
          )}
        </button>
        <input
          type="range"
          min="0"
          max="0.5"
          step="0.01"
          value={bgmVolume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <span className="text-xs text-gray-500 w-10 text-right">
          {Math.round(bgmVolume * 100)}%
        </span>
      </div>

      {/* 기본 모드 안내 */}
      {useDefaultBGM && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-sm text-blue-700 dark:text-blue-300">
          <p>기본 BGM이 자동으로 적용됩니다.</p>
          <p className="text-xs mt-1 opacity-75">
            평화로운 묵상 분위기의 피아노 음악입니다.
          </p>
        </div>
      )}

      {/* BGM 선택 모드 */}
      {!useDefaultBGM && (
        <>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : bgms.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Music className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>사용 가능한 BGM이 없습니다</p>
            </div>
          ) : (
            <div className="space-y-3">
              {categories.map((category) => (
                <div key={category}>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase">
                    {category}
                  </p>
                  <div className="space-y-1">
                    {bgms
                      .filter((b) => b.category === category)
                      .map((bgm) => {
                        const isSelected = selectedBGM === bgm.id;
                        const isPlaying = playingId === bgm.id;

                        return (
                          <div
                            key={bgm.id}
                            className={`flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                              isSelected
                                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                                : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                            } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                            onClick={() => selectBGM(bgm.id)}
                          >
                            {/* 재생 버튼 */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                togglePlay(bgm);
                              }}
                              disabled={!bgm.preview_url && !bgm.file_path}
                              className={`p-2 rounded-full transition-colors ${
                                isPlaying
                                  ? "bg-blue-500 text-white"
                                  : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200"
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
                              <p className="text-sm font-medium truncate">
                                {bgm.name}
                              </p>
                              <p className="text-xs text-gray-400">
                                {Math.floor(bgm.duration / 60)}:
                                {(bgm.duration % 60).toString().padStart(2, "0")}
                              </p>
                            </div>

                            {/* 선택 표시 */}
                            {isSelected && (
                              <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                                <Check className="w-4 h-4 text-white" />
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
        </>
      )}
    </div>
  );
}
