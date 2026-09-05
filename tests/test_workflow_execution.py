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
    with patch("src.tools.search.perform_hybrid_research", return_value="검색된 팩트 데이터"):
        with patch("src.models.client.UnifiedModelClient.generate_text_sync") as mock_sync:
            mock_sync.return_value = ModelGenerationResult(
                text="## 조사 결과\n\nAI 드론 시장은 급성장 중임.\n\n## 실제 참고 출처\n- 국가 공식 통계 포털",
                model_used="gemini-2.5-flash-lite",
                provider="gemini",
            )
            s2 = run_researcher(s1)
            assert len(s2.get("reference_paths", [])) >= 2
            assert len(s2.get("collected_references", [])) >= 2

    # 3. Expander (전 챕터 섹션 비동기 팽창)
    with patch("src.models.client.UnifiedModelClient.generate_text") as mock_async:
        async def fake_gen(*args, **kwargs):
            return ModelGenerationResult(
                text="가. 현황 분석\n본문 내용 서술.\n\n> **【그림 1-1】 구조도**\n> - 구조: A ➔ B\n\n| 구분 | 수치 |\n| A | 100 |",
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
