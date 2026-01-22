/**
 * API 응답 타입 정의
 */

// 영상 생성 요청 응답 (백엔드 main.py:171-179 매칭)
export interface CreateVideoResponse {
  status: "queued";
  task_id: string;
  church_id: string;
  pack_id: string;
  files_count: number;
  video_ids: string[];
  message: string;
}

// 태스크 상태 응답 (백엔드 main.py:195-220 매칭)
export interface TaskStatusResponse {
  task_id: string;
  status: "PENDING" | "PROCESSING" | "SUCCESS" | "FAILURE";
  progress: number;
  step?: string;  // SUCCESS/FAILURE시 없을 수 있음
  result?: VideoResult;
  error?: string;
}

// 영상 생성 결과
export interface VideoResult {
  video_id: string;
  video_url: string;
  srt_url: string;
  duration: number;
  clips_used: string[];
}

// 썸네일 레이아웃 타입 (thumbnail_editor에서 사용)
export interface ThumbnailLayout {
  text_boxes: Array<{
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    text: string;
    fontSize: number;
    fontWeight: string;
    color: string;
  }>;
  background_image_url?: string;
  intro_settings?: {
    useAsIntro: boolean;
    introDuration: number;
    useAsOutro: boolean;
    outroDuration: number;
  };
}

// 영상 목록 아이템 (백엔드 main.py:261 반환 필드 매칭)
export interface VideoItem {
  id: string;
  title: string;
  status: "pending" | "processing" | "completed" | "failed";
  duration: number | null;
  video_file_path: string | null;
  srt_file_path: string | null;
  thumbnail_url: string | null;
  created_at: string;
  completed_at: string | null;
  error_message?: string | null;  // 실패 시 에러 메시지
  thumbnail_layout?: ThumbnailLayout;  // 썸네일 레이아웃 (DB에 저장됨)
  clips_used?: string[];  // 사용된 클립 ID 목록
  bgm_id?: string | null;  // 사용된 BGM ID
  bgm_volume?: number;  // BGM 볼륨 (0.0 ~ 1.0)
}

// 업로드 파일 상태
export interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  status: "pending" | "uploading" | "processing" | "completed" | "failed";
  progress: number;
  step: string;
  taskId?: string;
  videoId?: string;
  videoUrl?: string;
  error?: string;
}

// 배경 클립 타입
export interface Clip {
  id: string;
  name: string;
  category: string;
  thumbnail_url: string;
  file_path: string;
  duration: number;
  pack_id: string;
}

// BGM 타입
export interface BGM {
  id: string;
  name: string;
  category: string;
  file_path: string;
  duration: number;
  preview_url?: string;
}

// 배경팩 타입
export interface ClipPack {
  id: string;
  name: string;
  description: string;
  thumbnail_url: string;
  clip_count: number;
  is_free: boolean;
}

// 영상 생성 옵션
export interface VideoOptions {
  title: string;
  clipIds?: string[];        // 선택된 배경 클립 (없으면 자동 선택)
  bgmId?: string;            // 선택된 BGM (없으면 기본값)
  bgmVolume?: number;        // BGM 볼륨 (0-1, 기본 0.12)
  generateThumbnail?: boolean; // 썸네일 생성 여부
  generationMode?: "default" | "natural" | "symbolic"; // 생성 방식
  subtitleLength?: "short" | "long"; // 자막 길이 (short: 8자, long: 16자)
}

// 자막 세그먼트 (편집용)
export interface SubtitleSegment {
  id: number;
  start: number;             // 시작 시간 (초)
  end: number;               // 끝 시간 (초)
  text: string;              // 자막 텍스트
}

// 영상 상세 정보 (확장)
export interface VideoDetail extends VideoItem {
  church_id: string;
  audio_file_path: string;
  srt_file_path: string | null;
  thumbnail_url: string | null;
  clips_used: string[];      // 사용된 클립 ID 목록
  bgm_id: string | null;
  bgm_volume: number;
  thumbnail_layout?: ThumbnailLayout;  // 썸네일 레이아웃
  subtitles?: SubtitleSegment[];
}

// 리소스 템플릿 (클립 + BGM 조합)
export interface ResourceTemplate {
  id: string;
  name: string;
  description?: string;
  clipIds: string[];         // 선택된 클립 ID 목록
  bgmId: string | null;      // 선택된 BGM ID
  bgmVolume: number;         // BGM 볼륨
  createdAt: string;
  updatedAt: string;
}
