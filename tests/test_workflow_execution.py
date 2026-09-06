"""End-to-end pipeline workflow test with mocked LLM generation."""
from unittest.mock import patch
from src.core.state import ReportState
from src.agents.drafter import run_drafter
from src.agents.researcher import run_researcher
from src.agents.expander import run_expander
from src.agents.reviewer import run_reviewer
from src.agents.gatekeeper import run_gatekeeper
from src.agents.merger import run_merger
from src.models.client import ModelGenerationResult


def test_full_pipeline_step_by_step(tmp_path):
    initial_state: ReportState = {
        "topic": "AI 드론 기술동향 분석",
        "direction": "글로벌 동향 조사 및 시사점 도출",
        "target_perspective": "연구기관 관점",
        "report_type": "market_tech_trend",
        "tone": "objective_smooth",
        "target_pages": 30,
        "target_chars": 40000,
        "is_blank_slate": True,
        "source_materials": [],
        "completed_sections": [],
        "expanded_sections": [],
        "artifact_history": [],
    }

    # 1. Drafter
    with patch("src.models.client.UnifiedModelClient.generate_text_sync") as mock_sync:
        mock_sync.return_value = ModelGenerationResult(
            text='["AI 드론 시장 동향", "관련 규제 정책"]',
            model_used="gemini-2.5-flash",
            provider="gemini",
        )
        s1 = run_drafter(initial_state)
        assert "chapters" in s1
        assert len(s1["chapters"]) == 8
        assert len(s1["keywords"]) >= 2
        assert s1["foundation_report_path"] is not None

    # 2. Researcher
    fake_search_output = {
        "has_results": True,
        "records": [
            {"title": "글로벌 AI 드론 시장 동향 보고서", "href": "https://example.com/drone_report", "source_type": "market_web"},
        ],
        "context_text": "글로벌 AI 드론 시장 동향에 대한 상세 팩트 데이터...",
    }
    with patch("src.tools.search.perform_hybrid_research_structured", return_value=fake_search_output):
        with patch("src.models.client.UnifiedModelClient.generate_text_sync") as mock_sync:
            mock_sync.return_value = ModelGenerationResult(
                text="## AI 드론 시장 동향 조사보고서\n\n가. 현황 분석\n글로벌 AI 드론 시장은 연평균 25% 이상 급성장하고 있으며, 특히 군사 및 상업용 공역 관제 분야를 중심으로 자율비행 알고리즘의 고도화가 핵심 경쟁력으로 부상하고 있음.\n미국과 유럽 등 주요 선도국은 규제 샌드박스를 통해 신기술 검증을 적극 지원하고 있으며 국내 역시 산학연 중심의 컨소시엄 구축이 활발함.\n\n나. 산업적 파급효과\nAI 드론 산업은 단순 하드웨어 제조를 넘어 데이터 서비스 및 인공지능 관제 솔루션과의 결합으로 부가가치가 극대화되는 추세임.\n\n## 실제 참고 출처\n- 글로벌 AI 드론 시장 동향 보고서 (https://example.com/drone_report)",
                model_used="gemini-2.5-flash-lite",
                provider="gemini",
            )
            s2 = run_researcher(s1)
            assert len(s2.get("reference_paths", [])) >= 2
            assert len(s2.get("collected_references", [])) >= 2
            assert len(s2.get("verified_references", [])) >= 1

    # 3. Expander (전 챕터 섹션 비동기 팽창)
    with patch("src.models.client.UnifiedModelClient.generate_text") as mock_async:
        async def fake_gen(*args, **kwargs):
            return ModelGenerationResult(
                text="가. 현황 분석\n글로벌 기술 경쟁 심화에 대응하기 위한 실증 데이터 기반 진단을 수행함.\n각 분야별 표준화 및 규제 개선이 시급한 상황이며 산학연 협력이 요구됨.\n\n> **【그림 1-1】 구조도**\n> - 구조: 거시 환경 ➔ 실증 진단 ➔ 대응 전략\n\n| 구분 | 지표명 | 수치 | 비고 |\n| :--- | :--- | :--- | :--- |\n| 핵심역량 | 기술성숙도 | 87.5% | 선진국 대비 |\n\n나. 세부 분석 및 시사점\n상기 지표에서 확인되듯 국내 기술 수준은 지속적으로 향상되고 있으나 원천 기술 확보를 위한 추가적인 정책 지원이 필수적임.",
                model_used="gemini-2.5-flash",
                provider="gemini",
            )
        mock_async.side_effect = fake_gen
        s3 = run_expander(s2)
        assert len(s3.get("expanded_sections", [])) >= 8


    # 4. Reviewer
    s4 = run_reviewer(s3)
    assert s4.get("reviewer_feedback") is not None
    # Headings normalized
    for sec in s4["expanded_sections"]:
        assert sec["content"].startswith("## ")

    # 5. Gatekeeper
    s4["target_total_min_length"] = 100 # Low threshold for test
    s5 = run_gatekeeper(s4)
    assert s5.get("next_step") == "merger"

    # 6. Merger
    s6 = run_merger(s5)
    assert s6.get("final_report_path") is not None
    from pathlib import Path
    final_file = Path(s6["final_report_path"])
    assert final_file.exists()
    final_text = final_file.read_text(encoding="utf-8")
    assert "# AI 드론 기술동향 분석" in final_text
    assert "국내외 공식 참고문헌" in final_text
    assert "영문 약어(Acronym)" in final_text
