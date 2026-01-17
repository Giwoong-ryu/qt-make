"use client";

import { useState, useEffect } from "react";
import { Film, Check, Shuffle, ChevronDown } from "lucide-react";
import type { Clip, ClipPack } from "@/types";
import { getClips, getClipPacks } from "@/lib/api";

interface ClipSelectorProps {
  selectedClips: string[];
  onSelectionChange: (clipIds: string[]) => void;
  maxClips?: number;
  disabled?: boolean;
}

export default function ClipSelector({
  selectedClips,
  onSelectionChange,
  maxClips = 10,
  disabled = false,
}: ClipSelectorProps) {
  const [packs, setPacks] = useState<ClipPack[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedPack, setSelectedPack] = useState<string>("pack-free");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [useAutoSelect, setUseAutoSelect] = useState(true);

  // 팩 목록 로드
  useEffect(() => {
    async function loadPacks() {
      try {
        const data = await getClipPacks();
        setPacks(data);
      } catch (error) {
        console.error("Failed to load packs:", error);
        // 기본 팩 설정
        setPacks([{
          id: "pack-free",
          name: "무료 기본팩",
          description: "자연/도시 배경",
          thumbnail_url: "",
          clip_count: 20,
          is_free: true,
        }]);
      }
    }
    loadPacks();
  }, []);

  // 클립 목록 로드
  useEffect(() => {
    async function loadClips() {
      setLoading(true);
      try {
        const data = await getClips(selectedPack);
        setClips(data);
      } catch (error) {
        console.error("Failed to load clips:", error);
        setClips([]);
      } finally {
        setLoading(false);
      }
    }
    loadClips();
  }, [selectedPack]);

  // 카테고리 목록 추출
  const categories = ["all", ...new Set(clips.map((c) => c.category))];

  // 필터링된 클립
  const filteredClips =
    selectedCategory === "all"
      ? clips
      : clips.filter((c) => c.category === selectedCategory);

  // 클립 선택/해제
  const toggleClip = (clipId: string) => {
    if (disabled || useAutoSelect) return;

    const isSelected = selectedClips.includes(clipId);
    if (isSelected) {
      onSelectionChange(selectedClips.filter((id) => id !== clipId));
    } else if (selectedClips.length < maxClips) {
      onSelectionChange([...selectedClips, clipId]);
    }
  };

  // 자동 선택 모드 토글
  const toggleAutoSelect = () => {
    setUseAutoSelect(!useAutoSelect);
    if (!useAutoSelect) {
      // 자동 모드로 전환 시 선택 초기화
      onSelectionChange([]);
    }
  };

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          배경 영상 선택
        </h3>
        <button
          onClick={toggleAutoSelect}
          disabled={disabled}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg transition-colors ${
            useAutoSelect
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
          }`}
        >
          <Shuffle className="w-3 h-3" />
          {useAutoSelect ? "자동 선택 (기본)" : "수동 선택"}
        </button>
      </div>

      {/* 자동 선택 모드일 때 */}
      {useAutoSelect && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-sm text-blue-700 dark:text-blue-300">
          <p>배경 영상이 자동으로 선택됩니다.</p>
          <p className="text-xs mt-1 opacity-75">
            음성 길이에 맞춰 다양한 카테고리에서 배경이 선택됩니다.
          </p>
        </div>
      )}

      {/* 수동 선택 모드일 때 */}
      {!useAutoSelect && (
        <>
          {/* 팩 & 카테고리 필터 */}
          <div className="flex gap-3">
            {/* 팩 선택 */}
            <div className="relative">
              <select
                value={selectedPack}
                onChange={(e) => setSelectedPack(e.target.value)}
                disabled={disabled}
                className="appearance-none pl-3 pr-8 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {packs.map((pack) => (
                  <option key={pack.id} value={pack.id}>
                    {pack.name} ({pack.clip_count})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>

            {/* 카테고리 필터 */}
            <div className="relative">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                disabled={disabled}
                className="appearance-none pl-3 pr-8 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat === "all" ? "전체" : cat}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* 선택 현황 */}
          <div className="text-xs text-gray-500">
            {selectedClips.length} / {maxClips} 선택됨
          </div>

          {/* 클립 그리드 */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filteredClips.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Film className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>클립이 없습니다</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
              {filteredClips.map((clip) => {
                const isSelected = selectedClips.includes(clip.id);
                const selectionIndex = selectedClips.indexOf(clip.id);

                return (
                  <button
                    key={clip.id}
                    onClick={() => toggleClip(clip.id)}
                    disabled={disabled}
                    className={`relative aspect-video rounded-lg overflow-hidden border-2 transition-all ${
                      isSelected
                        ? "border-blue-500 ring-2 ring-blue-200"
                        : "border-transparent hover:border-gray-300"
                    } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    {/* 썸네일 */}
                    {clip.thumbnail_url ? (
                      <img
                        src={clip.thumbnail_url}
                        alt={clip.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
                        <Film className="w-6 h-6 text-gray-400" />
                      </div>
                    )}

                    {/* 선택 표시 */}
                    {isSelected && (
                      <div className="absolute top-1 right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                        {selectionIndex >= 0 ? (
                          <span className="text-xs text-white font-bold">
                            {selectionIndex + 1}
                          </span>
                        ) : (
                          <Check className="w-3 h-3 text-white" />
                        )}
                      </div>
                    )}

                    {/* 카테고리 뱃지 */}
                    <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-black/60 rounded text-[10px] text-white">
                      {clip.category}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
