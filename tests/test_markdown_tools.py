"""Unit tests for markdown processing and heading normalization."""
from src.utils.markdown_tools import (
    clean_markdown_text,
    normalize_markdown_headings,
    sanitize_intermediate_conclusions,
)


def test_clean_markdown_text():
    wrapped = "```markdown\n# 본문\n내용입니다.\n```"
    assert clean_markdown_text(wrapped) == "# 본문\n내용입니다."

    normal = "일반 텍스트"
    assert clean_markdown_text(normal) == "일반 텍스트"


def test_normalize_markdown_headings():
    raw_content = """# Ⅰ. 글로벌 시장 규모
# 1. 글로벌 시장 규모 및 전망
본문 내용입니다.
# 주요 선도국 비교
비교 내용.
"""
    normalized = normalize_markdown_headings(
        raw_content,
        chapter_number="Ⅰ",
        section_number="1.",
        section_title="글로벌 시장 규모 및 전망",
    )

    assert normalized.startswith("## 1. 글로벌 시장 규모 및 전망")
    assert "### 주요 선도국 비교" in normalized
    # Top-level chapter header should be removed
    assert "# Ⅰ. 글로벌 시장 규모" not in normalized


def test_sanitize_intermediate_conclusions():
    content = """본문 분석 완료.

## 종합 결론 및 제언
이러한 이유로 전면적인 정책 개선이 필요함.

## 참고문헌
- 논문 1
- 기사 2
"""
    # For intermediate chapter (e.g. background_trend)
    sanitized = sanitize_intermediate_conclusions(content, role_type="background_trend")
    assert "### 다. 소결: 본 절의 주요 시사점" in sanitized
    assert "## 종합 결론 및 제언" not in sanitized
    assert "## 참고문헌" not in sanitized

    # For final_conclusion chapter, it should keep the conclusion
    kept = sanitize_intermediate_conclusions(content, role_type="final_conclusion")
    assert "## 종합 결론 및 제언" in kept

