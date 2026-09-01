import json
import os
import re


def normalize_slug(value, *, fallback="report"):
    text = str(value or fallback).strip()
    text = re.sub(r"[^0-9A-Za-z가-힣_.\-\s]+", "_", text)
    text = re.sub(r"[\s/\\]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def next_versioned_path(path):
    """주어진 경로에 대해 새 버전을 붙인 경로를 계산합니다."""
    if not path:
        raise ValueError("path must not be empty")

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    base, ext = os.path.splitext(path)
    final_path = path

    while os.path.exists(final_path):
        match = re.search(r"_v(\d+)$", base)
        if match:
            current_version = int(match.group(1))
            base = re.sub(r"_v\d+$", f"_v{current_version + 1}", base)
        else:
            base = f"{base}_v2"
        final_path = f"{base}{ext}"

    return final_path


def coerce_llm_text(value):
    """Gemini 등 일부 모델이 반환하는 list/dict 구조를 안전한 문자열로 변환합니다."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        if all(not isinstance(item, (list, tuple, dict)) for item in value):
            return json.dumps(list(value), ensure_ascii=False)
        parts = [coerce_llm_text(item) for item in value]
        return "\n\n".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("text", "content", "output_text", "message", "response", "markdown", "draft", "summary"):
            if key in value and value[key] is not None:
                return coerce_llm_text(value[key])
        if "parts" in value:
            return coerce_llm_text(value["parts"])
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def save_file_append_only(path, content):
    """기존 파일 덮어쓰기를 방지하고 안전한 새 버전 경로를 생성합니다."""
    normalized = coerce_llm_text(content)
    final_path = next_versioned_path(path)
    with open(final_path, 'x', encoding='utf-8') as f:
        f.write(normalized)
    return final_path


def build_report_artifact_path(topic, phase, *, section_title=None, base_dir="workspace/report"):
    safe_topic = normalize_slug(topic)
    if section_title:
        safe_title = normalize_slug(section_title)
        return next_versioned_path(os.path.join(base_dir, f"{safe_topic}_{phase}_{safe_title}.md"))
    return next_versioned_path(os.path.join(base_dir, f"{safe_topic}_{phase}.md"))


def register_artifact(state, *, artifact_type, title, path, detail=None):
    history = state.setdefault("artifact_history", [])
    entry = {
        "type": artifact_type,
        "title": title,
        "path": path,
        "detail": detail or "",
    }
    history.append(entry)
    state["active_version"] = path
    return entry
