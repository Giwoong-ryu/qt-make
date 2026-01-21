"""
Pexels에서 기독교/성경 관련 영상 대량 다운로드
"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

PEXELS_API_KEY = "SAfJgRX4oHDQsUytFJBP6crGNSK7r7cWJLexZ03aLXlCCRFykwKBWlYH"
OUTPUT_DIR = "pexels_christian_videos"

# 기독교/성경 관련 검색 키워드
SEARCH_QUERIES = [
    "christian worship",
    "christian cross",
    "church interior",
    "prayer hands",
    "bible book",
    "sunrise worship",
    "peaceful nature meditation",
    "candle flame dark",
    "water reflection calm",
    "clouds sky dramatic",
    "desert wilderness",
    "ancient ruins",
    "olive tree garden",
    "mountain landscape peaceful",
    "sea waves calm",
]

def search_pexels_videos(query, per_page=15, page=1):
    """Pexels API로 영상 검색"""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": per_page,
        "page": page,
        "orientation": "portrait"  # 세로 영상
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code == 200:
        return response.json().get("videos", [])
    else:
        print(f"[ERROR] Search failed for '{query}': {response.status_code}")
        return []

def download_video(video_data, output_dir):
    """영상 다운로드"""
    video_id = video_data["id"]
    
    # HD 품질 영상 URL 찾기
    video_files = video_data.get("video_files", [])
    hd_file = None
    for vf in video_files:
        if vf.get("quality") == "hd" and vf.get("width", 0) <= 1080:
            hd_file = vf
            break
    
    if not hd_file:
        # HD 없으면 가장 작은 파일
        video_files_sorted = sorted(video_files, key=lambda x: x.get("width", 9999))
        if video_files_sorted:
            hd_file = video_files_sorted[0]
    
    if not hd_file:
        return f"[SKIP] {video_id} - no video file"
    
    output_path = os.path.join(output_dir, f"pexels_{video_id}.mp4")
    if os.path.exists(output_path):
        return f"[SKIP] {video_id} - already exists"
    
    try:
        video_url = hd_file["link"]
        response = requests.get(video_url, timeout=120)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            size_mb = len(response.content) / (1024 * 1024)
            return f"[OK] pexels_{video_id}.mp4 ({size_mb:.1f}MB)"
        else:
            return f"[FAIL] {video_id} - HTTP {response.status_code}"
    except Exception as e:
        return f"[ERROR] {video_id} - {str(e)[:50]}"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Pexels 기독교 영상 다운로드")
    print(f"검색 키워드: {len(SEARCH_QUERIES)}개")
    print(f"저장 위치: {os.path.abspath(OUTPUT_DIR)}")
    print("-" * 50)
    
    all_videos = []
    seen_ids = set()
    
    # 각 키워드로 검색
    for query in SEARCH_QUERIES:
        print(f"검색 중: '{query}'...")
        videos = search_pexels_videos(query, per_page=15, page=1)
        
        for v in videos:
            if v["id"] not in seen_ids:
                seen_ids.add(v["id"])
                all_videos.append(v)
        
        time.sleep(0.5)  # API 레이트 리밋 방지
    
    print(f"\n총 {len(all_videos)}개 고유 영상 발견")
    print("-" * 50)
    
    # 다운로드
    completed = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(download_video, v, OUTPUT_DIR): v["id"] for v in all_videos}
        
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            print(f"[{completed}/{len(all_videos)}] {result}")
    
    print("-" * 50)
    print("다운로드 완료!")
    
    # 결과 확인
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
    total_size = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in files)
    print(f"총 {len(files)}개 영상, {total_size / (1024*1024):.1f}MB")

if __name__ == "__main__":
    main()
