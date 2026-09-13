"""Unit tests for 3-tier grounded bibliography and hallucination prevention."""
from pathlib import Path
from src.core.state import ReportState
from src.agents.merger import run_merger, _build_grounded_bibliography


def test_grounded_bibliography_with_verified_web_records():
    # 케이스 1: 실제 수집된 웹 검색 레코드가 있는 경우
    state: ReportState = {
        "topic": "AI 반도체 시장 동향",
        "verified_references": [
            {"title": "Gartner AI Semiconductor Forecast", "href": "https://gartner.com/ai-chips", "source_type": "market_web"},
            {"title": "KISTEP 정책 브리프", "href": "https://kistep.re.kr/brief", "source_type": "policy_pdf"},
        ],
        "collected_references": [],
        "source_materials": [
            # 내부 임시 파일 - 참고문헌에서 제외되어야 함
            {"filename": "research_AI_반도체.md", "content": "임시 요약"},
        ],
        "expanded_sections": [
            {
                "chapter_number": "Ⅰ",
                "section_number": "1.",
                "title": "개요",
                "content": "본문 내용... ※ 자료: 자체 분석 및 국책연구원 표준 프레임워크", # 가짜 출처 - 제외되어야 함
            }
        ],
        "chapters": [{"chapter_number": "Ⅷ", "title": "부록"}],
    }

    refs = _build_grounded_bibliography(state, full_body_str="본문 내용... ※ 자료: 자체 분석 및 국책연구원")
    assert any("Gartner AI Semiconductor Forecast" in r for r in refs)
    assert any("https://gartner.com/ai-chips" in r for r in refs)
    assert any("KISTEP 정책 브리프" in r for r in refs)
    # 가짜 출처 및 내부 파일 배제 확인
    assert not any("자체 분석" in r for r in refs)
    assert not any("research_AI_반도체.md" in r for r in refs)


def test_grounded_bibliography_with_user_source_materials_only():
    # 케이스 2: 웹 검색 결과가 없고 사용자 제공 원시자료만 있는 경우
    state: ReportState = {
        "topic": "스마트 모빌리티 정책",
        "verified_references": [],
        "collected_references": [],
        "source_materials": [
            {"filename": "2024_국토부_모빌리티_혁신로드맵.pdf", "content": "원시 문서"},
            # 내부 임시 파일은 제외되어야 함
            {"filename": "research_모빌리티_동향.md", "content": "임시 요약"},
            {"filename": "research_모빌리티_동향_final.md", "content": "임시 요약 final"},
        ],
        "expanded_sections": [
            {
                "chapter_number": "Ⅰ",
                "section_number": "1.",
                "title": "개요",
                "content": "본문 내용...",
            }
        ],
        "chapters": [{"chapter_number": "Ⅷ", "title": "부록"}],
    }

    refs = _build_grounded_bibliography(state, full_body_str="본문 내용...")
    assert len(refs) == 1
    assert "제공 기초자료: 2024_국토부_모빌리티_혁신로드맵.pdf" in refs[0]
    assert not any("research_" in r for r in refs)



def test_grounded_bibliography_empty_when_no_data(tmp_path):
    # 케이스 3: 웹 검색 결과도 없고 제공 자료도 없는 경우 허위 출처 생성 금지
    state: ReportState = {
        "topic": "양자컴퓨팅 미래전략",
        "verified_references": [],
        "collected_references": [],
        "source_materials": [],
        "expanded_sections": [
            {
                "chapter_number": "Ⅰ",
                "section_number": "1.",
                "title": "개요",
                "content": "양자 컴퓨팅 개요 본문 서술.",
            }
        ],
        "chapters": [{"chapter_number": "Ⅷ", "title": "부록"}],
        "report_type": "market_tech_trend",
    }

    s_res = run_merger(state)
    final_text = Path(s_res["final_report_path"]).read_text(encoding="utf-8")

    # 무인항공기 등 허위 참고문헌이 일체 생성되지 않아야 함
    assert "무인항공기" not in final_text
    assert "UAV" not in final_text
    assert "국가 공식 통계 포털 및 수집된 정책" not in final_text
    # 대신 사실에 기반한 안내 문구가 기재됨
    assert "별도의 외부 인용 문헌이 존재하지 않습니다" in final_text
