"""Standalone Verifier Workflow: Parses large reports, verifies chunks, and reassembles losslessly."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from src.agents.verifier import verify_and_correct_chunk
from src.models.client import UnifiedModelClient
from src.tools.doc_chunker import split_markdown_by_headings, reassemble_chunks, DocumentChunk
from src.utils.markdown_cleaner import clean_and_format_markdown

logger = logging.getLogger("report_generator.verifier_graph")


class StandaloneVerifier:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.client = UnifiedModelClient("verifier", self.config.get("verifier", {}))
        self.max_shrink_ratio = float(self.config.get("max_shrink_ratio", 0.9))  # 최대 10% 축소 허용

    async def verify_document_async(
        self,
        input_path: str,
        output_path: str | None = None,
        strategic_stance: str = "",
        verification_level: str = "strict",
    ) -> dict[str, Any]:
        """대형 마크다운 보고서 단독 검증·교정 실행."""
        src_file = Path(input_path)
        if not src_file.exists():
            raise FileNotFoundError(f"검증 대상 문서를 찾을 수 없습니다: {input_path}")

        raw_text = src_file.read_text(encoding="utf-8")
        original_length = len(raw_text)
        logger.info(f"[StandaloneVerifier] 문서 로드 완료 ({original_length:,}자). 청크 분할 착수...")

        chunks = split_markdown_by_headings(raw_text, max_chunk_chars=4000)
        logger.info(f"[StandaloneVerifier] 총 {len(chunks)}개 청크로 분할 완료. 순차 검증 시작...")

        verified_chunks: list[DocumentChunk] = []
        logs: list[dict[str, Any]] = []

        prev_context = ""

        for idx, chunk in enumerate(chunks, 1):
            chunk_text = chunk.content
            meta = {
                "title": chunk.heading_title,
                "chapter_number": chunk.chapter_number,
                "section_number": chunk.section_number,
                "role_type": chunk.role_type,
            }

            allow_stance = chunk.role_type in ("implication", "final_conclusion", "core_strategy")

            # 검증 수행
            res = await verify_and_correct_chunk(
                content=chunk_text,
                metadata=meta,
                client=self.client,
                strategic_stance=strategic_stance,
                allow_stance=allow_stance,
            )

            corrected = res["corrected_content"]

            # 분량 보존 게이트키퍼: 요약으로 인한 10% 이상 축소 방지
            if len(corrected) < len(chunk_text) * self.max_shrink_ratio:
                logger.warning(
                    f"[Gatekeeper] 청크 {idx}번 '{chunk.heading_title}' 분량 급감 감지 "
                    f"({len(chunk_text)}자 -> {len(corrected)}자). 원본 분량 보존."
                )
                corrected = chunk_text

            chunk.content = corrected
            verified_chunks.append(chunk)

            # 이전 청크 마지막 문단 문맥 갱신
            prev_context = corrected[-500:] if len(corrected) > 500 else corrected

            logs.append({
                "chunk_id": chunk.chunk_id,
                "title": chunk.heading_title,
                "passed": res["passed"],
                "changelog": res["changelog"],
                "hallucinations": res.get("hallucinations", []),
                "stance_violations": res.get("stance_violations", []),
            })

            print(f"  [검증 완료 {idx}/{len(chunks)}] {chunk.heading_title[:30]}", flush=True)

        # 3. 무손실 재조립 및 최종 마크다운 서식 정제
        reassembled = reassemble_chunks(verified_chunks)
        final_cleaned = clean_and_format_markdown(reassembled)

        final_length = len(final_cleaned)
        logger.info(f"[StandaloneVerifier] 검증 및 재조립 완료 ({original_length:,}자 -> {final_length:,}자)")

        if not output_path:
            import re
            from src.utils.file_manager import build_report_artifact_path
            stem = src_file.stem
            clean_topic = re.sub(r"_(?:p\d+|v\d+|final|verified)+.*$", "", stem)
            target_path = build_report_artifact_path(clean_topic, "p5", is_final=True, base_dir="workspace/report")
            out_file = Path(target_path)
        else:
            out_file = Path(output_path)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(final_cleaned, encoding="utf-8")
        logger.info(f"[StandaloneVerifier] 최종 검증본 마크다운 저장 완료: {out_file}")

        from src.tools.hwpx_exporter import export_markdown_to_hwpx
        hwpx_path = export_markdown_to_hwpx(out_file)
        if hwpx_path:
            logger.info(f"[StandaloneVerifier] 최종 HWPX 표준 변환 완료: {hwpx_path}")

        return {
            "output_path": str(out_file),
            "hwpx_path": hwpx_path,
            "original_length": original_length,
            "final_length": final_length,
            "total_chunks": len(chunks),
            "verification_logs": logs,
        }

    def verify_document(
        self,
        input_path: str,
        output_path: str | None = None,
        strategic_stance: str = "",
        verification_level: str = "strict",
    ) -> dict[str, Any]:
        """동기 호출 래퍼."""
        return asyncio.run(
            self.verify_document_async(
                input_path=input_path,
                output_path=output_path,
                strategic_stance=strategic_stance,
                verification_level=verification_level,
            )
        )
