import os
import re

def save_file_append_only(path, content):
    # 덮어쓰기 방지 로직 구현
    """
    기존 파일 덮어쓰기를 방지하고 새로운 이름으로 저장합니다.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    base, ext = os.path.splitext(path)
    final_path = path

    # 동일 파일 존재 시 _vN 패턴을 증가시킴 (예: v1 -> v2 -> v3)
    while os.path.exists(final_path):
        match = re.search(r"_v(\d+)$", base)
        if match:
            current_version = int(match.group(1))
            base = re.sub(r"_v\d+$", f"_v{current_version + 1}", base)
        else:
            base = f"{base}_v2"
        final_path = f"{base}{ext}"
        
    # 'x' 모드(exclusive creation)로 열어 혹시 모를 동시 접근 충돌 원천 차단
    with open(final_path, 'x', encoding='utf-8') as f:
        f.write(content)
        
    return final_path