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


def _build_grounded_bibliography(state: ReportState, full_body_str: str) -> list[str]:
    """
    사용자 지침 3단계 엄격 원칙에 따른 실증 참고문헌 빌더:
    1. 웹 검색에서 실제 수집된 레코드(verified_references)
    2. 사용자가 직접 제공한 원시 자료 (시스템 임시 파일 research_*.md 제외)
    3. 둘 다 없으면 허위 출처를 일체 만들지 않음
    """
    import re
    from src.utils.glossary_parser import extract_in_text_citations

    final_refs: list[str] = []
    seen: set[str] = set()

    seen_files: set[str] = set()

    def _add(ref_str: str):
        cleaned = re.sub(r"\s+", " ", ref_str).strip()
        if not cleaned:
            return
        # 가짜/더미 출처 필터링
        dummy_markers = (
            "국가 공식 통계 포털",
            "자체 분석 및 국책연구원",
            "국가 공식 데이터베이스",
            "공공기관 정책 백서 및 국내외 산업통계",
        )
        if any(marker in cleaned for marker in dummy_markers):
            return

        # 제공 기초자료 접두어 통일 및 파일명 기준 중복 차단
        for prefix in ("제공 원시 기초자료:", "제공 기초자료:"):
            if cleaned.startswith(prefix):
                fname = cleaned[len(prefix):].strip()
                cleaned = f"제공 기초자료: {fname}"
                if fname in seen_files:
                    return
                seen_files.add(fname)
                break

        if cleaned not in seen:
            seen.add(cleaned)
            final_refs.append(cleaned)


    # 1순위: verified_references (실제 수집된 웹 검색 레코드)
    verified_records = state.get("verified_references", [])
    for rec in verified_records:
        if isinstance(rec, dict):
            title = rec.get("title", "").strip()
            href = rec.get("href", "").strip()
            if title and href:
                _add(f"{title} ({href})")
            elif title:
                _add(title)

    # collected_references에서 실제 불릿 항목 파싱
    for ref_group in state.get("collected_references", []):
        for line in str(ref_group).splitlines():
            line_s = line.strip()
            if line_s.startswith(("- ", "* ")):
                content = line_s[2:].strip()
                _add(content)

    # 2순위: 사용자가 직접 제공한 원시 기초자료 파일명
    raw_sources = state.get("source_materials", [])
    for sm in raw_sources:
        if isinstance(sm, dict):
            fname = sm.get("filename", "")
            # 시스템 내부 생성 파일(research_*, _final.md) 철저 배제
            if fname and not fname.startswith("research_") and not fname.endswith("_final.md"):
                _add(f"제공 원시 기초자료: {fname}")

    # 본문 내 인용 중 실제 URL/학술 문헌 패턴만 선별
    for cite in extract_in_text_citations(full_body_str):
        if any(marker in cite for marker in ("http://", "https://", "「", "vol", "doi", "issn", "법률 제")):
            _add(cite)

    return final_refs


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

    # 3. 실증 기반 참고문헌 구성 (사용자 3단계 엄격 원칙 적용)
    grounded_references = _build_grounded_bibliography(state, full_body_str)

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
    if grounded_references:
        for idx, ref in enumerate(grounded_references[:30], 1):
            doc_lines.append(f"{idx}. {ref}")
    else:
        doc_lines.append("※ 본 보고서는 제공된 기획 지침 및 내부 분석 프레임워크를 기반으로 작성되었으며, 별도의 외부 인용 문헌이 존재하지 않습니다.")

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
        # 본문에서 약어가 추출되지 않은 경우 중립적인 일반 연구/산업 표준 약어만 표기
        from src.utils.glossary_parser import KNOWN_ACRONYMS
        neutral_keys = ("TRL", "CAGR", "R&D", "M&A", "API", "IP")
        for k in neutral_keys:
            if k in KNOWN_ACRONYMS:
                eng, kor = KNOWN_ACRONYMS[k]
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

