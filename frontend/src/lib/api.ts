/**
 * Backend API 클라이언트
 */
import axios from "axios";
import type {
  CreateVideoResponse,
  TaskStatusResponse,
  VideoItem,
  VideoDetail,
  Clip,
  ClipPack,
  BGM,
  SubtitleSegment,
  VideoOptions,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "qt_access_token";

const api = axios.create({
  baseURL: API_URL,
  timeout: 300000, // 5분 (영상 생성은 오래 걸릴 수 있음)
});

// 요청 인터셉터: 토큰 자동 추가 + 디버그 로깅
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  // 디버그: FormData 요청 확인
  if (config.data instanceof FormData) {
    console.log("[API Debug] FormData request to:", config.url);
    console.log("[API Debug] Content-Type:", config.headers["Content-Type"]);
    // FormData 내용 출력
    for (const [key, value] of config.data.entries()) {
      if (value instanceof File) {
        console.log(`[API Debug] ${key}: File(${value.name}, ${value.size} bytes, ${value.type})`);
      } else {
        console.log(`[API Debug] ${key}: ${value}`);
      }
    }
  }

  return config;
});

// 응답 인터셉터: 401 에러 시 토큰 제거
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem(TOKEN_KEY);
        // 로그인 페이지로 리다이렉트 (선택적)
        if (window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

/**
 * 헬스 체크
 */
export async function healthCheck(): Promise<{ status: string }> {
  const response = await api.get("/health");
  return response.data;
}

/**
 * MP3 파일 업로드 + 영상 생성 시작
 */
export async function createVideo(
  file: File,
  churchId: string = "kkotdongsanchurch"
): Promise<CreateVideoResponse> {
  const formData = new FormData();
  formData.append("files", file);
  formData.append("church_id", churchId);

  const response = await api.post("/api/videos/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 60000, // 업로드는 60초
  });

  return response.data;
}

/**
 * 태스크 상태 조회 (Polling)
 */
export async function getTaskStatus(
  taskId: string
): Promise<TaskStatusResponse> {
  const response = await api.get(`/api/videos/status/${taskId}`);
  return response.data;
}

/**
 * 영상 목록 조회
 */
export async function getVideos(churchId: string): Promise<VideoItem[]> {
  const response = await api.get(`/api/videos`, {
    params: { church_id: churchId },
  });
  return response.data.videos || [];
}

/**
 * 영상 상세 조회
 */
export async function getVideo(videoId: string): Promise<VideoItem> {
  const response = await api.get(`/api/videos/${videoId}`);
  return response.data;
}

/**
 * 영상 삭제
 */
export async function deleteVideo(
  videoId: string,
  churchId: string = "kkotdongsanchurch"
): Promise<void> {
  await api.delete(`/api/videos/${videoId}`, {
    params: { church_id: churchId },
  });
}

// ============================================
// 통계 관련 API
// ============================================

export interface ChurchStats {
  church_id: string;
  this_week_videos: number;
  last_week_videos: number;
  total_videos: number;
  completed_videos: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  storage_used_percent: number;
  credits_remaining: number;
  credits_reset_date: string;
}

/**
 * 교회별 통계 조회
 */
export async function getStats(churchId: string): Promise<ChurchStats> {
  const response = await api.get(`/api/stats/${churchId}`);
  return response.data;
}

// ============================================
// 배경 클립 관련 API
// ============================================

/**
 * 배경팩 목록 조회
 */
export async function getClipPacks(): Promise<ClipPack[]> {
  const response = await api.get("/api/clips/packs");
  return response.data.packs || [];
}

/**
 * 특정 팩의 클립 목록 조회
 */
export async function getClips(packId: string = "pack-free"): Promise<Clip[]> {
  const response = await api.get(`/api/clips`, {
    params: { pack_id: packId },
  });
  return response.data.clips || [];
}

/**
 * 카테고리별 클립 조회
 */
export async function getClipsByCategory(
  packId: string,
  category: string
): Promise<Clip[]> {
  const response = await api.get(`/api/clips`, {
    params: { pack_id: packId, category },
  });
  return response.data.clips || [];
}

// ============================================
// BGM 관련 API
// ============================================

/**
 * BGM 목록 조회
 */
export async function getBGMs(): Promise<BGM[]> {
  const response = await api.get("/api/bgm");
  return response.data.bgms || [];
}

/**
 * 카테고리별 BGM 조회
 */
export async function getBGMsByCategory(category: string): Promise<BGM[]> {
  const response = await api.get("/api/bgm", {
    params: { category },
  });
  return response.data.bgms || [];
}

// ============================================
// 영상 상세/편집 관련 API
// ============================================

/**
 * 영상 상세 정보 조회 (자막 포함)
 */
export async function getVideoDetail(videoId: string): Promise<VideoDetail> {
  const response = await api.get(`/api/videos/${videoId}/detail`);
  return response.data;
}

/**
 * 영상 제목 수정
 */
export async function updateVideoTitle(
  videoId: string,
  title: string,
  churchId: string = "kkotdongsanchurch"
): Promise<VideoItem> {
  const response = await api.patch(`/api/videos/${videoId}`, {
    title,
    church_id: churchId,
  });
  return response.data;
}

/**
 * 자막 조회 (SRT 파싱)
 */
export async function getSubtitles(videoId: string): Promise<SubtitleSegment[]> {
  const response = await api.get(`/api/videos/${videoId}/subtitles`);
  return response.data.subtitles || [];
}

/**
 * 자막 수정
 */
export async function updateSubtitles(
  videoId: string,
  subtitles: SubtitleSegment[],
  churchId: string = "kkotdongsanchurch"
): Promise<{ success: boolean; srt_url: string }> {
  const response = await api.put(
    `/api/videos/${videoId}/subtitles?church_id=${churchId}`,
    subtitles
  );
  return response.data;
}

// ============================================
// 썸네일 관련 API
// ============================================

/**
 * 썸네일 생성 요청
 */
export async function generateThumbnail(
  videoId: string,
  timestamp: number = 5
): Promise<{ thumbnail_url: string }> {
  const response = await api.post(`/api/videos/${videoId}/thumbnail`, {
    timestamp,
  });
  return response.data;
}

/**
 * 커스텀 썸네일 업로드
 */
export async function uploadThumbnail(
  videoId: string,
  file: File
): Promise<{ thumbnail_url: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(`/api/videos/${videoId}/thumbnail/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

// ============================================
// 확장된 영상 생성 API (옵션 포함)
// ============================================

/**
 * 영상 생성 (옵션 포함)
 */
export async function createVideoWithOptions(
  file: File,
  options: VideoOptions,
  churchId: string = "kkotdongsanchurch"
): Promise<CreateVideoResponse> {
  const formData = new FormData();
  formData.append("files", file);
  formData.append("church_id", churchId);
  formData.append("title", options.title);

  if (options.clipIds && options.clipIds.length > 0) {
    formData.append("clip_ids", JSON.stringify(options.clipIds));
  }
  if (options.bgmId) {
    formData.append("bgm_id", options.bgmId);
  }
  if (options.bgmVolume !== undefined) {
    formData.append("bgm_volume", options.bgmVolume.toString());
  }
  if (options.generateThumbnail !== undefined) {
    formData.append("generate_thumbnail", options.generateThumbnail.toString());
  }
  if (options.generationMode) {
    formData.append("generation_mode", options.generationMode);
  }
  if (options.subtitleLength) {
    formData.append("subtitle_length", options.subtitleLength);
  }

  const response = await api.post("/api/videos/upload", formData, {
    // Content-Type을 직접 설정하지 않음 - Axios가 FormData에 맞게 boundary 포함하여 자동 설정
    timeout: 60000,
  });

  return response.data;
}

/**
 * 영상 재생성 (설정 변경 후)
 */
export async function regenerateVideo(
  videoId: string,
  options: Partial<VideoOptions> & { canvasImageData?: string },
  churchId: string = "kkotdongsanchurch"
): Promise<{ task_id: string }> {
  // canvasImageData를 snake_case로 변환 (백엔드 API 규격)
  const { canvasImageData, ...restOptions } = options;

  // 디버그: 전송되는 데이터 확인
  console.log("[API regenerateVideo] 호출됨:");
  console.log("  - videoId:", videoId);
  console.log("  - canvasImageData:", canvasImageData ? `${canvasImageData.length} bytes (${canvasImageData.substring(0, 50)}...)` : "undefined");
  console.log("  - churchId:", churchId);

  const requestBody = {
    ...restOptions,
    church_id: churchId,
    canvas_image_data: canvasImageData,  // Canvas에서 export한 이미지 (있으면 FFmpeg 생성 스킵)
  };

  console.log("[API regenerateVideo] Request body keys:", Object.keys(requestBody));
  console.log("[API regenerateVideo] canvas_image_data in body:", requestBody.canvas_image_data ? `${requestBody.canvas_image_data.length} bytes` : "undefined/null");

  const response = await api.post(`/api/videos/${videoId}/regenerate`, requestBody);
  return response.data;
}

// ============================================
// 썸네일 컨셉 관련 API
// ============================================

export interface ThumbnailCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  sort_order: number;
}

export interface ThumbnailTemplate {
  id: string;
  category_id: string;
  name: string;
  image_url: string;
  text_color: string;
  text_position: string;
  overlay_opacity: number;
  used_count: number;
}

/**
 * 썸네일 카테고리 목록 조회
 */
export async function getThumbnailCategories(): Promise<ThumbnailCategory[]> {
  const response = await api.get("/api/thumbnail/categories");
  return response.data.categories || [];
}

/**
 * 썸네일 템플릿 목록 조회
 */
export async function getThumbnailTemplates(
  categoryId?: string
): Promise<ThumbnailTemplate[]> {
  const response = await api.get("/api/thumbnail/templates", {
    params: categoryId ? { category_id: categoryId } : {},
  });
  return response.data.templates || [];
}

/**
 * 템플릿 상세 조회
 */
export async function getThumbnailTemplate(
  templateId: string
): Promise<ThumbnailTemplate> {
  const response = await api.get(`/api/thumbnail/templates/${templateId}`);
  return response.data;
}

/**
 * 템플릿 기반 썸네일 생성
 */
export async function generateThumbnailFromTemplate(
  videoId: string,
  templateId: string,
  title: string,
  churchId: string = "kkotdongsanchurch"
): Promise<{ thumbnail_url: string; template_id: string; title: string }> {
  const formData = new FormData();
  formData.append("template_id", templateId);
  formData.append("title", title);
  formData.append("church_id", churchId);

  const response = await api.post(
    `/api/videos/${videoId}/thumbnail/generate-from-template`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return response.data;
}

/**
 * QT 썸네일 생성 (드래그앤드롭 에디터 레이아웃 기반)
 */
export interface TextBoxLayout {
  id: string;
  text: string;
  x: number;  // 0-100 (퍼센트)
  y: number;  // 0-100 (퍼센트)
  fontSize: number;
  fontFamily: string;
  color: string;
  visible: boolean;
}

export interface QTThumbnailLayout {
  textBoxes: TextBoxLayout[];
  backgroundImageUrl?: string;
  introSettings?: {
    useAsIntro: boolean;
    introDuration: number;
    separateIntro: boolean;
    separateIntroImageUrl?: string;
  };
}

export async function generateQTThumbnail(
  layout: QTThumbnailLayout,
  options?: {
    overlayOpacity?: number;
    outputWidth?: number;
    outputHeight?: number;
    videoId?: string;  // 썸네일을 비디오에 저장할 경우
  }
): Promise<{ thumbnail_url: string; saved_to_video?: boolean }> {
  const response = await api.post('/api/thumbnail/generate-qt', {
    background_image_url: layout.backgroundImageUrl,
    text_boxes: layout.textBoxes.filter(box => box.visible).map(box => ({
      id: box.id,
      text: box.text,
      x: box.x,
      y: box.y,
      fontSize: box.fontSize,
      fontFamily: box.fontFamily,
      color: box.color,
      visible: box.visible,
    })),
    overlay_opacity: options?.overlayOpacity ?? 0.3,
    output_width: options?.outputWidth ?? 1920,
    output_height: options?.outputHeight ?? 1080,
    video_id: options?.videoId,
  });
  return response.data;
}

/**
 * 썸네일 레이아웃 저장 (비디오에 연결)
 */
export async function saveThumbnailLayout(
  videoId: string,
  layout: QTThumbnailLayout,
  churchId: string = "kkotdongsanchurch"
): Promise<{ success: boolean; video_id: string; layout: object }> {
  const response = await api.put(`/api/videos/${videoId}/thumbnail-layout`, {
    church_id: churchId,
    text_boxes: layout.textBoxes.map(box => ({
      id: box.id,
      text: box.text,
      x: box.x,
      y: box.y,
      fontSize: box.fontSize,
      fontFamily: box.fontFamily,
      color: box.color,
      visible: box.visible,
    })),
    background_image_url: layout.backgroundImageUrl,
    intro_settings: layout.introSettings,
  });
  return response.data;
}

/**
 * 저장된 썸네일 레이아웃 조회
 */
export async function getThumbnailLayout(
  videoId: string
): Promise<{ video_id: string; layout: QTThumbnailLayout | null }> {
  const response = await api.get(`/api/videos/${videoId}/thumbnail-layout`);
  return response.data;
}

/**
 * Canvas에서 직접 생성한 썸네일 이미지 저장
 * (Canvas toDataURL로 생성한 base64 이미지를 서버에 저장)
 */
export async function saveCanvasThumbnail(
  videoId: string,
  canvasImageData: string  // data:image/jpeg;base64,... 형식
): Promise<{ thumbnail_url: string; video_id: string }> {
  const response = await api.post(`/api/videos/${videoId}/thumbnail/save-canvas`, {
    image_data: canvasImageData,
  });
  return response.data;
}

// ============================================
// 자동 치환 사전 API
// ============================================

export interface ReplacementEntry {
  id: string;
  church_id: string;
  original: string;
  replacement: string;
  created_at: string;
  updated_at: string;
  use_count: number;
}

/**
 * 치환 사전 목록 조회
 */
export async function getReplacementDictionary(
  churchId: string
): Promise<ReplacementEntry[]> {
  const response = await api.get(`/api/dictionary/${churchId}`);
  return response.data.entries || [];
}

/**
 * 치환 사전에 항목 추가 (자동 감지된 수정 저장)
 */
export async function addReplacementEntry(
  churchId: string,
  original: string,
  replacement: string
): Promise<ReplacementEntry> {
  const response = await api.post(`/api/dictionary/${churchId}`, {
    original,
    replacement,
  });
  return response.data;
}

/**
 * 치환 사전에 여러 항목 일괄 추가 (자막 수정 시 호출)
 */
export async function addReplacementEntries(
  churchId: string,
  entries: Array<{ original: string; replacement: string }>
): Promise<{ added: number; updated: number }> {
  const response = await api.post(`/api/dictionary/${churchId}/batch`, {
    entries,
  });
  return response.data;
}

/**
 * 치환 사전 항목 삭제
 */
export async function deleteReplacementEntry(
  churchId: string,
  entryId: string
): Promise<void> {
  await api.delete(`/api/dictionary/${churchId}/${entryId}`);
}

/**
 * 치환 사전 전체 삭제
 */
export async function clearReplacementDictionary(
  churchId: string
): Promise<void> {
  await api.delete(`/api/dictionary/${churchId}`);
}
