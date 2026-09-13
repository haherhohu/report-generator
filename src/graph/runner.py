"""PipelineRunner: Unified execution interface decoupled from CLI and Web UI."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable
import yaml

from src.core.state import ReportState
from src.graph.workflow import build_workflow_app
from src.tools.preprocessor import load_source_materials, run_preprocessing

logger = logging.getLogger("report_generator.runner")

DEFAULT_SETTINGS: dict[str, Any] = {
    "max_loops": 2,
    "max_concurrency": 4,
    "target_core_min_length": 3000,
    "target_total_min_length": 50000,
    "checkpoint_db_path": "workspace/checkpoints/report_pipeline.sqlite",
}


def load_pipeline_config(config_path: str = "config/pipeline_config.yaml") -> dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        # fallback to poc path
        p = Path("poc/config/pipeline_config.yaml")

    merged = DEFAULT_SETTINGS.copy()
    if p.exists():
        try:
            loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                merged.update(loaded)
        except Exception as e:
            logger.warning(f"파이프라인 설정 로드 실패, 기본값 사용: {e}")
    return merged


class PipelineRunner:
    """CLI, Streamlit 대시보드, 웹 API 어디서든 동일하게 임포트하여 사용하는 비즈니스 로직 실행기."""

    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        self.config = load_pipeline_config(config_path)
        self.app = build_workflow_app(self.config.get("checkpoint_db_path"))

    def run(
        self,
        initial_state: dict[str, Any],
        thread_id: str = "default_session",
        resume: bool = False,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """파이프라인 스트리밍 실행 및 상태 반환."""
        # 0. 사전 레퍼런스 전처리 (PDF/HTML 요약)
        run_preprocessing(raw_dir="workspace/raw_refs", summary_dir="workspace/source/summary")

        # 1. 기초 자료 로드
        core_materials = load_source_materials("workspace/source/core")
        summary_materials = load_source_materials("workspace/source/summary")
        is_blank_slate = (len(core_materials) == 0 and len(initial_state.get("source_materials", [])) == 0)

        # 2. 초기 상태 설정
        if resume:
            run_input = None
        else:
            state: dict[str, Any] = dict(initial_state)
            state.setdefault("source_materials", core_materials)
            state.setdefault("reference_summaries", summary_materials)
            state.setdefault("is_blank_slate", is_blank_slate)
            state.setdefault("keywords", [])
            state.setdefault("loop_count", 0)
            state.setdefault("max_loops", self.config["max_loops"])
            state.setdefault("max_concurrency", self.config["max_concurrency"])
            state.setdefault("target_core_min_length", self.config["target_core_min_length"])
            state.setdefault("target_total_min_length", self.config["target_total_min_length"])
            state.setdefault("completed_sections", [])
            state.setdefault("expanded_sections", [])
            state.setdefault("artifact_history", [])
            state.setdefault(
                "global_directive",
                "단순 요약이나 병합을 엄격히 금지합니다. 핵심 요약과 실증 데이터를 바탕으로 "
                "논리적 인과관계를 스스로 추론하여 구체적인 서술형 심층 보고서로 확장하십시오."
            )
            run_input = state

        run_config = {"configurable": {"thread_id": thread_id}}
        last_output: dict[str, Any] = {}

        try:
            for step_output in self.app.stream(run_input, config=run_config):
                for node_name, node_state in step_output.items():
                    last_output = node_state
                    if progress_callback:
                        progress_callback(node_name, node_state)
                    else:
                        print(f"  [Pipeline] 노드 완료: {node_name}")
        except Exception as exc:
            snapshot = self.app.get_state(run_config)
            pending = list(snapshot.next or [])
            logger.error(f"[Pipeline] 오류로 중단됨: {exc}. 재개 대기 노드: {pending}")
            raise

        return last_output

