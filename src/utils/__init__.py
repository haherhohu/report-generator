"""Utility modules for file management, markdown processing, routing, and guards."""
from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
    normalize_slug,
    next_versioned_path,
)
from src.utils.final_guard import (
    should_reuse_or_create_final,
    get_final_path_for_title,
    read_text_if_exists,
)
from src.utils.markdown_tools import (
    normalize_markdown_headings,
    sanitize_intermediate_conclusions,
    clean_markdown_text,
)
from src.utils.glossary_parser import (
    extract_acronyms_from_markdown,
    extract_in_text_citations,
)
from src.utils.router import route_section_instruction

__all__ = [
    "save_file_append_only",
    "build_report_artifact_path",
    "register_artifact",
    "normalize_slug",
    "next_versioned_path",
    "should_reuse_or_create_final",
    "get_final_path_for_title",
    "read_text_if_exists",
    "normalize_markdown_headings",
    "sanitize_intermediate_conclusions",
    "clean_markdown_text",
    "extract_acronyms_from_markdown",
    "extract_in_text_citations",
    "route_section_instruction",
]

