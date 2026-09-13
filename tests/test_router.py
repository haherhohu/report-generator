"""Unit tests for section routing and prompt instructions."""
from src.utils.router import route_section_instruction


def test_route_section_instruction_implication():
    meta = route_section_instruction(
        chapter_role="implication",
        section_title="핵심 시사점 도출",
        report_type="market_tech_trend",
        tone="objective_smooth",
        direction="동향 조사",
    )
    instruction = meta["specific_instruction"]
    assert "핵심 시사점 도출 지침" in instruction
    assert "억지 과제사업이나 예산표를 만들지 마십시오" in instruction
    assert "~한다" in instruction


def test_route_section_instruction_appendix():
    meta = route_section_instruction(
        chapter_role="appendix_facts",
        section_title="통계 및 관계 법령",
        report_type="research_policy",
        tone="official_formal",
        direction="국가 정책",
    )
    instruction = meta["specific_instruction"]
    assert "순수 팩트 나열 지침" in instruction
    assert "주관적인 시사점, 전망, 정책 제언을 일체 작성하지 마십시오" in instruction


def test_route_section_instruction_core_strategy():
    meta = route_section_instruction(
        chapter_role="core_strategy",
        section_title="추진 체계 및 거버넌스",
        report_type="research_policy",
        tone="official_formal",
        direction="민간 관제 체계 마련",
    )
    instruction = meta["specific_instruction"]
    assert "핵심 전략 수립 지침" in instruction
    assert "민간 관제 체계 마련" in instruction
    assert "~함" in instruction

