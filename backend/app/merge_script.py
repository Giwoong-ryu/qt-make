import os

base_dir = r"c:\Users\user\Desktop\gpt\n8n-make\kmong_work\qt-make\qt-video-saas\backend\app"
src_path = os.path.join(base_dir, "regenerate_task_snippet.py")
dst_path = os.path.join(base_dir, "tasks.py")

try:
    with open(src_path, "r", encoding="utf-8") as src:
        content = src.read()
    
    with open(dst_path, "a", encoding="utf-8") as dst:
        dst.write("\n\n" + content)
        
    print("Successfully merged tasks.py")
except Exception as e:
    print(f"Error merging files: {e}")
