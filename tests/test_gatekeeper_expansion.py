"""Test Gatekeeper dynamic section expansion and monotonic volume growth."""
from unittest.mock import patch
from src.core.state import ReportState
from src.agents.drafter import run_drafter
from src.agents.expander import run_expander
from src.agents.gatekeeper import run_gatekeeper
from src.models.client import ModelGenerationResult


def test_gatekeeper_expands_new_sections_monotonically():
    initial_state: ReportState = {
        "topic": "스마트 모빌리티 기술전략",
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
            text='["스마트 모빌리티 동향", "관련 정책 규제"]',
            model_used="gemini-2.5-flash",
            provider="gemini",
        )
        s1 = run_drafter(initial_state)

    initial_section_count = len(s1["sections"])
    assert initial_section_count == 16  # 8 chapters * 2 sections each

    # 2. Expander (최초 팽창)
    with patch("src.models.client.UnifiedModelClient.generate_text") as mock_async:
        async def fake_gen(*args, **kwargs):
            return ModelGenerationResult(
                text="가. 현황 분석\n본문 내용 서술.\n\n> **【그림 1-1】 구조도**\n> - 구조: A ➔ B\n\n| 구분 | 수치 |\n| A | 100 |",
                model_used="gemini-2.5-flash",
                provider="gemini",
            )
        mock_async.side_effect = fake_gen
        s2 = run_expander(s1)

    initial_expanded_count = len(s2["expanded_sections"])
    assert initial_expanded_count == 16

    initial_first_sec_content = s2["expanded_sections"][0]["content"]
    initial_total_len = sum(len(sec["content"]) for sec in s2["expanded_sections"])

    # 3. Gatekeeper에 높은 목표치(1,000,000자)를 주어 루프 유도
    s2["target_total_min_length"] = 1_000_000
    s3 = run_gatekeeper(s2)

    # Gatekeeper 검증
    assert s3.get("next_step") == "researcher"
    assert s3.get("loop_count") == 1
    new_loop_targets = s3.get("target_sections_for_loop", [])
    assert len(new_loop_targets) > 0

    # 신규 섹션이 state["sections"]에 증설되었는지 확인
    assert len(s3["sections"]) > initial_section_count
    # 신규 키워드가 추가되었는지 확인
    assert len(s3.get("keywords", [])) > 2

    # 4. Expander 재가동 (루프 타겟만 선별 작성)
    with patch("src.models.client.UnifiedModelClient.generate_text") as mock_async:
        async def fake_gen_loop(*args, **kwargs):
            return ModelGenerationResult(
                text="가. 신규 확장 실증 분석\n증설된 섹션 내용 서술.\n\n> **【그림 2-1】 심층 구조도**\n\n| 항목 | 결과 |\n| B | 200 |",
                model_used="gemini-2.5-flash",
                provider="gemini",
            )
        mock_async.side_effect = fake_gen_loop
        s4 = run_expander(s3)

    # 단조 증가(Monotonic Growth) 및 기존 데이터 보존 검증
    post_expanded_count = len(s4["expanded_sections"])
    assert post_expanded_count > initial_expanded_count
    assert post_expanded_count == initial_expanded_count + len(new_loop_targets)

    # 기존 첫 번째 섹션의 내용이 덮어씌워지지 않고 그대로 보존되었는지 검증
    assert s4["expanded_sections"][0]["content"] == initial_first_sec_content

    # 전체 글자 수가 엄격하게 증가했는지 검증
    post_total_len = sum(len(sec["content"]) for sec in s4["expanded_sections"])
    assert post_total_len > initial_total_len

