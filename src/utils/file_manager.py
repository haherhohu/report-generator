"""File management with append-only versioning and artifact tracking."""
from __future__ import annotations

import json
import os
import re
from typing import Any

def normalize_slug(value: Any, *, fallback: str = "report") -> str:
    import unicodedata
    text = unicodedata.normalize("NFC", str(value or fallback)).strip()
    text = re.sub(r"[^0-9A-Za-z가-힣_.\-\s]+", "_", text)
    text = re.sub(r"[\s/\\]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


from pathlib import Path


def resolve_existing_path(path: str | Path) -> Path:
    """주어진 파일 경로가 NFD/NFC 정규화 차이 등으로 인해 존재 여부가 갈릴 때 자동 탐색하여 유효한 경로 반환."""
    import unicodedata
    p = Path(path)
    if p.exists():
        return p
    if p.parent.exists():
        norm_name = unicodedata.normalize("NFC", p.name)
        for child in p.parent.iterdir():
            if unicodedata.normalize("NFC", child.name) == norm_name:
                return child
    return p


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


def normalize_phase(phase: str) -> str:
    """하위 호환성 유지: 이전 v1, v2, v3, v3_final 등을 새로운 p1~p5 표준으로 매핑."""
    p = str(phase or "p1").lower().strip()
    if p in ("v1", "p1", "draft", "outline"):
        return "p1"
    if p in ("v2", "p2", "grounded", "material"):
        return "p2"
    if p in ("v3", "p3", "section", "expanded"):
        return "p3"
    if p in ("p4", "verify", "verifier", "review"):
        return "p4"
    if p in ("v3_final", "p5", "final", "merged"):
        return "p5"
    return p


def build_report_artifact_path(
    topic: str,
    phase: str,
    *,
    section_title: str | None = None,
    version: int | str | None = None,
    is_final: bool = False,
    base_dir: str = "workspace/report",
) -> str:
    """
    보고서 및 섹션별 단계(phase)와 버전(v1~vn)에 맞는 아티팩트 파일 경로 생성.

    Phases:
      - p1: 기초 초안 기획 (Drafting / Outline)
      - p2: 사용자 기초자료 반영 초안 (Material-grounded Draft)
      - p3: 각 챕터별 중간본 팽창 (Expanded chapter sections)
      - p4: 검증 및 정제 (Verification / Reviewer audit)
      - p5: 취합 및 최종 완성본 (Merged final report)

    Naming convention:
      - 일반 단계 산출물: {topic}_{phase}_v{version}.md (예: AI_동향_p1_v1.md, AI_동향_p2_v1.md)
      - 섹션별 산출물: {topic}_{phase}_{section}_v{version}.md (예: AI_동향_p3_1.1_기술개요_v1.md)
      - 최종 완성 산출물: {topic}_{phase}_final_v{version}.md (예: AI_동향_p5_final_v1.md)
    """
    safe_topic = normalize_slug(topic)
    norm_phase = normalize_phase(phase)

    # p5 이거나 명시적 is_final인 경우 또는 원래 phase가 final/v3_final인 경우 final 표기 활성화
    marked_final = is_final or norm_phase == "p5" or str(phase).lower().strip() in ("final", "v3_final")

    if version is not None:
        v_num = str(version).lstrip("vV")
        v_tag = f"v{v_num}" if v_num else "v1"
    else:
        v_tag = "v1"

    final_tag = "_final" if marked_final else ""

    if section_title:
        safe_title = normalize_slug(section_title)
        filename = f"{safe_topic}_{norm_phase}_{safe_title}{final_tag}_{v_tag}.md"
    else:
        filename = f"{safe_topic}_{norm_phase}{final_tag}_{v_tag}.md"

    return next_versioned_path(os.path.join(base_dir, filename))


def get_existing_artifact_versions(
    topic: str,
    phase: str,
    *,
    section_title: str | None = None,
    base_dir: str = "workspace/report",
) -> list[str]:
    """해당 주제 및 단계(phase)에서 이미 생성된 버전별 아티팩트 파일 경로 목록을 버전 순으로 반환."""
    if not os.path.exists(base_dir):
        return []
    safe_topic = normalize_slug(topic)
    norm_phase = normalize_phase(phase)

    if section_title:
        safe_title = normalize_slug(section_title)
        pattern = re.compile(rf"^{re.escape(safe_topic)}_{re.escape(norm_phase)}_{re.escape(safe_title)}(?:_final)?_v(\d+)\.md$")
    else:
        pattern = re.compile(rf"^{re.escape(safe_topic)}_{re.escape(norm_phase)}(?:_final)?_v(\d+)\.md$")

    matched = []
    for fname in os.listdir(base_dir):
        m = pattern.match(fname)
        if m:
            version_num = int(m.group(1))
            matched.append((version_num, os.path.join(base_dir, fname)))

    matched.sort(key=lambda x: x[0])
    return [p for _, p in matched]


def get_latest_artifact_path(
    topic: str,
    phase: str,
    *,
    section_title: str | None = None,
    base_dir: str = "workspace/report",
) -> str | None:
    """해당 주제 및 단계(phase)의 최신 버전 아티팩트 경로를 반환. 없으면 None."""
    versions = get_existing_artifact_versions(topic, phase, section_title=section_title, base_dir=base_dir)
    return versions[-1] if versions else None


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

