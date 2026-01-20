"""
배경 영상 검색 서비스 (Pexels API + Gemini Vision)

감정 데이터 기반 Pexels 검색 및 Gemini Vision 안전성 검증
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

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
    STRATEGY_KEYWORDS = {
        "human": {
            "primary": [
                "person silhouette suffering dark",
                "hooded figure alone despair shadow",
                "person kneeling prayer contemplation",
                "person crouched pain sorrow"
            ],
            "fallback": "dark lonely figure silhouette"
        },
        "nature_bright": {
            "primary": [
                "sunrise golden hour mountain hope",
                "light breaking through clouds rays",
                "morning sunlight forest peace",
                "golden rays hope landscape"
            ],
            "fallback": "bright nature sunrise golden"
        },
        "nature_calm": {
            "primary": [
                "calm mountain landscape serene",
                "peaceful lake reflection quiet",
                "serene forest nature tranquil",
                "quiet ocean waves gentle"
            ],
            "fallback": "calm nature scenery peaceful"
        }
    }

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
        self.vision_model = genai.GenerativeModel('gemini-2.5-flash-lite')

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

    def search_by_visual_description(
        self,
        visual_query: str,
        duration_needed: int,
        max_results: int = 5
    ) -> List[PexelsVideo]:
        """
        Visual Description 기반 영상 검색 (Stage 3)

        이 메서드는 LLM 감독이 생성한 시각적 묘사를 받아서
        Pexels에서 영상을 검색합니다.

        Args:
            visual_query: LLM이 생성한 영어 시각 묘사
                         예: "A woman looking anxious and jealous in an ancient palace,
                              shadowy lighting, tense atmosphere, cinematic style"
            duration_needed: 필요한 영상 길이 (초)
            max_results: 반환할 영상 개수

        Returns:
            검증된 PexelsVideo 리스트
        """
        logger.info(f"[PexelsSearch] Visual query: {visual_query}")

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
        modified_query = visual_query
        for bright_word in bright_keywords:
            modified_query = modified_query.replace(bright_word, "")

        # 어두운 톤 키워드 추가 (70% 확률)
        import random
        if random.random() < 0.7:  # 70% 확률로 어두운 톤 강제
            dark_keyword = random.choice(dark_tone_keywords)
            modified_query = f"{modified_query} {dark_keyword}"

        logger.info(f"[PexelsSearch] Modified query (dark tone): {modified_query}")

        # 1. Pexels 검색 (수정된 쿼리 사용)
        try:
            response = requests.get(
                self.BASE_URL,
                headers={"Authorization": self.pexels_key},
                params={
                    "query": modified_query,
                    "per_page": 20,
                    "orientation": "landscape"
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Pexels API error: {response.status_code}")
                return []

            data = response.json()
            videos_data = data.get("videos", [])

            if not videos_data:
                logger.warning("No videos found for visual query")
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

        # 2. Gemini Vision으로 썸네일 검증
        verified = []
        for video in candidates:
            if len(verified) >= max_results:
                break

            is_safe = self._verify_with_gemini_vision(video.image_url)
            if is_safe:
                video.vision_verified = True
                video.quality_score = 50  # 기본 점수
                verified.append(video)

        logger.info(f"[PexelsSearch] Verified {len(verified)}/{len(candidates)} videos")
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

            # Gemini Vision 프롬프트 (QT 묵상 영상 톤: 어두움 70% / 밝음 30%)
            prompt = """이 영상 썸네일을 분석해주세요.

다음 중 하나라도 해당되면 "REJECT":

【사람 관련 REJECT】
- 사람의 얼굴이 정면에서 보임 (눈, 코, 입 식별 가능)
- 사람 얼굴이 화면 중앙/측면 어디든 크게 보임
- 사람 얼굴 표정이 명확하게 보임
- 사람이 손으로 물건을 조작하는 클로즈업 (예: 상자에서 물건 꺼내기)
- **화질이 안 좋은 영상** (흐릿함, 노이즈, 저화질)

【소품/제품 관련 REJECT】
- 제품, 상자, 도구, 소품이 화면 중심
- 브랜드명이나 로고가 보임 (예: "Kind" 같은 제품명)
- 상업적 느낌의 촬영 (제품 광고, 언박싱 등)

【빛/밝기 관련 REJECT - 최우선 차단!】
- **강한 빛줄기나 광선이 보임** (light beam, sunbeam, ray of light)
- **과도하게 밝고 강렬한 빛** (spotlight, 직사광선)
- 햇살 가득한 화사한 분위기 (선명한 노란색/주황색 빛)
- 과도하게 따뜻한 톤 (golden hour, sunrise/sunset의 강렬한 빛)
- 밝고 활기찬 느낌 (묵상 분위기 부적합)

【기타 REJECT】
- 자동차, 오토바이, 기계류가 보임
- 부적절한 콘텐츠

다음은 "ACCEPT":
- 풍경, 자연, 건축물이 메인
- **어둡고 묵직한 분위기** (dim light, soft shadows, subdued tones)
- **차분하고 경건한 톤** (solemn, reverent, contemplative mood)
- **고화질 영상** (선명하고 깨끗함)
- 사람은 있지만 얼굴이 보이지 않음:
  * 뒷모습, 실루엣
  * 멀리서 작게 보임 (배경)
  * 후드나 모자로 얼굴 완전히 가려짐
  * 고개를 깊이 숙여서 얼굴 안 보임
- 인간의 신체 표현 (얼굴 제외):
  * 엎드린 모습 (기도, 절망)
  * 무릎 꿇은 자세 (회개, 탄원)
  * 두 손 마주잡음 (기도, 간구)
  * 웅크린 자세 (고통, 슬픔)
- 사람 손, 발만 보임
- 빛, 하늘, 물, 자연 요소 중심 (단, 어둡거나 중립적인 톤)

**톤 우선순위**: 어두움(70%) > 밝음(30%)
- 어두운 영상 우선 선택
- 밝은 영상은 30% 이하만 허용

응답: "ACCEPT" 또는 "REJECT" 한 단어만 출력"""

            # Gemini Vision 호출
            result = self.vision_model.generate_content([
                {
                    "mime_type": "image/jpeg",
                    "data": response.content
                },
                prompt
            ])

            verdict = result.text.strip().upper()
            is_safe = "ACCEPT" in verdict

            logger.debug(
                f"Vision check: {thumbnail_url} → {verdict} "
                f"({'safe' if is_safe else 'blocked'})"
            )

            return is_safe

        except Exception as e:
            logger.exception(f"Gemini Vision failed: {e}")
            # 폴백: 실패 시 안전하다고 가정 (False Positive보다 False Negative 선호)
            return True

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
