"""Merger Agent: Lossless sequential compilation, centralized bibliography, and acronym glossary generation."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import yaml

from src.core.report_types import get_report_type_config
from src.core.state import ReportState
from src.models.fallback_engine import generate_fallback_citations_glossary
from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
)
from src.utils.glossary_parser import (
    extract_acronyms_from_markdown,
    extract_in_text_citations,
)

logger = logging.getLogger("report_generator.agents.merger")


def _load_config() -> dict:
    for path in ("config/agents_config.yaml", "poc/config/agents_config.yaml"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def run_merger(state: ReportState) -> ReportState:
    """Step 10: 전체 본문 순차 무손실 병합, 통합 참고문헌 및 총괄 영문 약어표 합성."""
    topic = state["topic"]
    report_type = state.get("report_type", "market_tech_trend")
    direction = state.get("direction", "")
    type_config = get_report_type_config(report_type, direction=direction)

    logger.info(f"[Merger] '{topic}' 최종 보고서 취합 및 통합 부록/약어표 생성 착수...")

    existing_final = state.get("final_report_path")
    if existing_final and os.path.exists(existing_final):
        logger.info(f"[Merger] -> [재사용] 기존 최종 보고서 사용 ({existing_final})")
        return state

    sections = state.get("expanded_sections", [])
    if not sections:
        raise ValueError("[Merger] 병합할 챕터 데이터가 없습니다.")

    import re

    # 1. 챕터/섹션 순서 정렬 (숫자 기반 정밀 정렬)
    def _sort_key(s: dict) -> tuple[int, int]:
        chap_str = str(s.get("chapter_number", "")).strip()
        sec_str = str(s.get("section_number", "")).strip()

        roman_map = {"Ⅰ": 1, "Ⅱ": 2, "Ⅲ": 3, "Ⅳ": 4, "Ⅴ": 5, "Ⅵ": 6, "Ⅶ": 7, "Ⅷ": 8, "Ⅸ": 9, "Ⅹ": 10}
        chap_idx = 99
        for r_k, r_v in roman_map.items():
            if r_k in chap_str:
                chap_idx = r_v
                break
        if chap_idx == 99:
            nums = [int(n) for n in re.findall(r"\d+", chap_str)]
            chap_idx = nums[0] if nums else 99

        sec_nums = [int(n) for n in re.findall(r"\d+", sec_str)]
        sec_idx = sec_nums[0] if sec_nums else 0

        return (chap_idx, sec_idx)

    sorted_sections = sorted(sections, key=_sort_key)

    # 2. 본문 무손실 결합 (요약 및 가감 일절 배제)
    doc_lines = [
        f"# {topic}",
        "",
        "> **【보고서 개요】**",
        f"> - 보고서 유형: {type_config.label}",
        f"> - 타겟 관점: {state.get('target_perspective', '공공 및 연구기관')}",
        "> - 편제 규격: 국가전략 대형 기획 및 산업 인텔리전스 표준",
        "",
        "---",
        "",
    ]

    body_text_accumulator = []
    for sec in sorted_sections:
        c = sec.get("content", "").strip()
        if c:
            doc_lines.append(c)
            doc_lines.append("\n---\n")
            body_text_accumulator.append(c)

    full_body_str = "\n".join(body_text_accumulator)

    # 3. 본문 내 인용 및 실제 수집된 출처 취합
    collected_refs = list(state.get("collected_references", []))
    in_text_sources = extract_in_text_citations(full_body_str)

    # 원본 파일명 추가
    source_files = [
        f"제공 원시 기초자료: {item.get('filename')}"
        for item in state.get("source_materials", []) if isinstance(item, dict) and item.get("filename")
    ]

    combined_references: list[str] = []
    seen_refs = set()
    for ref_group in (collected_refs + in_text_sources + source_files):
        cleaned_ref = str(ref_group).strip()
        if cleaned_ref and cleaned_ref not in seen_refs:
            seen_refs.add(cleaned_ref)
            combined_references.append(cleaned_ref)

    # 4. 본문 전체에서 영문 약어(Acronym) 자동 추출
    extracted_acronyms = extract_acronyms_from_markdown(full_body_str)

    # 5. 통합 부록/참고문헌/약어표 생성
    last_chapter = type_config.chapters[-1]
    appendix_header = f"## {last_chapter.chapter_number} {last_chapter.title}"

    doc_lines.append(appendix_header)
    doc_lines.append("")

    # 참고문헌 블록
    doc_lines.append("### 1. 국내외 공식 참고문헌 및 데이터 출처 총괄 목록")
    doc_lines.append("")
    if combined_references:
        for idx, ref in enumerate(combined_references[:25], 1):
            doc_lines.append(f"{idx}. {ref}")
    else:
        doc_lines.append("1. 국가 공식 통계 포털 및 수집된 정책 실태조사 문헌 일체.")

    doc_lines.append("")
    doc_lines.append("---")
    doc_lines.append("")

    # 영문 약어표 블록
    doc_lines.append("### 2. 보고서 수록 주요 영문 약어(Acronym) 및 전문용어 총괄 정의표 (Glossary)")
    doc_lines.append("")
    doc_lines.append("| 영문 약어 (Acronym) | 영문 원어 (Full Term) | 한글 공식 명칭 및 핵심 정의 |")
    doc_lines.append("| :--- | :--- | :--- |")

    if extracted_acronyms:
        for acr in extracted_acronyms:
            doc_lines.append(f"| **{acr['acronym']}** | {acr['full_term']} | {acr['definition']} |")
    else:
        # 기본 사전 데이터 표기
        from src.utils.glossary_parser import KNOWN_ACRONYMS
        for k, (eng, kor) in list(KNOWN_ACRONYMS.items())[:8]:
            doc_lines.append(f"| **{k}** | {eng} | {kor} |")

    doc_lines.append("")

    final_merged_text = "\n".join(doc_lines).strip() + "\n"

    # 6. 최종 파일 저장 (Append-only)
    file_path = build_report_artifact_path(topic, "v3_final")
    saved_final_path = save_file_append_only(file_path, final_merged_text)
    register_artifact(state, artifact_type="final-report", title="최종 완성 보고서", path=saved_final_path)

    state["final_report_path"] = saved_final_path
    logger.info(f"[Merger] ✅ 최종 보고서 취합 완료! 저장 경로: {saved_final_path}")
    logger.info(f"[Merger] 총 글자 수: {len(final_merged_text):,}자, 총 줄 수: {len(doc_lines):,}줄")

    return state

