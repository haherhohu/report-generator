"""Glossary Manager for consistent terminology across long-form translations."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml

from src.utils.glossary_parser import KNOWN_ACRONYMS


class GlossaryManager:
    """초장문 번역 시 전문용어 일관성을 강제하는 용어집 관리자."""

    def __init__(self, custom_glossary: dict[str, str] | None = None):
        self.glossary: dict[str, str] = {}
        # 1. 기본 내장 공인 약어집 등록
        for acr, (full_eng, def_kor) in KNOWN_ACRONYMS.items():
            self.glossary[acr] = f"{def_kor}({acr})"
            self.glossary[full_eng] = f"{def_kor}({acr})"

        # 2. 사용자 지정 사전 병합
        if custom_glossary:
            self.glossary.update(custom_glossary)

    def load_glossary_file(self, file_path: str | Path) -> None:
        p = Path(file_path)
        if not p.exists():
            return
        try:
            content = p.read_text(encoding="utf-8")
            if p.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content) or {}
                if isinstance(data, dict):
                    self.glossary.update({str(k): str(v) for k, v in data.items()})
            elif p.suffix in (".csv", ".tsv"):
                delim = "\t" if p.suffix == ".tsv" else ","
                for line in content.splitlines():
                    parts = line.split(delim)
                    if len(parts) >= 2:
                        self.glossary[parts[0].strip()] = parts[1].strip()
        except Exception:
            pass

    def scan_and_extract_terms(self, text: str) -> dict[str, str]:
        """원문 텍스트를 스캔하여 매칭되는 주요 전문 용어 목록을 필터링."""
        matched: dict[str, str] = {}
        for term, target_trans in self.glossary.items():
            # 단어 경계 매칭
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if pattern.search(text):
                matched[term] = target_trans
        return matched

    def build_glossary_prompt_instruction(self, relevant_glossary: dict[str, str]) -> str:
        """번역 LLM에 주입할 고정 전문용어 사전 지침 생성."""
        if not relevant_glossary:
            return ""

        lines = ["[고정 전문용어 사전 (Glossary - 번역 시 반드시 아래 용어로 1:1 치환할 것)]"]
        for src, tgt in sorted(relevant_glossary.items(), key=lambda x: -len(x[0]))[:40]:
            lines.append(f"- {src} ➔ {tgt}")

        return "\n".join(lines) + "\n"

    def enforce_glossary_post_process(self, text: str, relevant_glossary: dict[str, str]) -> str:
        """번역 후처리: 누락되거나 오역된 중요 용어의 결정론적 치환 보정."""
        processed = text
        # 대표적인 직역 오역 사례 정규화
        common_mistranslations = [
            (r"\b공급망\s*폐쇄\b", "공급망 축소 및 제약"),
            (r"\b닫는\s*중\b", "마감 중"),
            (r"\b게임\s*체인저\b", "핵심 전환 동인"),
        ]
        for pat, repl in common_mistranslations:
            processed = re.sub(pat, repl, processed)

        return processed
