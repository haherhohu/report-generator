"""Final report shield to prevent redundant LLM token consumption and infinite loops."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

def normalize_report_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_matching_history_entries(state: dict, *, title: str, include_final: bool = True) -> list[dict]:
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


def get_final_path_for_title(state: dict, *, title: str) -> str | None:
    lookup = normalize_report_key(title)
    for entry in state.get("artifact_history", []) or []:
        entry_title = entry.get("title", "")
        if normalize_report_key(entry_title) == lookup and "final" in str(entry.get("type", "")).lower():
            path = entry.get("path")
            if path and os.path.exists(path):
                return path
    return None


def read_text_if_exists(path: str | None) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _dedupe_paragraphs(parts: list[str]) -> list[str]:
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


def is_valid_quality_content(content: str | None) -> bool:
    """내용이 보고서/자료조사로서 최소한의 품질(서술 본문 및 유효 분량)을 갖추었는지 판별."""
    if not content:
        return False
    text = content.strip()
    if len(text) < 150:
        return False

    # 결함 및 에러/실패 문구 패턴 검출
    error_patterns = [
        "기존 보고서가 없어 빈 문서로 생성됨",
        "SSL 인증 오류로 인해",
        "데이터를 가져오지 못함",
        "usable한 사실이나 통계가 부재함",
        "인사이트를 제시하지 못함",
        "재검색을 수행하여 정확한 데이터를 확보할 것임",
        "(no items)",
    ]
    if any(err in text for err in error_patterns):
        return False

    # 표(|), 헤딩(#), 단순 출처 섹션을 제외하고 실질 서술형 텍스트(불릿 서술 포함) 길이 검사
    lines = text.splitlines()
    narrative_chars = 0
    in_references_section = False

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        if line_s.startswith("#") and "참고 출처" in line_s:
            in_references_section = True
            continue
        if in_references_section:
            if line_s.startswith("#"):
                in_references_section = False
            else:
                continue

        # 표 기호 및 헤딩 기호 제외
        if line_s.startswith(("|", ":---")):
            continue
        if line_s.startswith("#"):
            continue

        # 불릿(*, -, >) 및 숫자 번호 기호 제거 후 실제 본문 텍스트 길이 측정
        cleaned_line = re.sub(r"^[\*\-\>\d\.\s]+", "", line_s).strip()
        narrative_chars += len(cleaned_line)

    # 실질 서술형 본문이 80자 미만이면 '표만 덜렁 있거나 내용 없는 부실 본문'으로 판정
    if narrative_chars < 80:
        return False

    return True


def clean_junk_reference_files(
    reference_dir: str | Path = "workspace/reference",
    archive_dir: str | Path | None = "workspace/reference/.junk_archive",
) -> list[dict[str, Any]]:
    """함량미달/결함 조사보고서 파일들을 스캔하여 격리 아카이빙 또는 정리."""
    ref_path = Path(reference_dir)
    if not ref_path.exists():
        return []

    target_archive = Path(archive_dir) if archive_dir else None
    if target_archive:
        target_archive.mkdir(parents=True, exist_ok=True)

    cleaned_items = []
    for f in sorted(list(ref_path.glob("*.md"))):
        # 아카이브 폴더 내 파일은 스킵
        if target_archive and target_archive in f.parents:
            continue

        content = f.read_text(encoding="utf-8", errors="ignore")
        if not is_valid_quality_content(content):
            item_info = {
                "filename": f.name,
                "length": len(content.strip()),
                "path": str(f),
            }
            if target_archive:
                dest = target_archive / f.name
                f.rename(dest)
                item_info["action"] = f"archived to {dest}"
            else:
                f.unlink(missing_ok=True)
                item_info["action"] = "deleted"

            cleaned_items.append(item_info)

    return cleaned_items



def build_final_bundle_document(title: str, paths: list[str], *, summary_only: bool = False) -> str:
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
        # 단편적인 표 조각만 남지 않도록 의미 있는 서술 단락을 우선 반영
        meaningful_blocks = [b for b in unique_blocks if len(b.strip()) >= 40]
        selected = meaningful_blocks[:8] if meaningful_blocks else unique_blocks[:5]
        body = "\n\n---\n\n".join(selected)
    else:
        body = "\n\n---\n\n".join(unique_blocks[:35])

    return f"# {title} 최종본\n\n{body}\n"


def should_reuse_or_create_final(
    state: dict,
    *,
    title: str,
    related_paths: list[str] | None = None,
    duplicate_threshold: int = 5,
    summary_only: bool = False,
    require_quality: bool = False,
) -> dict[str, Any]:
    """동일한 키워드/섹션이 duplicate_threshold(기본 5회) 이상 생성되었을 때 Final본을 생성하거나 기존 Final본을 재사용."""
    final_path = get_final_path_for_title(state, title=title)
    if final_path:
        content = read_text_if_exists(final_path)
        # require_quality일 때 기존 Final이 부실한 표만 있거나 불량이면 재사용 거부
        if not require_quality or is_valid_quality_content(content):
            return {
                "path": final_path,
                "content": content,
                "used_final": True,
                "triggered_duplicate": False,
            }

    matches = [
        item for item in state.get("artifact_history", []) or []
        if normalize_report_key(item.get("title", "")) == normalize_report_key(title)
    ]
    if require_quality:
        matches = [
            item for item in matches
            if item.get("path") and is_valid_quality_content(read_text_if_exists(item.get("path")))
        ]

    if len(matches) >= duplicate_threshold:
        final_content = build_final_bundle_document(
            title,
            [item.get("path") for item in matches if item.get("path")],
            summary_only=summary_only,
        )
        return {
            "path": None,
            "content": final_content,
            "used_final": False,
            "triggered_duplicate": True,
        }

    if related_paths:
        unique_paths = []
        seen = set()
        for p in related_paths:
            if p and p not in seen:
                seen.add(p)
                if not require_quality or is_valid_quality_content(read_text_if_exists(p)):
                    unique_paths.append(p)
        if len(unique_paths) >= duplicate_threshold:
            final_content = build_final_bundle_document(
                title, unique_paths, summary_only=summary_only
            )
            return {
                "path": None,
                "content": final_content,
                "used_final": False,
                "triggered_duplicate": True,
            }

    return {
        "path": None,
        "content": None,
        "used_final": False,
        "triggered_duplicate": False,
    }


