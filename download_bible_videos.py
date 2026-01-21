"""
SamuraiPolix/Shorts-Maker에서 57개 성경 배경 영상 다운로드
"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://raw.githubusercontent.com/SamuraiPolix/Shorts-Maker/master/videos"
OUTPUT_DIR = "bible_video_samples"

# 전체 영상 목록 (1-57, 29 제외 - repo에 없음)
VIDEO_IDS = list(range(1, 58))
if 29 not in VIDEO_IDS:
    VIDEO_IDS.append(29)
VIDEO_IDS = sorted(VIDEO_IDS)

def download_video(video_id):
    url = f"{BASE_URL}/{video_id}.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    
    if os.path.exists(output_path):
        return f"[SKIP] {video_id}.mp4 already exists"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            size_mb = len(response.content) / (1024 * 1024)
            return f"[OK] {video_id}.mp4 ({size_mb:.1f}MB)"
        else:
            return f"[FAIL] {video_id}.mp4 - HTTP {response.status_code}"
    except Exception as e:
        return f"[ERROR] {video_id}.mp4 - {str(e)}"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"다운로드 시작: {len(VIDEO_IDS)}개 영상")
    print(f"저장 위치: {os.path.abspath(OUTPUT_DIR)}")
    print("-" * 50)
    
    completed = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_video, vid): vid for vid in VIDEO_IDS}
        
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            print(f"[{completed}/{len(VIDEO_IDS)}] {result}")
    
    print("-" * 50)
    print("다운로드 완료!")
    
    # 결과 확인
    files = os.listdir(OUTPUT_DIR)
    mp4_files = [f for f in files if f.endswith('.mp4')]
    total_size = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in mp4_files)
    print(f"총 {len(mp4_files)}개 영상, {total_size / (1024*1024):.1f}MB")

if __name__ == "__main__":
    main()
