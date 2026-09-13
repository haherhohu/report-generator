"""Unit tests for acronym extraction and citation collection."""
from src.utils.glossary_parser import (
    extract_acronyms_from_markdown,
    extract_in_text_citations,
)


def test_extract_acronyms_from_markdown():
    text = """
    무인항공기(UAV) 및 무인항공시스템(UAS)의 지휘통제(C2) 네트워크 안전성을 검증한다.
    핵심 원천기술의 기술성숙도(TRL)는 6단계에 도달하였으며, 
    시장 규모는 연평균 복합 성장률(CAGR) 18.5%로 성장할 것으로 전망된다.
    미국 연방항공청(FAA)은 새로운 규정을 발표했다.
    """
    results = extract_acronyms_from_markdown(text)
    acronyms = {item["acronym"] for item in results}

    assert "UAV" in acronyms
    assert "UAS" in acronyms
    assert "C2" in acronyms
    assert "TRL" in acronyms
    assert "CAGR" in acronyms
    assert "FAA" in acronyms


def test_extract_in_text_citations():
    text = """
    산업 성장률은 지속적으로 상승하고 있다 [1].
    
    | 연도 | 규모 |
    | 2024 | 100억 |
    ※ 자료: 국가 공식 통계 포털 및 국책연구원 실태조사
    
    [1] 산업통상자원부, 첨단기술 육성 종합계획, 2024.
    """
    citations = extract_in_text_citations(text)
    assert any("국가 공식 통계" in c for c in citations)
    assert any("[1]" in c for c in citations)

