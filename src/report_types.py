"""Report type definitions and chapter templates for the generation pipeline."""

from __future__ import annotations

REPORT_TYPE_TEMPLATES = {
    "research_policy": {
        "label": "연구보고서(정책용)",
        "chapters": [
            {"index": 1, "title": "1장 서론"},
            {"index": 2, "title": "2장 필요성"},
            {"index": 3, "title": "3장 사례 연구/분석"},
            {"index": 4, "title": "4장 전략 및 정책 제언"},
            {"index": 5, "title": "5장 수행내역(세부과제)"},
            {"index": 6, "title": "6장 추진체계/일정 및 예산"},
            {"index": 7, "title": "7장 기대효과 및 결론"},
            {"index": 8, "title": "8장 부록 (통계 및 법령 등)"},
            {"index": 9, "title": "9장 참고문헌, 약어표"},
        ],
    },
    "trend_analysis": {
        "label": "동향분석 보고서",
        "chapters": [
            {"index": 1, "title": "1장 서론"},
            {"index": 2, "title": "2장 시장동향"},
            {"index": 3, "title": "3장 기술(산업)동향"},
            {"index": 4, "title": "4장 국가별 동향"},
            {"index": 5, "title": "5장 경쟁사/주요 사례"},
            {"index": 6, "title": "6장 시사점"},
            {"index": 7, "title": "7장 통계 및 참고자료"},
            {"index": 8, "title": "8장 결론"},
        ],
    },
}

DEFAULT_REPORT_TYPE = "research_policy"


def normalize_report_type(report_type: str | None, *, direction: str | None = None) -> str:
    """보고서 종류를 표준화하고, 방향성 문자열에서 동향 분석형을 자동 감지합니다."""
    text = (report_type or "").strip().lower().replace("-", "_")
    if not text and direction:
        lowered = str(direction).lower()
        if "동향" in str(direction) or "trend" in lowered or "market" in lowered:
            text = "trend_analysis"
    if text in REPORT_TYPE_TEMPLATES:
        return text
    if text in {"policy", "research", "policy_research", "정책용", "연구보고서"}:
        return "research_policy"
    if text in {"trend", "trend_analysis", "동향분석", "시장동향", "technology_trend"}:
        return "trend_analysis"
    return DEFAULT_REPORT_TYPE


def get_report_outline(report_type: str | None = None, *, direction: str | None = None):
    normalized = normalize_report_type(report_type, direction=direction)
    return list(REPORT_TYPE_TEMPLATES[normalized]["chapters"])


def get_required_chapter_titles(report_type: str | None = None, *, direction: str | None = None):
    normalized = normalize_report_type(report_type, direction=direction)
    return {chapter["index"]: chapter["title"] for chapter in REPORT_TYPE_TEMPLATES[normalized]["chapters"]}
