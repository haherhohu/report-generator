"""Unit tests for report types and dynamic template configuration."""
from src.core.report_types import (
    normalize_report_type,
    get_report_type_config,
    get_chapter_role,
    build_initial_chapters,
    get_required_chapter_titles,
)


def test_normalize_report_type():
    assert normalize_report_type("market_tech_trend") == "market_tech_trend"
    assert normalize_report_type("동향분석") == "market_tech_trend"
    assert normalize_report_type("research_policy") == "research_policy"
    assert normalize_report_type("정책용") == "research_policy"
    assert normalize_report_type("global_market_expansion") == "global_market_expansion"
    assert normalize_report_type("해외진출") == "global_market_expansion"

    # From direction
    assert normalize_report_type(None, direction="글로벌 시장 동향 조사 분석") == "market_tech_trend"
    assert normalize_report_type(None, direction="해외 시장 진출 가이드라인 수립") == "global_market_expansion"
    assert normalize_report_type(None, direction="국가 정책 과제 기획 연구") == "research_policy"


def test_get_report_type_config():
    trend_config = get_report_type_config("market_tech_trend")
    assert trend_config.type_id == "market_tech_trend"
    assert trend_config.default_tone == "objective_smooth"
    assert len(trend_config.chapters) == 8

    policy_config = get_report_type_config("research_policy")
    assert policy_config.type_id == "research_policy"
    assert policy_config.default_tone == "official_formal"
    assert len(policy_config.chapters) == 9

    global_config = get_report_type_config("global_market_expansion")
    assert global_config.type_id == "global_market_expansion"
    assert len(global_config.chapters) == 8


def test_get_chapter_role():
    # market_tech_trend: Chapter 6 is implication
    assert get_chapter_role("market_tech_trend", 6) == "implication"
    # research_policy: Chapter 4 is core_strategy, Chapter 5 is action_plans
    assert get_chapter_role("research_policy", 4) == "core_strategy"
    assert get_chapter_role("research_policy", 5) == "action_plans"


def test_build_initial_chapters():
    chapters = build_initial_chapters("market_tech_trend", target_pages=100, target_chars=125000)
    assert len(chapters) == 8
    total_sec_pages = sum(sec["target_pages"] for chap in chapters for sec in chap["sections"])
    assert total_sec_pages > 80

    titles = get_required_chapter_titles("market_tech_trend")
    assert 6 in titles
    assert "시사점" in titles[6]

