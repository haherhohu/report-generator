"""Translator Agent: Translates markdown chunks with glossary binding and layout preservation."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from src.models.client import UnifiedModelClient
from src.utils.markdown_cleaner import clean_table_nesting

logger = logging.getLogger("report_generator.agents.translator")


async def translate_chunk_async(
    chunk_text: str,
    client: UnifiedModelClient,
    glossary_instruction: str = "",
    source_lang: str = "en",
    target_lang: str = "ko",
    tone: str = "objective_smooth",
) -> str:
    """단일 마크다운 청크 전문 번역."""
    if not chunk_text or not chunk_text.strip():
        return ""

    if os.getenv("MOCK_MODE") == "true" or getattr(client, "provider", "") == "mock":
        # Mock 번역 결과
        return f"[번역본 ({target_lang})]\n\n" + chunk_text

    tone_rule = "모든 문장의 종결 어미는 공공 보고서 표준인 '~한다', '~이다', '~됨'을 준수하십시오."
    if tone == "official_formal":
        tone_rule = "모든 문장의 종결 어미는 국책연구원 표준인 '~함', '~임' 개조식을 준수하십시오."

    system_prompt = (
        "당신은 최고 수준의 국책연구기관 전문 번역위원이자 기술 감수위원입니다. "
        "원문의 논리적 의미를 완벽하게 한국어로 옮기되, 기계 번역투나 어색한 비문을 배제하고 "
        "관공서/학술 보고서에 걸맞은 품격 있는 문체로 전문 번역하십시오."
    )

    user_prompt = f"""
다음은 보고서의 세부 섹션 원문({source_lang})입니다. 목표 언어({target_lang})로 번역하십시오.

{glossary_instruction}

[번역 5대 철칙]
1. 원문의 문단 구조, 표(Table), 리스트 순서, 수식($...$), 도식화 블록을 100% 동일하게 유지하십시오.
2. 표 내부의 텍스트와 수치를 누락하거나 요약하지 말고 행(Row)을 1:1로 정확하게 번역하십시오.
3. {tone_rule}
4. 영어 직역 표현(예: closing -> 폐쇄)을 문맥에 맞는 자연스러운 한국어 전문 용어로 의역하십시오.
5. 설명이나 사족 없이 순수 번역된 마크다운 텍스트만 출력하십시오.

[원문]
{chunk_text}
"""
    try:
        res = await client.generate_text(user_prompt, system_instruction=system_prompt)
        translated = clean_table_nesting(res.text)
        return translated.strip()
    except Exception as e:
        logger.warning(f"[Translator] 번역 실패: {e}")
        return chunk_text
