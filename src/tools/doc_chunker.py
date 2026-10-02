"""Document chunker for large markdown documents based on heading hierarchy."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: int
    heading_level: int
    heading_title: str
    content: str
    chapter_number: str = ""
    section_number: str = ""
    role_type: str = "background_trend"
    is_continuation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def full_text(self) -> str:
        if self.heading_level == 0 or self.is_continuation or "(계속)" in self.heading_title:
            return self.content.strip()
        prefix = "#" * self.heading_level
        return f"{prefix} {self.heading_title}\n\n{self.content}".strip()


def parse_heading_info(line: str) -> tuple[int, str]:
    """헤딩 라인에서 레벨과 제목을 추출."""
    m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
    if not m:
        return 0, ""
    level = len(m.group(1))
    title = m.group(2).strip()
    return level, title


def split_markdown_by_headings(markdown_text: str, max_chunk_chars: int = 5000) -> list[DocumentChunk]:
    """
    마크다운 문서를 헤딩(H1, H2, H3) 및 문맥 단위로 분할하여 DocumentChunk 리스트로 변환.
    표(Table)나 코드 블록 내부가 잘리지 않도록 안전하게 분할.
    """
    if not markdown_text:
        return []

    lines = markdown_text.splitlines()
    chunks: list[DocumentChunk] = []

    current_level = 0
    current_title = ""
    current_lines: list[str] = []
    chunk_counter = 0

    current_chapter = ""
    current_section = ""
    is_cont = False

    in_code_block = False
    in_table = False

    def _flush_chunk():
        nonlocal chunk_counter, current_lines, current_level, current_title, is_cont
        text_body = "\n".join(current_lines).strip()
        if text_body or current_title:
            chunk_counter += 1
            # 챕터 역할 자동 추론
            r_type = "background_trend"
            low_t = current_title.lower()
            if any(k in low_t for k in ("서론", "배경", "개요", "추진 필요성")):
                r_type = "intro"
            elif any(k in low_t for k in ("시사점", "제언", "전망")):
                r_type = "implication"
            elif any(k in low_t for k in ("결론", "맺음말", "권고사항")):
                r_type = "final_conclusion"
            elif any(k in low_t for k in ("전략", "거버넌스", "체계")):
                r_type = "core_strategy"
            elif any(k in low_t for k in ("부록", "약어", "참고문헌")):
                r_type = "appendix_facts"

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_counter,
                    heading_level=current_level,
                    heading_title=current_title,
                    content=text_body,
                    chapter_number=current_chapter,
                    section_number=current_section,
                    role_type=r_type,
                    is_continuation=is_cont,
                )
            )
        current_lines = []

    for line in lines:
        stripped = line.strip()

        # 코드 블록 감지
        if stripped.startswith("```"):
            in_code_block = not in_code_block

        # 표 감지
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
        elif not stripped.startswith("|"):
            in_table = False

        is_heading = not in_code_block and not in_table and stripped.startswith("#") and " " in stripped

        if is_heading:
            level, title = parse_heading_info(stripped)
            if level in (1, 2, 3):
                _flush_chunk()
                is_cont = False
                current_level = level
                current_title = title

                # 챕터 및 절 번호 감지
                if level == 1 or "장" in title or re.search(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]", title):
                    current_chapter = title.split()[0] if title else ""
                elif level == 2 or re.search(r"^\d+\.", title):
                    current_section = title.split()[0] if title else ""

                continue

        current_lines.append(line)

        # 단일 섹션이 너무 길 때 문단 단위 추가 분할 방어 (단, (계속) 헤딩 주입 방지)
        if len("\n".join(current_lines)) > max_chunk_chars and not in_code_block and not in_table:
            if stripped == "":
                _flush_chunk()
                is_cont = True

    _flush_chunk()
    return chunks


def reassemble_chunks(chunks: list[DocumentChunk]) -> str:
    """DocumentChunk 리스트를 원본 구조에 맞게 무손실 재조립."""
    if not chunks:
        return ""

    result: list[str] = []
    for chk in chunks:
        txt = chk.full_text()
        if not txt:
            continue
        if chk.is_continuation or "(계속)" in chk.heading_title:
            result.append("\n\n" + txt)
        else:
            if result:
                result.append("\n\n---\n\n" + txt)
            else:
                result.append(txt)

    return "".join(result).strip() + "\n"
