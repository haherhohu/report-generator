import os
import re
from pathlib import Path


def normalize_report_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_matching_history_entries(state, *, title, include_final=True):
    entries = []
    lookup = normalize_report_key(title)
    for entry in state.get("artifact_history", []) or []:
        entry_title = entry.get("title", "")
        if normalize_report_key(entry_title) != lookup:
            continue
        if not include_final and "final" in str(entry.get("type", "")).lower():
            continue
        entries.append(entry)
    return entries


def get_final_path_for_title(state, *, title):
    lookup = normalize_report_key(title)
    for entry in state.get("artifact_history", []) or []:
        entry_title = entry.get("title", "")
        if normalize_report_key(entry_title) == lookup and "final" in str(entry.get("type", "")).lower():
            path = entry.get("path")
            if path and os.path.exists(path):
                return path
    return None


def read_text_if_exists(path):
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _dedupe_paragraphs(parts):
    seen = set()
    ordered = []
    for block in parts:
        cleaned = re.sub(r"\s+", " ", str(block or "")).strip()
        if not cleaned:
            continue
        norm = cleaned.lower()
        if norm in seen:
            continue
        seen.add(norm)
        ordered.append(cleaned)
    return ordered


def build_final_bundle_document(title, paths, *, summary_only=False):
    docs = []
    for path in paths:
        content = read_text_if_exists(path)
        if content:
            docs.append(content)

    if not docs:
        return f"# {title} 최종본\n\n기존 보고서가 없어 빈 문서로 생성됨.\n"

    blocks = []
    for doc in docs:
        for section in re.split(r"\n\s*\n", doc):
            paragraph = section.strip()
            if paragraph:
                blocks.append(paragraph)

    unique_blocks = _dedupe_paragraphs(blocks)
    if summary_only:
        selected = []
        for block in unique_blocks:
            if len(block) < 200:
                selected.append(block)
            elif len(block) > 600:
                selected.append(block[:600])
            else:
                selected.append(block)
        body = "\n\n---\n\n".join(selected[:8])
    else:
        body = "\n\n---\n\n".join(unique_blocks[:30])

    return f"# {title} 최종본\n\n{body}\n"


def should_reuse_or_create_final(state, *, title, related_paths, duplicate_threshold=5, summary_only=False):
    final_path = get_final_path_for_title(state, title=title)
    if final_path:
        return {"path": final_path, "content": read_text_if_exists(final_path), "used_final": True}

    matches = [
        item for item in state.get("artifact_history", []) or []
        if normalize_report_key(item.get("title", "")) == normalize_report_key(title)
    ]
    if len(matches) >= duplicate_threshold:
        final_content = build_final_bundle_document(title, [item.get("path") for item in matches if item.get("path")], summary_only=summary_only)
        return {"path": None, "content": final_content, "used_final": False, "triggered_duplicate": True}

    if related_paths:
        unique_paths = []
        seen = set()
        for path in related_paths:
            if path in seen:
                continue
            seen.add(path)
            unique_paths.append(path)
        if len(unique_paths) >= duplicate_threshold:
            final_content = build_final_bundle_document(title, unique_paths, summary_only=summary_only)
            return {"path": None, "content": final_content, "used_final": False, "triggered_duplicate": True}

    return {"path": None, "content": None, "used_final": False, "triggered_duplicate": False}
