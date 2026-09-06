"""Unit tests for researcher quality gate and solitary table prevention."""
from pathlib import Path
from unittest.mock import patch
from src.core.state import ReportState
from src.agents.researcher import run_researcher
from src.models.client import ModelGenerationResult
from src.utils.final_guard import is_valid_quality_content, should_reuse_or_create_final


def test_is_valid_quality_content_detects_solitary_tables():
    # 1. 표만 하나 덜렁 있고 서술 문단이 거의 없는 불량 콘텐츠
    solitary_table = """
| 연번 | 조사 구분 | 주요 지표명 | 수치/통계 |
| :---: | :--- | :--- | :--- |
| 1 | 시장 규모 | 글로벌 시장 총매출 | 약 1,280억 달러 |
"""
    assert is_valid_quality_content(solitary_table) is False

    # 2. 200자 미만의 단답형 불량 콘텐츠
    short_reply = "## 조사 결과\n\nAI 드론 시장은 급성장 중임.\n\n## 실제 참고 출처\n- 국가 공식 통계 포털"
    assert is_valid_quality_content(short_reply) is False

    # 3. 서술형 문단과 수치/분석이 풍부하게 전개된 양질의 콘텐츠
    rich_content = """## AI 드론 시장 동향 조사보고서

가. 현황 분석
글로벌 AI 드론 시장은 연평균 25% 이상 급성장하고 있으며, 특히 군사 및 상업용 공역 관제 분야를 중심으로 자율비행 알고리즘의 고도화가 핵심 경쟁력으로 부상하고 있음.
미국과 유럽 등 주요 선도국은 규제 샌드박스를 통해 신기술 검증을 적극 지원하고 있으며 국내 역시 산학연 중심의 컨소시엄 구축이 활발함.

나. 산업적 파급효과
AI 드론 산업은 단순 하드웨어 제조를 넘어 데이터 서비스 및 인공지능 관제 솔루션과의 결합으로 부가가치가 극대화되는 추세임.
국내 기업의 글로벌 시장 진입을 위해 통신 규격 인증 및 보안 체계 마련이 시급한 과제로 대두됨.

| 구분 | 주요 지표명 | 기준연도 | 수치 | 비고 |
| :--- | :--- | :---: | :---: | :--- |
| 시장 규모 | 글로벌 시장 총매출 | 2024 | 1,280억 달러 | 시장 분석원 |
| 기술 수준 | 최고 선도국 대비 | 2024 | 87.5% | 기술평가원 |
"""
    assert is_valid_quality_content(rich_content) is True


def test_should_not_create_final_from_junk_artifacts(tmp_path):
    # 불량 아티팩트(표만 덜렁 있거나 짧은 단편) 5개 생성
    paths = []
    for i in range(5):
        p = tmp_path / f"junk_note_{i}.md"
        p.write_text(f"| A | {i} |\n단답 {i}", encoding="utf-8")
        paths.append(str(p))

    state = {
        "artifact_history": [
            {"title": "시장 동향", "type": "research-note", "path": p}
            for p in paths
        ]
    }

    # require_quality=True일 때 불량품 5개는 Final로 승격되지 않아야 함
    res = should_reuse_or_create_final(
        state,
        title="시장 동향",
        related_paths=paths,
        duplicate_threshold=5,
        summary_only=True,
        require_quality=True,
    )

    assert res["triggered_duplicate"] is False
    assert res["content"] is None


def test_researcher_handles_search_failure_with_user_source():
    # 검색 실패 시 사용자 제공 원시자료가 있으면 이를 활용하는지 검증
    initial_state: ReportState = {
        "topic": "UAS 관제 체계",
        "direction": "실증 방안 도출",
        "keywords": ["Vantis 관제"],
        "source_materials": [
            {
                "filename": "FAA_Vantis_Guide.pdf",
                "content": "노스다코타 Vantis는 전주기 초시계 비행(BVLOS)을 지원하는 미국 최초의 주 전역 공용 무인항공기 관제 인프라임.\n\n레이더와 감시 센서망을 연동하여 지상 및 공역 안전성을 검증함.",
            }
        ],
        "completed_sections": [],
        "expanded_sections": [],
        "artifact_history": [],
    }

    fake_search_fail = {
        "has_results": False,
        "records": [],
        "context_text": "",
    }

    with patch("src.tools.search.perform_hybrid_research_structured", return_value=fake_search_fail):
        with patch("src.models.client.UnifiedModelClient.generate_text_sync") as mock_sync:
            # LLM 호출 실패 시에도 사용자 제공 자료 기반 폴백 작동 확인
            mock_sync.side_effect = Exception("API error")
            res_state = run_researcher(initial_state)

            assert len(res_state["reference_paths"]) == 1
            note = Path(res_state["reference_paths"][0]).read_text(encoding="utf-8")
            assert "제공 기초자료 기반 분석" in note
            assert "FAA_Vantis_Guide.pdf" in note

