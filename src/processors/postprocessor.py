"""Unified Report Post-Processor.

Consolidates all fragmented cleaners and hotfixes into a single cohesive pipeline:
1. Base Markdown Sanitation: CoT stripping, table nesting escape, HTML table conversion.
2. Fact & Policy Stance Alignment: Saemangeum/Physical AI RAMS factual grounding, aerospace coding purge.
3. Fictitious Entity & Meta Leak Purge: KURA, fictitious MOUs, internal reference leaks, regex artifact cleanup.
4. Tables & Figures Formatting: Line breaks separation before captions, 1x1 callout boxes, cell centering.
5. Executive Summary & TOC Integrity: Config-driven 5-line summary, 1:1 TOC-caption synchronization.
6. Paragraph Indentation & Final HWPX Readiness.
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import re
from pathlib import Path
from typing import Any

from src.utils.markdown_cleaner import (
    clean_table_nesting,
    strip_cot_and_system_residue,
    strip_continuation_headings,
    sanitize_broken_tags,
    convert_html_tables_to_markdown,
    generate_executive_summary,
)

logger = logging.getLogger("report_generator.processors.postprocessor")


class ReportPostProcessor:
    """단일 진입점으로 통합된 고성능 국책/공공 보고서 후처리 엔진."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def process(self, text: str, topic: str = "") -> str:
        """마크다운 원문을 수신하여 6단계 파이프라인을 거쳐 HWPX 공공 규격 적합 마크다운으로 최종 정제."""
        if not text:
            return ""

        logger.info("[PostProcessor] === 통합 보고서 후처리 파이프라인 가동 ===")
        processed = text

        # Step 1: 기초 마크다운 문법 및 CoT 사고과정 완전 박멸
        processed = clean_table_nesting(processed)
        processed = strip_cot_and_system_residue(processed)
        processed = strip_continuation_headings(processed)
        processed = sanitize_broken_tags(processed)
        processed = convert_html_tables_to_markdown(processed)

        # Step 2: 5대 사실성 및 정책 스탠스 핫픽스
        try:
            from src.tools.fact_stance_hotfix import clean_fact_stance_all
            processed, _ = clean_fact_stance_all(processed)
        except Exception as e:
            logger.warning(f"[PostProcessor] fact_stance_hotfix 적용 중 경고: {e}")

        # Step 3: 비공개 내부문서 및 가상 조직/MOU(KURA 등), 정규식 아티팩트 전수 박멸
        try:
            from src.tools.apply_deep_purge_v3 import clean_draft_proposals_and_fictitious_entities
            processed = clean_draft_proposals_and_fictitious_entities(processed)
        except Exception as e:
            logger.warning(f"[PostProcessor] deep_purge 적용 중 경고: {e}")

        # Step 4: 표 및 그림 서식 정규화 (캡션 앞 개행 분리, 1x1 콜아웃 박스)
        try:
            from src.tools.apply_user_feedback_v2 import (
                normalize_all_tables_v2,
                normalize_all_figures_v2,
            )
            processed = normalize_all_tables_v2(processed)
            processed = normalize_all_figures_v2(processed)
        except Exception as e:
            logger.warning(f"[PostProcessor] user_feedback_v2 표/그림 정규화 중 경고: {e}")

        # Step 5: 사용자 피드백 18대 품질 혁신 정제 엔진 가동
        try:
            from src.processors.report_quality_enhancer import apply_all_quality_enhancements
            processed = apply_all_quality_enhancements(processed)
        except Exception as e:
            logger.warning(f"[PostProcessor] report_quality_enhancer 적용 중 경고: {e}")

        # Step 6: 제목 및 Executive Summary (5줄 요약문) 무결성 확보
        processed = self._ensure_executive_summary(processed, topic=topic)

        # 공백 개행 정돈 (최대 2줄 연속 빈 줄)
        processed = re.sub(r"\n{3,}", "\n\n", processed).strip() + "\n"

        logger.info(f"[PostProcessor] ✅ 후처리 완료 (최종 분량: {len(processed):,}자)")
        return processed

    def _ensure_executive_summary(self, doc_text: str, topic: str = "") -> str:
        """문서 최상단에 Executive Summary 인용구가 없으면 제목을 분석하여 자동 주입."""
        if "> **【Executive Summary: 핵심 요약】**" in doc_text:
            return doc_text

        lines = doc_text.splitlines()
        first_h1_idx = -1
        doc_title = topic

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                first_h1_idx = idx
                if not doc_title:
                    doc_title = stripped.lstrip("# ").strip()
                break

        if not doc_title:
            doc_title = "국책 기술 및 정책 동향 보고서"

        body_snippet = "\n".join(lines[first_h1_idx + 1:first_h1_idx + 100]) if first_h1_idx != -1 else doc_text[:3000]
        exec_summary = generate_executive_summary(doc_title, body_snippet)

        if first_h1_idx != -1:
            # H1 바로 다음 또는 빈 줄 뒤에 삽입
            insert_pos = first_h1_idx + 1
            while insert_pos < len(lines) and lines[insert_pos].strip() == "":
                insert_pos += 1
            lines.insert(insert_pos, "")
            lines.insert(insert_pos + 1, exec_summary)
            lines.insert(insert_pos + 2, "")
            lines.insert(insert_pos + 3, "---")
            lines.insert(insert_pos + 4, "")
            return "\n".join(lines)
        else:
            return f"# {doc_title}\n\n{exec_summary}\n\n---\n\n{doc_text}"


_DEFAULT_PROCESSOR = ReportPostProcessor()


def process_report_markdown(text: str, topic: str = "") -> str:
    """간편 함수형 진입점."""
    return _DEFAULT_PROCESSOR.process(text, topic=topic)


def process_report_file(file_path: str | Path, output_path: str | Path | None = None) -> Path:
    """단일 마크다운 파일 후처리 실행 및 저장."""
    src = Path(file_path)
    if not src.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {src}")

    text = src.read_text(encoding="utf-8")
    cleaned = process_report_markdown(text)

    dest = Path(output_path) if output_path else src
    dest.write_text(cleaned, encoding="utf-8")
    logger.info(f"후처리 저장 완료: {dest}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Report Post-Processor CLI")
    parser.add_argument("--file", help="단일 마크다운 파일 경로")
    parser.add_argument("--dir", help="일괄 처리할 디렉터리 경로")
    parser.add_argument("--pattern", default="*.md", help="디렉터리 파일 패턴 (기본: *.md)")
    parser.add_argument("--inplace", action="store_true", help="원본 파일 덮어쓰기")
    parser.add_argument("--out", help="출력 파일 경로")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

    if args.file:
        out_path = args.file if args.inplace else args.out
        process_report_file(args.file, output_path=out_path)
    elif args.dir:
        files = glob.glob(os.path.join(args.dir, args.pattern))
        logger.info(f"총 {len(files)}개 파일 일괄 후처리 시작...")
        for f in sorted(files):
            process_report_file(f, output_path=f if args.inplace else None)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
