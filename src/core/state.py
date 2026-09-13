"""State definitions for the LangGraph report generation pipeline."""
from __future__ import annotations

from typing import TypedDict, NotRequired, Any, Literal

class SectionItem(TypedDict):
    section_id: str
    chapter_number: str       # 예: "1장", "Ⅰ"
    section_number: str       # 예: "1절", "1."
    title: str
    target_pages: int
    target_chars: int
    key_topics: list[str]
    planned_tables: list[str]
    planned_case_studies: list[str]
    content: NotRequired[str]
    draft_path: NotRequired[str]
    status: NotRequired[Literal["pending", "completed", "skipped"]]

class ChapterItem(TypedDict):
    chapter_id: str
    chapter_number: str       # 예: "1장", "Ⅰ"
    title: str
    target_pages: int
    target_chars: int
    role_type: str            # "intro" | "background_trend" | "empirical_case" | "core_strategy" | "action_plans" | "roadmap" | "implication" | "final_conclusion" | "appendix_facts" | "appendix_references"
    is_core_chapter: bool
    allowed_conclusions: bool
    sections: list[SectionItem]

class ReportState(TypedDict):
    # 기본 메타데이터
    topic: str
    direction: str | list[str]
    target_perspective: str
    report_type: str          # "research_policy" | "market_tech_trend" | "global_market_expansion"
    tone: str                 # "official_formal" (~함, ~임) | "objective_smooth" (~한다, ~이다)
    target_pages: int
    target_chars: int
    is_blank_slate: bool

    # 입력 자료 및 리서치 아카이브
    source_materials: NotRequired[list[dict[str, Any]]]
    reference_summaries: NotRequired[list[dict[str, Any]]]
    reference_paths: NotRequired[list[str]]
    keywords: NotRequired[list[str]]
    keyword_search_cache: NotRequired[dict[str, str]]
    collected_references: NotRequired[list[str]]

    # 목차 및 본문 상태
    chapters: NotRequired[list[ChapterItem]]
    sections: NotRequired[list[dict[str, Any]]]
    expanded_sections: NotRequired[list[dict[str, Any]]]
    completed_sections: NotRequired[list[str]]

    # 루프 및 분량 통제
    loop_count: NotRequired[int]
    max_loops: NotRequired[int]
    max_concurrency: NotRequired[int]
    target_core_min_length: NotRequired[int]
    target_total_min_length: NotRequired[int]
    target_sections_for_loop: NotRequired[list[Any]]
    reviewer_feedback: NotRequired[str]
    next_step: NotRequired[str]

    # 파일 및 산출물 경로
    foundation_report_path: NotRequired[str]
    final_report_path: NotRequired[str]
    section_final_paths: NotRequired[dict[str, str]]
    report_final_paths: NotRequired[dict[str, str]]
    artifact_history: NotRequired[list[dict[str, Any]]]
    active_version: NotRequired[str]
    global_directive: NotRequired[str]

