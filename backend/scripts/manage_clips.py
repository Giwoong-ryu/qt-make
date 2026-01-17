#!/usr/bin/env python3
"""
배경 클립 관리 스크립트
- 클립 목록 조회
- 특정 클립 비활성화
- 부적절한 클립 일괄 비활성화
"""
import os
import sys

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


def get_supabase():
    """Supabase 클라이언트 생성"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수를 설정하세요")
    return create_client(url, key)


def list_clips(pack_id: str = "pack-free", show_inactive: bool = False):
    """클립 목록 조회"""
    supabase = get_supabase()

    query = supabase.table("clips").select("*").eq("pack_id", pack_id)
    if not show_inactive:
        query = query.eq("is_active", True)

    result = query.order("created_at", desc=True).execute()

    print(f"\n=== {pack_id} 클립 목록 ===")
    print(f"{'ID':<40} {'이름':<30} {'카테고리':<15} {'활성':<5}")
    print("-" * 100)

    for clip in result.data:
        status = "Y" if clip.get("is_active") else "N"
        name = clip.get("name", "")[:28]
        category = clip.get("category", "")[:13]
        print(f"{clip['id']:<40} {name:<30} {category:<15} {status:<5}")

    print(f"\n총 {len(result.data)}개 클립")
    return result.data


def deactivate_clip(clip_id: str):
    """클립 비활성화"""
    supabase = get_supabase()

    result = supabase.table("clips").update({
        "is_active": False
    }).eq("id", clip_id).execute()

    if result.data:
        print(f"[OK] 클립 비활성화됨: {clip_id}")
        return True
    else:
        print(f"[FAIL] 클립을 찾을 수 없음: {clip_id}")
        return False


def deactivate_by_keyword(keyword: str, pack_id: str = "pack-free"):
    """키워드가 포함된 클립 비활성화"""
    supabase = get_supabase()

    # 클립 목록 조회
    result = supabase.table("clips").select("*").eq("pack_id", pack_id).eq("is_active", True).execute()

    deactivated = []
    for clip in result.data:
        name = clip.get("name", "").lower()
        file_path = clip.get("file_path", "").lower()

        if keyword.lower() in name or keyword.lower() in file_path:
            deactivate_clip(clip["id"])
            deactivated.append(clip)

    print(f"\n총 {len(deactivated)}개 클립 비활성화됨 (키워드: {keyword})")
    return deactivated


def delete_clip_permanently(clip_id: str):
    """클립 영구 삭제 (주의!)"""
    supabase = get_supabase()

    # 먼저 클립 정보 조회
    clip = supabase.table("clips").select("*").eq("id", clip_id).execute()
    if not clip.data:
        print(f"[FAIL] 클립을 찾을 수 없음: {clip_id}")
        return False

    clip_info = clip.data[0]
    print(f"삭제할 클립: {clip_info.get('name')} ({clip_info.get('file_path')})")

    confirm = input("정말 삭제하시겠습니까? (yes 입력): ")
    if confirm.lower() != "yes":
        print("취소됨")
        return False

    # DB에서 삭제
    result = supabase.table("clips").delete().eq("id", clip_id).execute()
    print(f"[OK] 클립 삭제됨: {clip_id}")
    return True


def find_inappropriate_clips(pack_id: str = "pack-free"):
    """부적절할 수 있는 클립 찾기 (말, 춤 등)"""
    keywords = ["horse", "dance", "dancing", "man", "person", "people", "말", "춤", "사람"]

    supabase = get_supabase()
    result = supabase.table("clips").select("*").eq("pack_id", pack_id).eq("is_active", True).execute()

    suspicious = []
    for clip in result.data:
        name = clip.get("name", "").lower()
        file_path = clip.get("file_path", "").lower()

        for keyword in keywords:
            if keyword in name or keyword in file_path:
                suspicious.append({
                    **clip,
                    "matched_keyword": keyword
                })
                break

    if suspicious:
        print(f"\n=== 부적절할 수 있는 클립 ({len(suspicious)}개) ===")
        for clip in suspicious:
            print(f"  - {clip['id']}: {clip.get('name')} (매칭: {clip['matched_keyword']})")
    else:
        print("\n부적절한 클립이 발견되지 않았습니다.")

    return suspicious


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="배경 클립 관리")
    parser.add_argument("command", choices=["list", "deactivate", "delete", "find-bad", "deactivate-keyword"],
                        help="실행할 명령")
    parser.add_argument("--clip-id", help="클립 ID")
    parser.add_argument("--keyword", help="검색 키워드")
    parser.add_argument("--pack-id", default="pack-free", help="배경팩 ID")
    parser.add_argument("--show-inactive", action="store_true", help="비활성 클립도 표시")

    args = parser.parse_args()

    if args.command == "list":
        list_clips(args.pack_id, args.show_inactive)

    elif args.command == "deactivate":
        if not args.clip_id:
            print("--clip-id 옵션이 필요합니다")
            sys.exit(1)
        deactivate_clip(args.clip_id)

    elif args.command == "delete":
        if not args.clip_id:
            print("--clip-id 옵션이 필요합니다")
            sys.exit(1)
        delete_clip_permanently(args.clip_id)

    elif args.command == "find-bad":
        find_inappropriate_clips(args.pack_id)

    elif args.command == "deactivate-keyword":
        if not args.keyword:
            print("--keyword 옵션이 필요합니다")
            sys.exit(1)
        deactivate_by_keyword(args.keyword, args.pack_id)
