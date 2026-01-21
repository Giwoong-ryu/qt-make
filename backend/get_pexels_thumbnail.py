"""
Pexels API로 클립 8719740의 썸네일 URL 가져오기
"""
import os
import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    print("PEXELS_API_KEY 환경변수가 설정되지 않았습니다.")
    exit(1)

clip_id = 8719740

# Pexels Videos API - Get Video by ID
url = f"https://api.pexels.com/videos/videos/{clip_id}"
headers = {"Authorization": PEXELS_API_KEY}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()

    print(f"[Pexels Video: {clip_id}]")
    print(f"  URL: {data.get('url')}")
    print(f"  Image (Thumbnail): {data.get('image')}")
    print(f"  Duration: {data.get('duration')} seconds")
    print(f"  Width x Height: {data.get('width')} x {data.get('height')}")

    # video_files 확인
    video_files = data.get("video_files", [])
    for vf in video_files:
        if vf.get("quality") == "hd":
            print(f"\n  HD Video: {vf.get('link')}")
            break
else:
    print(f"Error: {response.status_code}")
    print(response.text)
