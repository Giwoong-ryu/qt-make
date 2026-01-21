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

5. Other inappropriate:
   - Violence, weapons, blood
   - Alcohol, smoking, drugs
   - Nightclub, bar, party scenes
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
</accept_examples>

<reject_examples>
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
</reject_examples>

CRITICAL RULE: If you can see a person's face clearly (eyes, nose, mouth), ALWAYS REJECT.
This is for meditation content - faces distract from contemplation.

Output:"""

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
