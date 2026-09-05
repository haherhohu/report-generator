"""Tests for PipelineRunner and SqliteSaver checkpointer resume functionality."""
from unittest.mock import patch
from pathlib import Path
from src.graph.runner import PipelineRunner
from src.models.client import ModelGenerationResult


def test_pipeline_runner_and_checkpoint_resume(tmp_path):
    checkpoint_db = str(tmp_path / "test_pipeline.sqlite")
    
    # 임시 파이프라인 설정
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(f"""
max_loops: 1
max_concurrency: 2
target_core_min_length: 100
target_total_min_length: 500
checkpoint_db_path: "{checkpoint_db}"
""", encoding="utf-8")

    runner = PipelineRunner(str(config_file))

    initial_state = {
        "topic": "위성통신 기반 무인기 관제 동향",
        "direction": "위성 기반 C2 통신 분석 및 시사점",
        "target_perspective": "국토교통부 관점",
        "report_type": "market_tech_trend",
        "tone": "objective_smooth",
        "target_pages": 30,
        "target_chars": 40000,
        "is_blank_slate": True,
        "source_materials": [],
    }

    # 전체 노드 모킹 실행
    with patch("src.tools.search.perform_hybrid_research", return_value="위성 통신 팩트 데이터"):
        with patch("src.models.client.UnifiedModelClient.generate_text_sync") as mock_sync:
            mock_sync.return_value = ModelGenerationResult(
                text='["위성 통신 규격", "글로벌 시장 동향"]',
                model_used="gemini-2.5-flash",
                provider="gemini",
            )
            with patch("src.models.client.UnifiedModelClient.generate_text") as mock_async:
                async def fake_async(*args, **kwargs):
                    return ModelGenerationResult(
                        text="가. 분석 내용\n상세 내용 서술.\n\n> **【그림 1-1】 구조도**\n> - 흐름: A ➔ B\n\n| 구분 | 지표 |\n| 위성 | C2 |",
                        model_used="gemini-2.5-flash",
                        provider="gemini",
                    )
                mock_async.side_effect = fake_async

                progress_records = []
                def on_progress(node, state):
                    progress_records.append(node)

                result = runner.run(
                    initial_state=initial_state,
                    thread_id="test_session_1",
                    resume=False,
                    progress_callback=on_progress,
                )

                assert "drafter" in progress_records
                assert "researcher" in progress_records
                assert "merger" in progress_records
                assert result.get("final_report_path") is not None
                assert Path(result["final_report_path"]).exists()

                # 체크포인트 DB 생성 확인
                assert Path(checkpoint_db).exists()

