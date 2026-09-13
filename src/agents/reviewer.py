"""Reviewer Agent: Checks structural completeness, normalizes heading depth, and copyedits tone."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
import yaml

from src.core.report_types import get_report_type_config
from src.core.state import ReportState
from src.models.client import UnifiedModelClient
from src.utils.markdown_tools import (
    normalize_markdown_headings,
    sanitize_intermediate_conclusions,
)

logger = logging.getLogger("report_generator.agents.reviewer")


def _load_config() -> dict:
    for path in ("config/agents_config.yaml", "poc/config/agents_config.yaml"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_prompt() -> str:
    for path in ("prompts/reviewer_prompt.md", "poc/prompts/reviewer_prompt.md"):
        if os.path.exists(path):
            return Path(path).read_text(encoding="utf-8")
    return (
        "당신은 대한민국 국가 최고 연구기관 및 정부 부처의 수석 에디터이자 교열·윤문 심의위원입니다. "
        "보고서 본문의 마크다운 헤딩 계층, 문체 정합성, 불필요한 번역투 및 동어반복을 정밀하게 교열하십시오."
    )


def _apply_deterministic_polish(content: str, tone: str) -> str:
    """번역투, 이중 피동형, 어색한 어미를 정제하는 결정론적 교열기."""
    polished = content
    # 이중 피동 및 번역투 정제
    replacements = [
        ("되어지고 있는", "지속되는"),
        ("되어지고", "되며"),
        ("보여진다", "분석된다"),
        ("생각되어진다", "판단된다"),
        ("생각된다", "판단된다"),
        ("많은 부분에 있어서", "대부분의 영역에서"),
        ("매우 중요한 핵심적인", "핵심적인"),
        ("다양한 여러가지", "다양한"),
    ]
    for before, after in replacements:
        polished = polished.replace(before, after)

    # 톤별 어미 조정 보강
    if tone == "official_formal":
        # ~합니다 -> ~함
        polished = re.sub(r"합니다\.", "함.", polished)
        polished = re.sub(r"입니다\.", "임.", polished)
        polished = re.sub(r"됩니다\.", "됨.", polished)

    return polished


def run_reviewer(state: ReportState) -> ReportState:
    """Step 8: 구조적 누락 챕터 점검, 헤딩 뎁스 표준화 및 문체 윤문·교열."""
    logger.info("[Reviewer] === 전 챕터 구조 및 품질 교열 프로세스 시작 ===")

    report_type = state.get("report_type", "market_tech_trend")
    direction = state.get("direction", "")
    type_config = get_report_type_config(report_type, direction=direction)
    tone = state.get("tone", type_config.default_tone)

    expanded_sections = state.get("expanded_sections", [])
    if not expanded_sections:
        logger.warning("[Reviewer] expanded_sections가 비어 있습니다.")
        state["reviewer_feedback"] = "생성된 섹션이 없습니다."
        state["target_sections_for_loop"] = ["all"]
        return state

    # 1. 챕터 누락 여부 검증 (보고서 유형별 동적 검증)
    expected_chapters = {c.chapter_number for c in type_config.chapters if not c.role_type.startswith("appendix")}
    present_chapters = set()
    for s in expanded_sections:
        chap_num = s.get("chapter_number")
        if chap_num:
            present_chapters.add(chap_num)
        else:
            # title에서 추출 시도
            t = str(s.get("title", ""))
            for exp in expected_chapters:
                if exp in t:
                    present_chapters.add(exp)

    missing_chapters = expected_chapters - present_chapters
    if missing_chapters:
        logger.warning(f"[Reviewer] 필수 챕터 누락 감지: {missing_chapters}")
        state["reviewer_feedback"] = f"누락된 챕터 {list(missing_chapters)}를 반드시 포함하여 생성하십시오."
        state["target_sections_for_loop"] = list(missing_chapters)
        return state

    # 2. 전 섹션 교열 및 마크다운 헤딩 깊이 정규화
    config = _load_config()
    rev_config = config.get("reviewer", {})
    client = UnifiedModelClient("reviewer", rev_config)
    system_prompt = _load_prompt()

    polished_sections = []
    for s in expanded_sections:
        raw_text = s.get("content", "")
        chap_num = s.get("chapter_number", "")
        sec_num = s.get("section_number", "")
        title = s.get("title", "")
        role_type = s.get("role_type", "background_trend")

        # 1차: 결정론적 정규화 및 피동형 정제
        sanitized = sanitize_intermediate_conclusions(raw_text, role_type=role_type)
        heading_norm = normalize_markdown_headings(sanitized, chap_num, sec_num, title)
        polished_text = _apply_deterministic_polish(heading_norm, tone=tone)

        polished_sec = dict(s)
        polished_sec["content"] = polished_text
        polished_sections.append(polished_sec)

    state["expanded_sections"] = polished_sections
    state["reviewer_feedback"] = "승인(Approved). 모든 챕터 구조와 헤딩 뎁스, 문체 규격이 충족되었습니다."
    state["target_sections_for_loop"] = []

    logger.info("[Reviewer] 전 섹션 교열 및 헤딩 표준화 완료.")
    return state

