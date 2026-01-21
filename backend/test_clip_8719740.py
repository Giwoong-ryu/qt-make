"""
Pexels ID 8719740 클립을 Gemini Vision으로 테스트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import google.generativeai as genai
import requests

# Gemini API 설정 (GOOGLE_API_KEY 또는 GEMINI_API_KEY 사용)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

def test_clip_classification():
    """Pexels ID 8719740의 썸네일을 Gemini Vision으로 분류"""

    # Pexels 클립 ID
    clip_id = 8719740

    # Pexels 썸네일 URL (실제 Pexels API가 반환하는 형식)
    thumbnail_url = f"https://images.pexels.com/videos/{clip_id}/adult-art-bead-bible-{clip_id}.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=630&w=1200"

    print(f"[테스트 클립]")
    print(f"  Pexels ID: {clip_id}")
    print(f"  Thumbnail URL: {thumbnail_url}")
    print(f"  Video Page: https://www.pexels.com/video/{clip_id}/")
    print()

    # Gemini Vision Prompt (background_video_search.py와 동일)
    prompt = """<task>
Classify this video thumbnail for meditation/prayer/spiritual content.
This is for a Christian prayer/meditation app. Be EXTREMELY STRICT about human faces.
Output only: ACCEPT or REJECT
</task>

<reject_criteria>
REJECT if ANY of the following is present:

1. HUMAN FACES (HIGHEST PRIORITY - ALWAYS REJECT):
   - ANY face looking at camera (front view, 3/4 view, side view)
   - Eyes visible and looking towards viewer
   - Face clearly identifiable (even without smile)
   - Person posing or sitting in center of frame
   - Close-up or medium shot showing face details
   - Studio portrait style (gray background, centered person)
   - Interview/vlog/presentation setup

   EXCEPTION (ONLY these are acceptable):
   - Complete silhouette (black shadow only, no face details)
   - Back of head only (facing away from camera)
   - Hooded figure with face COMPLETELY HIDDEN IN SHADOW (if ANY face part visible = REJECT)
   - Extreme long shot where face is tiny dot (< 5% of frame)
   - Blurred/out of focus face (intentional artistic blur)

   ⚠️ IMPORTANT: Nun/veil/religious clothing does NOT exempt from face rule.
   If you can see eyes, nose, or mouth under veil/habit → REJECT!

2. Inappropriate content:
   - Violence, weapons, fighting
   - Controversial symbols, political content
   - Sexual/romantic content
   - Partying, drinking, nightlife
   - Urban chaos (traffic, crowds, protests)

3. Distracting content:
   - Bright neon lights, flashy colors
   - Text overlays, captions, logos
   - Commercial products (phones, laptops)
   - Modern technology close-ups
</reject_criteria>

<accept_criteria>
ACCEPT ONLY if ALL of the following are true:

1. NO human face visible (as defined above)
2. Content fits meditation/prayer theme:
   - Nature: forests, mountains, oceans, skies
   - Abstract: flowing water, clouds, light beams
   - Spiritual symbols: candles, crosses (non-political)
   - Peaceful scenes: empty churches, gardens, sunsets
3. Calm colors: earth tones, pastels, soft lighting
4. Slow motion or still shots
</accept_criteria>

<output_format>
Output ONLY one word: ACCEPT or REJECT
NO explanations, NO additional text.
</output_format>"""

    # Gemini 2.5 Flash 모델 사용 (background_video_search.py와 동일)
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("[Gemini Vision 분류 시작...]")
    try:
        # 1. 썸네일 다운로드
        print(f"  썸네일 다운로드 중...")
        img_response = requests.get(thumbnail_url, timeout=10)
        img_response.raise_for_status()

        # 2. Gemini Vision 호출 (바이너리 데이터로 전달)
        print(f"  Gemini Vision 분석 중...")
        response = model.generate_content([
            {
                "mime_type": "image/jpeg",
                "data": img_response.content
            },
            prompt
        ])

        result = response.text.strip().upper()
        print(f"\n[결과] {result}")

        if "REJECT" in result:
            print("  → ❌ REJECT (얼굴 또는 부적절한 콘텐츠 감지)")
        elif "ACCEPT" in result:
            print("  → ✅ ACCEPT (명상/기도 콘텐츠로 분류됨)")
        else:
            print(f"  → ⚠️ 예상치 못한 응답: {result}")

    except Exception as e:
        print(f"\n[에러] {e}")

if __name__ == "__main__":
    test_clip_classification()
