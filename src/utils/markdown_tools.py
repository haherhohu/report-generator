"""Markdown processing tools for heading depth normalization, cleanup, and intermediate conclusion sanitization."""
from __future__ import annotations

import re

def clean_markdown_text(content: str) -> str:
    """코드 블록 래핑 및 불필요한 공백을 정제."""
    if not content or not isinstance(content, str):
        return ""

    text = content.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return text


def normalize_markdown_headings(
    content: str,
    chapter_number: str,
    section_number: str,
    section_title: str,
) -> str:
    """
    모든 섹션의 마크다운 헤딩 깊이를 표준화:
    - 섹션 헤더: '## [절번호] [절제목]' 형식 고정
    - 내부의 1단계(#) 또는 2단계(##) 헤더는 3단계(###) 또는 4단계(####)로 강등
    """
    cleaned = clean_markdown_text(content)
    if not cleaned:
        return f"## {section_number} {section_title}\n\n[내용 작성 대기 중]"

    # 내부의 H1(# )을 제거하거나 H3(### )으로 변경
    # 만약 첫 줄이 이미 동일한 H1/H2 제목이면 제거
    lines = cleaned.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # 장 전체 제목 형태(# Ⅰ. ... or # 1장 ...) 제거
        if re.match(r"^#\s+(?:제?\s*\d+\s*장|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|\bChapter\b)", stripped, re.IGNORECASE):
            continue
        # 절 제목과 정확히 일치하는 H1/H2 라인 제거 (상단에서 일괄 주입할 것이므로)
        if re.match(rf"^#{{1,3}}\s*(?:{re.escape(section_number)}\s*)?{re.escape(section_title)}", stripped):
            continue
        # 남은 H1(# )은 H3(### )으로 강등
        if stripped.startswith("# "):
            filtered_lines.append("### " + stripped[2:])
        elif stripped.startswith("## "):
            filtered_lines.append("### " + stripped[3:])
        else:
            filtered_lines.append(line)

    body = "\n".join(filtered_lines).strip()
    expected_header = f"## {section_number} {section_title}".strip()

    return f"{expected_header}\n\n{body}"


def sanitize_intermediate_conclusions(content: str, role_type: str) -> str:
    """
    본문 챕터(1장 ~ N-1장)에서 독립적으로 전체 '결론 및 제언'을 쓰는 현상을 방지.
    final_conclusion 역할이 아닌 경우, '결론' 표기를 '[소결: 본 절의 주요 시사점]'으로 대체.
    """
    if role_type == "final_conclusion":
        return content

    # '## 결론', '### 결론', '종합 결론 및 제언' 등을 '소결: 본 절의 주요 시사점'으로 치환
    patterns = [
        (r"(?m)^#+\s*(?:종합\s*)?결론(?:\s*및\s*(?:시사점|제언))?.*$", "### 다. 소결: 본 절의 주요 시사점"),
        (r"(?m)^#+\s*(?:향후\s*과제\s*및\s*결론|맺음말).*$", "### 다. 소결: 본 절의 주요 시사점"),
    ]

    sanitized = content
    for pat, repl in patterns:
        sanitized = re.sub(pat, repl, sanitized)

    # 중간 장에서 개별 약어표나 참고문헌 헤더가 들어간 경우 제거
    sanitized = re.sub(r"(?m)^#+\s*(?:참고문헌|약어표|참고자료\s*목록).*?\n(?:[-*0-9].*?\n)*", "", sanitized)

    return sanitized
