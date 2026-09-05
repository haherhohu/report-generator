"""File management with append-only versioning and artifact tracking."""
from __future__ import annotations

import json
import os
import re
from typing import Any

def normalize_slug(value: Any, *, fallback: str = "report") -> str:
    text = str(value or fallback).strip()
    text = re.sub(r"[^0-9A-Za-z가-힣_.\-\s]+", "_", text)
    text = re.sub(r"[\s/\\]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def next_versioned_path(path: str) -> str:
    """주어진 파일 경로가 이미 존재하면 _v2, _v3 형태로 고유한 새 경로를 반환."""
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


def coerce_llm_text(value: Any) -> str:
    """Gemini나 OpenAI 등 다양한 모델 응답 포맷을 순수 문자열로 안전하게 변환."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        parts = [coerce_llm_text(item) for item in value]
        return "\n\n".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("text", "content", "output_text", "message", "response", "markdown", "draft", "summary"):
            if key in value and value[key] is not None:
                return coerce_llm_text(value[key])
        if "parts" in value:
            return coerce_llm_text(value["parts"])
        return json.dumps(value, ensure_ascii=False, indent=2)
    if hasattr(value, "text"):
        return str(value.text or "").strip()
    if hasattr(value, "content"):
        return coerce_llm_text(value.content)
    return str(value)


def save_file_append_only(path: str, content: Any) -> str:
    """기존 파일 덮어쓰기를 방지하고 항상 새로운 버전 파일로 안전하게 저장."""
    normalized = coerce_llm_text(content)
    final_path = next_versioned_path(path)
    with open(final_path, "x", encoding="utf-8") as f:
        f.write(normalized)
    return final_path


def build_report_artifact_path(
    topic: str,
    phase: str,
    *,
    section_title: str | None = None,
    base_dir: str = "workspace/report",
) -> str:
    """보고서 및 섹션별 단계에 맞는 아티팩트 파일 경로 생성."""
    safe_topic = normalize_slug(topic)
    if section_title:
        safe_title = normalize_slug(section_title)
        filename = f"{safe_topic}_{phase}_{safe_title}.md"
    else:
        filename = f"{safe_topic}_{phase}.md"
    return next_versioned_path(os.path.join(base_dir, filename))


def register_artifact(state: dict, *, artifact_type: str, title: str, path: str, detail: str | None = None) -> dict:
    """파이프라인 실행 중 생성된 산출물을 상태 히스토리에 기록."""
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

