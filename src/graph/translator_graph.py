"""Standalone Translator Workflow: Long-form AST chunked translation with glossary enforcement."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from src.agents.translator import translate_chunk_async
from src.models.client import UnifiedModelClient
from src.tools.doc_chunker import split_markdown_by_headings, DocumentChunk
from src.tools.glossary_manager import GlossaryManager
from src.utils.markdown_cleaner import clean_and_format_markdown

logger = logging.getLogger("report_generator.translator_graph")


class StandaloneTranslator:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.client = UnifiedModelClient("translator", self.config.get("translator", {}))
        self.glossary_manager = GlossaryManager()
        self.max_concurrency = int(self.config.get("max_concurrency", 4))

    async def translate_document_async(
        self,
        input_path: str,
        output_path: str | None = None,
        source_lang: str = "en",
        target_lang: str = "ko",
        custom_glossary_path: str | None = None,
    ) -> dict[str, Any]:
        """초장문 보고서 분할 번역 파이프라인 가동."""
        src_file = Path(input_path)
        if not src_file.exists():
            raise FileNotFoundError(f"번역 대상 문서를 찾을 수 없습니다: {input_path}")

        if custom_glossary_path:
            self.glossary_manager.load_glossary_file(custom_glossary_path)

        raw_text = src_file.read_text(encoding="utf-8")
        original_length = len(raw_text)
        logger.info(f"[StandaloneTranslator] 문서 로드 완료 ({original_length:,}자). 용어집 스캔 및 청크 분할...")

        chunks = split_markdown_by_headings(raw_text, max_chunk_chars=3500)
        logger.info(f"[StandaloneTranslator] 총 {len(chunks)}개 청크로 분할. 번역 착수...")

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _translate_single(chunk: DocumentChunk, idx: int) -> DocumentChunk:
            async with semaphore:
                relevant_terms = self.glossary_manager.scan_and_extract_terms(chunk.content)
                glossary_inst = self.glossary_manager.build_glossary_prompt_instruction(relevant_terms)

                translated_text = await translate_chunk_async(
                    chunk_text=chunk.content,
                    client=self.client,
                    glossary_instruction=glossary_inst,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                post_processed = self.glossary_manager.enforce_glossary_post_process(
                    translated_text, relevant_terms
                )

                chunk.content = post_processed
                print(f"  [번역 완료 {idx}/{len(chunks)}] {chunk.heading_title[:30]}", flush=True)
                return chunk

        tasks = [_translate_single(c, i + 1) for i, c in enumerate(chunks)]
        translated_chunks = await asyncio.gather(*tasks)

        # 재조립
        parts = [c.full_text() for c in translated_chunks]
        reassembled = "\n\n---\n\n".join(parts).strip() + "\n"
        final_cleaned = clean_and_format_markdown(reassembled)

        if not output_path:
            out_file = src_file.parent / f"{src_file.stem}_{target_lang}{src_file.suffix}"
        else:
            out_file = Path(output_path)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(final_cleaned, encoding="utf-8")
        logger.info(f"[StandaloneTranslator] 번역 완성본 저장 완료: {out_file}")

        return {
            "output_path": str(out_file),
            "original_length": original_length,
            "final_length": len(final_cleaned),
            "total_chunks": len(chunks),
        }

    def translate_document(
        self,
        input_path: str,
        output_path: str | None = None,
        source_lang: str = "en",
        target_lang: str = "ko",
        custom_glossary_path: str | None = None,
    ) -> dict[str, Any]:
        """동기 호출 래퍼."""
        return asyncio.run(
            self.translate_document_async(
                input_path=input_path,
                output_path=output_path,
                source_lang=source_lang,
                target_lang=target_lang,
                custom_glossary_path=custom_glossary_path,
            )
        )
