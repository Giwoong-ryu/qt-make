"""
배경 영상 검색 서비스 (Pexels API + Gemini Vision)

감정 데이터 기반 Pexels 검색 및 Gemini Vision 안전성 검증
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Tuple

import google.generativeai as genai
import requests

from app.config import get_settings
from app.services.mood_analyzer import MoodData

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PexelsVideo:
    """Pexels 영상 정보"""
    id: int
    url: str
    image_url: str  # 썸네일
    duration: int   # 초 단위
    width: int
    height: int
    file_path: str  # 다운로드 URL
    quality_score: int = 0
    vision_verified: bool = False
    vision_score: Optional['VisionScore'] = None  # v1.5: 상세 점수


@dataclass
class VisionScore:
    """
    Gemini Vision 점수화 결과 (v1.5)
    
    기존 accept/reject 이진 판단에서 0-100 점수화로 개선
    """
    # Hard Reject 기준 (하나라도 True면 즉시 탈락)
    has_face_closeup: bool = False
    has_cityscape: bool = False
    has_logo_text: bool = False
    has_modern_objects: bool = False
    has_revealing_content: bool = False
    
    # Soft Scores (0-100, 높을수록 좋음)
    semantic_match: int = 50      # 자막 매칭 점수
    biblical_vibe: int = 50       # 성경 분위기 점수
    visual_quality: int = 50      # 시각 품질 점수
    
    # Modernness (0-100, 낮을수록 좋음 - 성경 시대에 가까움)
    modernness: int = 50
    
    # 최종 판정
    hard_reject: bool = False
    final_score: int = 0
    reject_reason: str = ""
    scene_tags: List[str] = None
    mood_tags: List[str] = None
    
    def __post_init__(self):
        if self.scene_tags is None:
            self.scene_tags = []
        if self.mood_tags is None:
            self.mood_tags = []
        
        # Hard Reject 계산
        if any([self.has_face_closeup, self.has_cityscape, 
                self.has_logo_text, self.has_modern_objects,
                self.has_revealing_content]):
            self.hard_reject = True
            self.final_score = 0
        else:
            # Soft Score 계산: semantic(40%) + biblical(30%) + quality(20%) - modernness(10%)
            self.final_score = int(
                self.semantic_match * 0.4 +
                self.biblical_vibe * 0.3 +
                self.visual_quality * 0.2 -
                self.modernness * 0.1
            )
            self.final_score = max(0, min(100, self.final_score))


class PexelsVideoSearch:
    """Pexels 영상 검색 및 Gemini Vision 검증"""

    BASE_URL = "https://api.pexels.com/videos/search"

    # 3단계 검색 우선순위 (Runway AI Prompt Engineering)
    PRIORITY_SCORES = {
        1: 40,  # subject + emotion + color_tone
        2: 25,  # subject + motion
        3: 10   # subject only
    }

    # 전략별 검색 키워드 (빈도 기반 감정 분석 결과 연동)
    # Best Practice: Pexels는 구체적 키워드일수록 정확 (broad keywords = 부정확)
    # Reference: https://www.pexels.com/api/documentation/
    # v1.5: symbolic 모드 추가, 네거티브 키워드 강화 (2026-01-22)
    STRATEGY_KEYWORDS = {
        "human": {
            "primary": [
                "silhouette sunset back view walking",      # "person" 제거 (얼굴 클로즈업 방지)
                "hooded figure shadow dark moody",          # 구체적 시각 요소 강조
                "back view kneeling prayer",                # 뒷모습 명시 (church 제거)
                "praying hands blur contemplation"          # 신체 부위만 (얼굴 제외)
            ],
            "fallback": "silhouette shadow back view",
            "negative": ["city", "stage", "concert", "microphone", "audience", "office"]
        },
        "nature_bright": {
            "primary": [
                "sunrise golden hour mountain rays",        # 명확한 장면 묘사
                "light breaking through clouds hope",       # 시각적 요소 구체화
                "morning sunlight forest fog ethereal",     # 분위기 키워드 추가
                "golden rays sunset landscape peaceful"     # 복합 감정 표현
            ],
            "fallback": "sunrise golden light nature",
            "negative": ["city", "building", "car", "highway", "road", "vehicle"]
        },
        "nature_calm": {
            "primary": [
                "calm mountain lake reflection serene",     # 구체적 장소 + 감정
                "peaceful water surface quiet minimal",     # 미니멀 강조 (사람 제외)
                "serene forest trees soft focus tranquil",  # 부드러운 시각 강조
                "gentle ocean waves zen meditation"         # 명상 컨텍스트 명시
            ],
            "fallback": "calm nature minimal peaceful",
            "negative": ["city", "building", "car", "highway", "road", "people"]
        },
        # NEW: symbolic 모드 - 기도손, 성경책, 십자가 실루엣 (v1.5)
        "symbolic": {
            "primary": [
                "praying hands closeup candlelight warm",   # 기도 손 클로즈업
                "open bible soft light wooden table",       # 성경책
                "cross silhouette sunrise hope",            # 십자가 실루엣
                "worship hands raised silhouette sunset"    # 찬양 손
            ],
            "fallback": "prayer hands bible cross candle",
            "negative": ["city", "office", "stage", "concert", "logo", "fashion", "model"]
        }
    }
    
    # 공통 네거티브 키워드 (모든 모드에 적용) - "christian" 제거됨
    # v1.6: timelapse/hyperlapse 필터링 추가 (2026-01-23) - 자연경관 모드에서 빠른 영상 제외
    # v1.8: 비기독교 종교 콘텐츠 필터링 추가 (2026-01-23) - 코란/이슬람/힌두/불교 차단
    # v1.9: 가톨릭/정교회 콘텐츠 필터링 추가 (2026-01-23) - 개신교 앱이므로 성호긋기/마리아/묵주 차단
    GLOBAL_NEGATIVE = [
        "logo", "text", "watermark", "brand", "smartphone", "laptop",
        "timelapse", "time-lapse", "time lapse", "hyperlapse", "fast motion",
        "sped up", "speed up", "accelerated", "quick motion",
        # Catholic/Orthodox (Protestant app - reject Catholic imagery)
        "catholic", "rosary", "virgin mary", "madonna", "crucifix", "confession",
        "orthodox", "icon", "saint statue", "holy water",
        # Non-Christian religious content (CRITICAL)
        "quran", "koran", "mosque", "islam", "muslim", "mecca", "kaaba", "ramadan",
        "buddha", "buddhist", "buddhism", "temple", "pagoda", "monk",
        "hindu", "hinduism", "shiva", "vishnu", "ganesha", "krishna", "om symbol",
        "jewish", "judaism", "menorah", "torah", "synagogue", "rabbi"
    ]

    def __init__(self, pexels_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        초기화

        Args:
            pexels_api_key: Pexels API 키
            gemini_api_key: Gemini API 키
        """
        self.pexels_key = pexels_api_key or settings.PEXELS_API_KEY
        self.gemini_key = gemini_api_key or settings.GEMINI_API_KEY

        if not self.pexels_key:
            raise ValueError("PEXELS_API_KEY is required")
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is required")

        genai.configure(api_key=self.gemini_key)

        # Gemini Vision 모델 (flash: 정확도 향상, 비용 차이 미미)
        self.vision_model = genai.GenerativeModel(
            'gemini-2.5-flash'
        )

    def search_by_mood(
        self,
        mood: Optional[MoodData],
        duration_needed: int,
        max_results: int = 5,
        strategy: Optional[str] = None
    ) -> List[PexelsVideo]:
        """
        감정 데이터 기반 영상 검색 + Gemini Vision 검증

        Args:
            mood: 감정 데이터 (strategy 사용 시 None 가능)
            duration_needed: 필요한 영상 길이 (초)
            max_results: 반환할 영상 개수
            strategy: 영상 전략 ("human" / "nature_bright" / "nature_calm")
                     None이면 mood 기반 검색

        Returns:
            검증된 PexelsVideo 리스트
        """
        # 1. Pexels 검색 (후보 20개)
        candidates = self._search_pexels(mood, per_page=20, strategy=strategy)

        if not candidates:
            logger.warning("No Pexels results found")
            return []

        # 2. Gemini Vision으로 썸네일 검증
        verified = []
        for video in candidates:
            if len(verified) >= max_results:
                break

            is_safe = self._verify_with_gemini_vision(video.image_url)
            if is_safe:
                video.vision_verified = True
                verified.append(video)

        # 3. 품질 점수 계산
        for video in verified:
            video.quality_score = self._calculate_quality_score(video, mood)

        # 4. 품질 점수 기준 정렬
        verified.sort(key=lambda v: v.quality_score, reverse=True)

        # 로깅 (mood 또는 strategy 정보)
        search_info = f"{mood.emotion}/{mood.subject}" if mood else f"strategy={strategy}"
        logger.info(
            f"Verified {len(verified)}/{len(candidates)} videos "
            f"({search_info})"
        )
        return verified

    # v1.7: 3단계 Fallback 시스템 (2026-01-23)
    MAX_CHECKS_PER_QUERY = 50  # 50개 검증했는데도 안 나오면 다음 시도

    def search_by_visual_description(
        self,
        visual_query: str,
        duration_needed: int,
        max_results: int = 5,
        exclude_ids: set = None
    ) -> List[PexelsVideo]:
        """
        Visual Description 기반 영상 검색 (Stage 3)

        v1.7: 3단계 Fallback 시스템 추가 (2026-01-23)
        - 1차 시도: 원본 쿼리 (2페이지, 40개)
        - 2차 시도: 단순화 쿼리 (첫 3개 키워드, 3페이지, 60개)
        - 3차 시도: Fallback 쿼리 (모드별 안전한 키워드, 5페이지, 100개)

        이 메서드는 LLM 감독이 생성한 시각적 묘사를 받아서
        Pexels에서 영상을 검색합니다.

        Args:
            visual_query: LLM이 생성한 영어 시각 묘사
                         예: "A woman looking anxious and jealous in an ancient palace,
                              shadowy lighting, tense atmosphere, cinematic style"
            duration_needed: 필요한 영상 길이 (초)
            max_results: 반환할 영상 개수
            exclude_ids: 제외할 영상 ID set (중복 방지용)

        Returns:
            검증된 PexelsVideo 리스트
        """
        exclude_ids = exclude_ids or set()
        logger.info(f"[PexelsSearch] Visual query: {visual_query} (excluding {len(exclude_ids)} IDs)")

        # 3단계 Fallback 시스템
        for attempt in range(1, 4):
            if attempt == 1:
                # 1차 시도: 원본 쿼리
                query_to_use = self._apply_tone_adjustment(visual_query)
                max_pages = 2
                logger.info(f"[PexelsSearch] Attempt 1/3 (Original query)")
            elif attempt == 2:
                # 2차 시도: 단순화 (첫 3개 키워드만)
                simplified_query = " ".join(visual_query.split()[:3])
                query_to_use = self._apply_tone_adjustment(simplified_query)
                max_pages = 3
                logger.info(f"[PexelsSearch] Attempt 2/3 (Simplified: \"{simplified_query}\")")
            else:
                # 3차 시도: Fallback 쿼리 (모드별 안전한 키워드)
                fallback_query = self._get_fallback_query()
                query_to_use = self._apply_tone_adjustment(fallback_query)
                max_pages = 5
                logger.info(f"[PexelsSearch] Attempt 3/3 (Fallback: \"{fallback_query}\")")

            # 내부 검증 로직 실행
            verified = self._search_with_verification(
                query_to_use, exclude_ids, max_results, max_pages
            )

            # 결과 판단
            if len(verified) >= max_results:
                logger.info(f"[PexelsSearch] Success on attempt {attempt}: {len(verified)} videos found")
                return verified[:max_results]
            elif len(verified) > 0:
                # 부분 성공 (1-2개라도 반환) - 다음 시도 안 함
                logger.info(f"[PexelsSearch] Partial success on attempt {attempt}: {len(verified)}/{max_results} videos (returning anyway)")
                return verified
            else:
                logger.warning(f"[PexelsSearch] Attempt {attempt} failed: 0/{max_results} videos")

        # 3번 다 실패 → 빈 배열 (영상 생성 실패 처리)
        logger.error(f"[PexelsSearch] All 3 attempts failed for query: {visual_query}")
        return []

    def _get_fallback_query(self) -> str:
        """
        모드별 Fallback 기본 쿼리

        Returns:
            모드에 맞는 안전한 검색 키워드
        """
        # 현재 모드를 어떻게 판단할지? → generation_mode가 없으므로 STRATEGY_KEYWORDS의 fallback 사용
        # 임시로 "symbolic" 모드를 기본으로 사용 (기도손/성경/십자가)
        # TODO: 추후 generation_mode 파라미터 추가하여 정확한 모드 사용

        # 현재는 symbolic 모드 fallback 사용
        return self.STRATEGY_KEYWORDS["symbolic"]["fallback"]

    def _apply_tone_adjustment(self, query: str) -> str:
        """
        QT 묵상 영상 톤 조정 적용

        Args:
            query: 원본 검색 쿼리

        Returns:
            톤 조정된 쿼리
        """
        # QT 묵상 영상 톤 조정: 어두움 70% / 밝음 30%
        # 밝은 키워드 제거 및 어두운 톤 키워드 추가
        dark_tone_keywords = [
            "dark", "moody", "shadowy", "dim light", "soft light",
            "contemplative", "solemn", "reverent", "subdued"
        ]

        # 밝은 키워드 탐지 (제거 대상)
        bright_keywords = [
            "bright", "sunny", "golden hour", "sunrise", "sunset",
            "warm light", "cheerful", "vibrant"
        ]

        # 쿼리에서 밝은 키워드 제거
        modified_query = query
        for bright_word in bright_keywords:
            modified_query = modified_query.replace(bright_word, "")

        # 어두운 톤 키워드 추가 (70% 확률)
        import random
        if random.random() < 0.7:  # 70% 확률로 어두운 톤 강제
            dark_keyword = random.choice(dark_tone_keywords)
            modified_query = f"{modified_query} {dark_keyword}"

        # v1.6: timelapse 방지 - "slow" 또는 "real time" 키워드 추가
        # Pexels에서 자연 영상 검색 시 timelapse가 상위 노출되는 문제 해결
        anti_timelapse_keywords = ["slow", "gentle", "peaceful", "still", "calm"]
        anti_timelapse = random.choice(anti_timelapse_keywords)
        modified_query = f"{modified_query} {anti_timelapse}"

        logger.info(f"[PexelsSearch] Modified query (dark tone + anti-timelapse): {modified_query}")
        return modified_query

    def _search_with_verification(
        self,
        query: str,
        exclude_ids: set,
        max_results: int,
        max_pages: int
    ) -> List[PexelsVideo]:
        """
        Pexels 검색 + Gemini Vision 검증 (내부 헬퍼)

        Args:
            query: 검색 쿼리 (톤 조정 완료된 상태)
            exclude_ids: 제외할 영상 ID set
            max_results: 반환할 영상 개수
            max_pages: 검색할 최대 페이지 수

        Returns:
            검증된 PexelsVideo 리스트
        """
        # 1. Pexels 검색
        all_videos_data = []
        try:
            for page in range(1, max_pages + 1):
                response = requests.get(
                    self.BASE_URL,
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": query,
                        "per_page": 20,
                        "page": page,
                        "orientation": "landscape"
                    },
                    timeout=10
                )

                if response.status_code != 200:
                    logger.error(f"Pexels API error: {response.status_code}")
                    break

                data = response.json()
                page_videos = data.get("videos", [])
                all_videos_data.extend(page_videos)

                if len(page_videos) < 20:  # 더 이상 결과 없음
                    break

            videos_data = all_videos_data

            if not videos_data:
                logger.warning("No videos found for query")
                return []

            # PexelsVideo 객체 생성
            candidates = []
            for video_data in videos_data:
                # HD 품질 파일 URL 찾기
                video_files = video_data.get("video_files", [])
                hd_file = None

                for vf in video_files:
                    if vf.get("quality") == "hd" and vf.get("width") == 1920:
                        hd_file = vf
                        break

                if not hd_file:
                    # HD 없으면 첫 번째 파일 사용
                    hd_file = video_files[0] if video_files else None

                if not hd_file:
                    continue

                # 이미 사용된 영상 제외
                video_id = video_data["id"]
                if video_id in exclude_ids:
                    continue

                # duration 필터링 (3초 이상만 - VideoCompositor가 반복 처리)
                video_duration = video_data.get("duration", 0)
                if video_duration < 3:
                    continue

                pexels_video = PexelsVideo(
                    id=video_data["id"],
                    url=video_data.get("url", ""),
                    image_url=video_data.get("image", ""),
                    duration=video_duration,
                    width=hd_file.get("width", 1920),
                    height=hd_file.get("height", 1080),
                    file_path=hd_file.get("link", "")
                )
                candidates.append(pexels_video)

        except Exception as e:
            logger.error(f"Pexels search failed: {e}")
            return []

        # 2. Gemini Vision 병렬 검증 (5개씩 배치, 3개 통과 시 조기 중단)
        verified = []
        blocked_count = 0
        checked_count = 0
        TARGET_PASS = 3  # 목표 통과 개수
        BATCH_SIZE = 5   # 병렬 처리 배치 크기

        def verify_single(video: PexelsVideo) -> Tuple[PexelsVideo, bool]:
            """단일 비디오 검증 (병렬 처리용)"""
            is_safe = self._verify_with_gemini_vision(video.image_url)
            return (video, is_safe)

        # 배치별 병렬 처리 (MAX_CHECKS_PER_QUERY 제한 적용)
        for batch_start in range(0, min(len(candidates), self.MAX_CHECKS_PER_QUERY), BATCH_SIZE):
            # 이미 충분히 통과했으면 조기 중단
            if len(verified) >= TARGET_PASS:
                logger.info(f"[PexelsSearch] Early stop: {len(verified)} passed (target: {TARGET_PASS})")
                break

            batch = candidates[batch_start:batch_start + BATCH_SIZE]
            logger.info(f"[PexelsSearch] Batch {batch_start//BATCH_SIZE + 1}: checking {len(batch)} videos (verified: {len(verified)}/{TARGET_PASS})")

            # 병렬 검증
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                futures = {executor.submit(verify_single, video): video for video in batch}

                for future in as_completed(futures):
                    checked_count += 1
                    video, is_safe = future.result()

                    if is_safe:
                        video.vision_verified = True
                        video.quality_score = 50
                        verified.append(video)
                        logger.info(f"[PexelsSearch] ✅ ACCEPT: ID={video.id}")
                    else:
                        blocked_count += 1
                        logger.info(f"[PexelsSearch] ❌ REJECT: ID={video.id}")

        logger.info(f"[PexelsSearch] Result: ✅ {len(verified)} passed, ❌ {blocked_count} blocked (checked: {checked_count}/{len(candidates)})")

        # 품질 좋은 순으로 반환
        return verified

    def _search_pexels(
        self,
        mood: Optional[MoodData],
        per_page: int = 20,
        strategy: Optional[str] = None
    ) -> List[PexelsVideo]:
        """
        Pexels API 검색 (3단계 우선순위)

        Args:
            mood: 감정 데이터 (strategy 사용 시 None 가능)
            per_page: 페이지당 결과 수
            strategy: 영상 전략 ("human" / "nature_bright" / "nature_calm")

        Returns:
            PexelsVideo 리스트
        """
        # 3단계 쿼리 생성
        queries = self._create_search_queries(mood, strategy)

        all_videos = []
        for priority, query in enumerate(queries, start=1):
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": query,
                        "per_page": per_page // 3,  # 각 우선순위별로 나눠서
                        "orientation": "landscape"
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    videos = data.get('videos', [])

                    for v in videos:
                        # HD 파일 찾기
                        hd_file = next(
                            (f for f in v.get('video_files', [])
                             if f.get('quality') == 'hd'),
                            v.get('video_files', [{}])[0]
                        )

                        all_videos.append(PexelsVideo(
                            id=v['id'],
                            url=v['url'],
                            image_url=v['image'],
                            duration=v.get('duration', 0),
                            width=v.get('width', 1920),
                            height=v.get('height', 1080),
                            file_path=hd_file.get('link', '')
                        ))

                    logger.info(f"Priority {priority}: {len(videos)} results for '{query}'")

            except Exception as e:
                logger.exception(f"Pexels search failed (priority {priority}): {e}")
                continue

        return all_videos

    def _create_search_queries(
        self,
        mood: Optional[MoodData],
        strategy: Optional[str] = None
    ) -> List[str]:
        """
        3단계 검색 쿼리 생성

        Args:
            mood: 감정 데이터 (strategy 사용 시 None 가능)
            strategy: 영상 전략 ("human" / "nature_bright" / "nature_calm")

        Returns:
            [Priority 1, Priority 2, Priority 3] 쿼리 리스트
        """
        # 전략 기반 쿼리 (빈도 분석 결과)
        if strategy and strategy in self.STRATEGY_KEYWORDS:
            keywords = self.STRATEGY_KEYWORDS[strategy]
            queries = keywords["primary"].copy()  # primary 키워드들
            queries.append(keywords["fallback"])  # fallback 키워드
            logger.info(f"Using strategy-based queries: {strategy}")
            return queries

        # 기본: mood 기반 쿼리 (mood가 None이면 폴백)
        if not mood:
            logger.warning("No mood or strategy provided, using fallback query")
            return ["calm nature scenery"]  # 기본 폴백

        return [
            # Priority 1: subject + emotion + color_tone
            f"{mood.subject} {mood.emotion} {mood.color_tone}",

            # Priority 2: subject + motion
            f"{mood.subject} {mood.motion}",

            # Priority 3: subject only
            f"{mood.subject}"
        ]

    def _verify_with_gemini_vision(self, thumbnail_url: str) -> bool:
        """
        Gemini Vision으로 썸네일 안전성 검증

        Args:
            thumbnail_url: 영상 썸네일 URL

        Returns:
            True (안전) / False (사람 메인 또는 부적절)
        """
        try:
            # 이미지 다운로드
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to download thumbnail: {thumbnail_url}")
                return False

            # Gemini 3 최적화 프롬프트 (간결 + 구조화 + Few-shot)
            # Reference: https://www.philschmid.de/gemini-3-prompt-practices
            # 사용자 예제 10개 기반으로 재설계 (2026-01-21)
            # 부적절 영상 필터 강화 (2026-01-21) - 노출/패션/모델링 콘텐츠 차단
            # 정면 얼굴 필터 강화 (2026-01-21) - 얼굴이 보이면 무조건 차단
            prompt = """<task>
Classify this video thumbnail for meditation/prayer/spiritual content.
This is for a Christian prayer/meditation app. Be EXTREMELY STRICT about human faces.
Output only: ACCEPT or REJECT
</task>

<reject_criteria>
REJECT if ANY of the following is present:

0. TIMELAPSE/FAST MOTION (HIGH PRIORITY - ALWAYS REJECT):
   - Cloud movement that looks unnaturally fast (timelapse clouds)
   - Fast moving shadows indicating sun position change
   - Star trails, star movement patterns (astrophotography timelapse)
   - Traffic light trails, car light streaks (long exposure)
   - Fast blooming flowers, fast growing plants
   - Unnaturally rapid water movement (waterfalls look frozen/silky = long exposure)
   - City lights turning on/off rapidly (day-to-night timelapse)
   - Crowds/people moving unnaturally fast
   - ANY visual indication of sped-up or accelerated footage

   IMPORTANT: Meditation content needs SLOW, PEACEFUL footage.
   Timelapse creates anxiety, not peace. ALWAYS REJECT.

1. HUMAN FACES (HIGHEST PRIORITY - ALWAYS REJECT):

   ⚠️ CRITICAL: ANY PERSON IN CENTER OF FRAME = AUTOMATIC REJECT
   Even if religious figure (nun, priest, monk) = REJECT

   - ANY face looking at camera (front view, 3/4 view, side view)
   - Eyes, nose, or mouth visible (even partially)
   - Face clearly identifiable (even without smile)
   - Person posing or sitting in center of frame
   - Person kneeling/praying in center of frame
   - Close-up or medium shot showing face details
   - Studio portrait style (gray background, centered person)
   - Interview/vlog/presentation setup
   - Religious figures: nun, priest, monk with ANY face visible

   EXCEPTION (ONLY these are acceptable):
   - Complete silhouette (black shadow only, no face details)
   - Back of head only (facing away from camera, no face visible)
   - Hooded figure with face COMPLETELY HIDDEN IN SHADOW (if ANY face part visible = REJECT)
   - Extreme long shot where person is tiny dot (< 2% of frame)
   - Heavy intentional blur (no features recognizable)

2. REVEALING/SUGGESTIVE CONTENT:
   - Low-cut tops, cleavage, revealing necklines
   - Tight/form-fitting clothing emphasizing body
   - Swimwear, bikini, lingerie, underwear
   - Bare shoulders, midriff, exposed skin
   - Fashion model poses (hand on hip, looking over shoulder)
   - Glamour/beauty shots, studio fashion photography
   - Seductive or alluring expressions
   - Entertainment industry footage (music videos, fashion shows)

3. Product/commercial content:
   - Hand holding light bulb, unboxing, brand logos, advertisements

4. Vehicles:
   - Cars, motorcycles, driving scenes

5. Animals (selective):
   ⚠️ REJECT ONLY:
   - Pet animals: dogs, cats (especially close-ups)
   - Cute animal videos (YouTube pet style)
   - Insects, reptiles, creepy creatures
   - Animals in unnatural/entertainment settings

   ✅ ACCEPT (Biblical/nature symbols):
   - Sheep, lamb flock (in distance/background)
   - Doves, eagles (birds in flight, distant)
   - Fish (underwater, symbolic)
   - Wildlife in natural habitat (wide shots)

6. Other inappropriate:
   - Violence, weapons, blood
   - Alcohol, smoking, drugs
   - Nightclub, bar, party scenes

7. CULT-LIKE RELIGIOUS IMAGERY (REJECT FOR SYMBOLIC MODE):
   - Cross with unnatural glowing/radiating light effects (lens flare ok, neon glow not ok)
   - Overly dramatic divine light beams (theatrical/CGI style)
   - Crosses with strange color lighting (purple, green, red neon)
   - Otherworldly/sci-fi religious imagery
   - Exaggerated supernatural effects around religious symbols
   - Stock footage with "heavenly rays" that look artificial
   - Religious symbols with HDR/over-processed look

   ACCEPT (natural religious imagery):
   - Simple wooden cross silhouette against sunset (natural light)
   - Cross in church with natural window light
   - Candles creating soft warm glow (not neon/electric)
   - Bible with soft reading lamp light
   - Sunrise/sunset creating natural golden rays

8. CATHOLIC/ORTHODOX IMAGERY (REJECT - THIS IS PROTESTANT APP):
   ⚠️ THIS IS A PROTESTANT (개신교) APP. CATHOLIC IMAGERY = REJECT.

   SIGN OF THE CROSS (성호 긋기):
   - Person making sign of the cross (touching forehead, chest, shoulders)
   - Hand movement in cross pattern on body
   - Any blessing gesture involving cross sign

   MARY/SAINTS VENERATION:
   - Virgin Mary statues or images
   - Mary with halo, crown, or religious dress
   - Saints with halos
   - Praying to Mary or saints (hands toward statue)
   - Candles lit before Mary/saint statues

   CATHOLIC SYMBOLS:
   - Rosary beads (묵주) - round beads with crucifix
   - Crucifix with Jesus body on cross (Protestant uses empty cross)
   - Catholic priest vestments (ornate robes, mitres)
   - Confessional booth
   - Holy water font
   - Incense burning in Catholic context
   - Eucharist/communion wafer held up
   - Catholic cathedral interior (ornate altars, statues)

   ORTHODOX:
   - Orthodox icons (painted religious images)
   - Orthodox priests (long beards, black robes, tall hats)
   - Orthodox church domes (onion shaped)
   - Icon corner with candles

   ACCEPT (Protestant imagery):
   - Empty wooden cross (no body)
   - Open Bible
   - Simple church interior (no statues)
   - Hands raised in worship (no cross sign)
   - Clasped praying hands (Protestant style)

9. NON-CHRISTIAN RELIGIOUS CONTENT (CRITICAL - ALWAYS REJECT):
   ⚠️ THIS IS A CHRISTIAN APP. OTHER RELIGIONS = AUTOMATIC REJECT.

   ISLAM (REJECT ALL):
   - Quran, Koran (any Islamic scripture/text)
   - Mosque, minaret, Islamic architecture (domed buildings with crescent)
   - Islamic calligraphy, Arabic religious text
   - Muslim prayer (sajda, bowing towards Mecca)
   - Islamic geometric patterns with religious context
   - Kaaba, Mecca, hajj pilgrimage scenes
   - Crescent moon and star symbol (Islamic symbol)
   - Hijab, niqab, burqa (Islamic religious dress)
   - Islamic prayer beads (misbaha/tasbih)
   - Ramadan, Eid imagery

   HINDUISM (REJECT ALL):
   - Hindu temples, shrines (gopuram towers)
   - Hindu gods/deities (Shiva, Vishnu, Ganesha, Krishna)
   - Om symbol, swastika (Hindu context)
   - Puja, aarti ceremonies
   - Hindu prayer items (diyas, incense, flowers)
   - Yoga in explicitly Hindu religious context

   BUDDHISM (REJECT ALL):
   - Buddha statues, images
   - Buddhist temples, pagodas, stupas
   - Buddhist monks (orange/saffron robes)
   - Meditation in explicitly Buddhist context
   - Prayer wheels, Buddhist prayer flags
   - Lotus in Buddhist religious context

   OTHER RELIGIONS (REJECT ALL):
   - Jewish: Menorah, Torah scroll, Star of David, synagogue, yarmulke
   - Sikh: Gurdwara, Khanda symbol, turban in religious context
   - Shinto: Torii gates, Shinto shrines
   - Any non-Christian religious text, symbols, or practices
</reject_criteria>

<accept_examples>
- Nature ONLY: mountains, ocean, forest, sky, clouds, sunset, fog, rain, waterfalls
- Architecture: church, cathedral, ancient buildings, throne rooms (no people)
- Objects: coffee cup with sunset, candles, religious symbols, books
- Text graphics: "Forgiveness", spiritual messages on nature background
- Light effects: sun rays, golden hour, lens flare
- Artistic blur, soft focus, black and white, dreamy atmosphere
- Complete silhouettes: person as black shadow against bright background
- Back view: person walking away, back of head visible only
- Hooded figures: face completely hidden in shadow
- Praying hands ONLY (no face visible at all)
- Biblical animals: sheep flock in field, doves flying, eagles soaring (distant)
</accept_examples>

<reject_examples>
TIMELAPSE/FAST MOTION (REJECT):
- Fast moving clouds across sky ❌
- Star trails or star movement ❌
- Traffic light trails at night ❌
- Day-to-night city transition ❌
- Fast blooming flowers ❌
- Silky smooth waterfalls (long exposure effect) ❌
- Crowds moving unnaturally fast ❌
- Shadows moving rapidly across landscape ❌

HUMAN FACES (REJECT):
- Woman sitting facing camera (even with neutral expression) ❌
- Man looking at camera from any angle ❌
- Person in center of frame with face visible ❌
- Studio portrait with gray background ❌
- Close-up of person's face (even if serious) ❌
- Person in tight clothing ❌
- Fashion/modeling poses ❌
- Hand holding product ❌
- Car driving ❌
- Beach scenes with swimwear ❌
- Nun/priest with face visible under veil/habit ❌
- Religious person praying with face visible ❌
- Person in church with face looking at camera ❌
- Pet dogs/cats (especially close-ups) ❌
- Cute animal videos (YouTube style) ❌
- Insects, reptiles, creepy creatures ❌

CULT-LIKE IMAGERY (REJECT):
- Cross with neon/electric glow effect ❌
- Overly dramatic "heavenly rays" (CGI style) ❌
- Purple/green/red glowing religious symbols ❌
- Sci-fi style religious imagery ❌
- Over-processed HDR religious photos ❌

CATHOLIC/ORTHODOX (THIS IS PROTESTANT APP - REJECT):
- Person making sign of the cross (성호 긋기) ❌
- Virgin Mary statue or image ❌
- Saints with halos ❌
- Rosary beads (묵주) ❌
- Crucifix with Jesus body on cross ❌
- Catholic priest in ornate vestments ❌
- Orthodox icons, Orthodox priests ❌
- Praying before Mary/saint statue ❌
- Confessional booth, holy water ❌
- Ornate Catholic altar with statues ❌

NON-CHRISTIAN RELIGIOUS (CRITICAL - REJECT):
- Quran/Koran (Islamic scripture) ❌
- Mosque, minaret, Islamic architecture ❌
- Muslim prayer (person bowing/prostrating) ❌
- Islamic calligraphy, Arabic religious text ❌
- Crescent moon with star (Islamic symbol) ❌
- Buddha statue or image ❌
- Buddhist temple, pagoda ❌
- Hindu temple, deity statue ❌
- Om symbol, Hindu gods ❌
- Menorah, Torah, Star of David ❌
- Any non-Christian religious content ❌
</reject_examples>

CRITICAL RULE: If you can see a person's face clearly (eyes, nose, mouth), ALWAYS REJECT.
This is for meditation content - faces distract from contemplation.

Output:"""

            # Gemini Vision 호출
            result = self.vision_model.generate_content(
                [
                    {
                        "mime_type": "image/jpeg",
                        "data": response.content
                    },
                    prompt
                ]
            )

            verdict = result.text.strip().upper()
            is_safe = "ACCEPT" in verdict

            logger.info(
                f"[Gemini Vision] {thumbnail_url[-20:]} → {verdict} "
                f"({'✅ PASS' if is_safe else '❌ BLOCKED'})"
            )

            return is_safe

        except Exception as e:
            logger.exception(f"Gemini Vision failed: {e}")
            # 폴백: 실패 시 안전하다고 가정 (False Positive보다 False Negative 선호)
            return True

    def _score_with_gemini_vision(self, thumbnail_url: str, strategy: str = None) -> VisionScore:
        """
        Gemini Vision으로 썸네일 점수화 검증 (v1.5)
        
        기존 accept/reject 이진 판단에서 상세 점수화로 개선
        
        Args:
            thumbnail_url: 영상 썸네일 URL
            strategy: 현재 검색 전략 (semantic_match 계산용)
            
        Returns:
            VisionScore 객체
        """
        try:
            # 이미지 다운로드
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to download thumbnail: {thumbnail_url}")
                return VisionScore(hard_reject=True, reject_reason="download_failed")
            
            # v1.5 점수화 프롬프트 (JSON 출력)
            prompt = """<task>
Analyze this video thumbnail for Christian meditation/prayer content.
Output a JSON object with the following structure (no markdown, just raw JSON):
</task>

<output_schema>
{
  "has_face_closeup": boolean,
  "has_cityscape": boolean,
  "has_logo_text": boolean,
  "has_modern_objects": boolean,
  "has_revealing_content": boolean,
  "scene_tags": ["tag1", "tag2"],
  "mood_tags": ["tag1", "tag2"],
  "biblical_vibe": 0-100,
  "visual_quality": 0-100,
  "modernness": 0-100,
  "reject_reason": "string or empty"
}
</output_schema>

<scoring_guide>
- has_face_closeup: true if ANY human face is clearly visible (eyes, nose, mouth)
- has_cityscape: true if city buildings, skyscrapers, urban scenes present
- has_logo_text: true if brand logos, watermarks, or prominent text visible
- has_modern_objects: true if cars, smartphones, laptops, modern furniture present
- has_revealing_content: true if revealing clothing, suggestive poses present
- scene_tags: describe what's in the image (e.g., "desert", "sunset", "hands", "cross")
- mood_tags: describe the feeling (e.g., "peaceful", "solemn", "hopeful")
- biblical_vibe: 0-100, how much it feels like biblical/spiritual content
- visual_quality: 0-100, image clarity, composition, aesthetic appeal
- modernness: 0-100, how modern/contemporary it looks (lower = more timeless/biblical)
- reject_reason: brief reason if any hard reject criteria met, empty otherwise
</scoring_guide>

<acceptable_content>
- Nature landscapes (mountains, deserts, oceans, forests)
- Silhouettes (complete black shadow, no face visible)
- Back views (person facing away from camera)
- Praying hands (no face)
- Religious symbols (cross, bible, candles)
- Biblical animals (sheep, doves, eagles in distance)
</acceptable_content>

Output ONLY the JSON object:"""

            # Gemini Vision 호출
            result = self.vision_model.generate_content(
                [
                    {
                        "mime_type": "image/jpeg",
                        "data": response.content
                    },
                    prompt
                ]
            )
            
            # JSON 파싱
            import json
            import re
            
            response_text = result.text.strip()
            # Remove markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Vision JSON: {response_text[:100]}")
                # 폴백: 기존 accept/reject 로직 사용
                is_accept = "ACCEPT" in response_text.upper()
                return VisionScore(
                    hard_reject=not is_accept,
                    reject_reason="json_parse_failed" if not is_accept else ""
                )
            
            # VisionScore 생성
            score = VisionScore(
                has_face_closeup=data.get("has_face_closeup", False),
                has_cityscape=data.get("has_cityscape", False),
                has_logo_text=data.get("has_logo_text", False),
                has_modern_objects=data.get("has_modern_objects", False),
                has_revealing_content=data.get("has_revealing_content", False),
                scene_tags=data.get("scene_tags", []),
                mood_tags=data.get("mood_tags", []),
                semantic_match=self._calculate_semantic_match(data.get("scene_tags", []), strategy),
                biblical_vibe=data.get("biblical_vibe", 50),
                visual_quality=data.get("visual_quality", 50),
                modernness=data.get("modernness", 50),
                reject_reason=data.get("reject_reason", "")
            )
            
            logger.info(
                f"[Vision Score] {thumbnail_url[-20:]} → "
                f"{'❌ REJECT' if score.hard_reject else f'✅ {score.final_score}점'} "
                f"(biblical={score.biblical_vibe}, modern={score.modernness})"
            )
            
            return score
            
        except Exception as e:
            logger.exception(f"Gemini Vision scoring failed: {e}")
            return VisionScore(hard_reject=False, semantic_match=50, biblical_vibe=50)
    
    def _calculate_semantic_match(self, scene_tags: List[str], strategy: str) -> int:
        """
        scene_tags와 전략의 매칭 점수 계산
        
        Args:
            scene_tags: Gemini Vision이 감지한 장면 태그
            strategy: 현재 검색 전략
            
        Returns:
            0-100 점수
        """
        if not scene_tags or not strategy:
            return 50
        
        # 전략별 기대 태그
        expected_tags = {
            "human": ["silhouette", "shadow", "back", "hooded", "praying", "hands", "kneeling"],
            "nature_bright": ["sunrise", "sunset", "golden", "light", "rays", "mountain", "hope"],
            "nature_calm": ["lake", "water", "calm", "peaceful", "forest", "serene", "ocean"],
            "symbolic": ["hands", "prayer", "bible", "cross", "candle", "worship", "church"]
        }
        
        if strategy not in expected_tags:
            return 50
        
        # 겹치는 태그 개수로 점수 계산
        matched = sum(1 for tag in scene_tags if any(exp in tag.lower() for exp in expected_tags[strategy]))
        score = min(100, 30 + matched * 20)  # 기본 30점 + 태그당 20점
        
        return score


    def _calculate_quality_score(self, video: PexelsVideo, mood: MoodData) -> int:
        """
        품질 점수 계산 (0-100점)

        Args:
            video: Pexels 영상
            mood: 감정 데이터

        Returns:
            품질 점수
        """
        score = 0

        # 1. 검색 우선순위 (40점 최대)
        # → 이미 search 단계에서 우선순위별로 나뉘므로 여기서는 생략 가능
        # 간단히 duration 기준으로 대체
        if 15 <= video.duration <= 30:
            score += 40
        elif 10 <= video.duration < 15:
            score += 30
        elif video.duration > 30:
            score += 20
        else:
            score += 10

        # 2. 해상도 (20점)
        if video.width >= 1920 and video.height >= 1080:
            score += 20
        elif video.width >= 1280:
            score += 15
        else:
            score += 10

        # 3. 영상 길이 (20점)
        if 15 <= video.duration <= 30:
            score += 20
        elif 10 <= video.duration < 15:
            score += 15
        elif video.duration > 30:
            score += 10

        # 4. Gemini Vision 안전성 (20점)
        if video.vision_verified:
            score += 20

        return min(score, 100)


def get_video_search() -> PexelsVideoSearch:
    """PexelsVideoSearch 싱글톤"""
    return PexelsVideoSearch()
