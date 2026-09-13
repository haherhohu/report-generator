"""LangGraph StateGraph definition and SqliteSaver checkpoint binding."""
from __future__ import annotations

import os
import sqlite3
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.core.state import ReportState
from src.agents.drafter import run_drafter
from src.agents.researcher import run_researcher
from src.agents.expander import run_expander
from src.agents.reviewer import run_reviewer
from src.agents.gatekeeper import run_gatekeeper
from src.agents.merger import run_merger


def route_after_gatekeeper(state: ReportState) -> str:
    """Gatekeeper 심사 결과에 따라 재조사 루프 또는 최종 병합으로 분기."""
    next_step = state.get("next_step")
    if next_step == "researcher":
        return "researcher"
    return "merger"


def create_report_graph() -> StateGraph:
    """파이프라인 StateGraph 그래프 구조 생성."""
    graph = StateGraph(ReportState)

    # 1. 6대 에이전트 노드 등록
    graph.add_node("drafter", run_drafter)
    graph.add_node("researcher", run_researcher)
    graph.add_node("expander", run_expander)
    graph.add_node("reviewer", run_reviewer)
    graph.add_node("gatekeeper", run_gatekeeper)
    graph.add_node("merger", run_merger)

    # 2. 엣지 연결 (순차 진행 및 조건부 루프)
    graph.set_entry_point("drafter")
    graph.add_edge("drafter", "researcher")
    graph.add_edge("researcher", "expander")
    graph.add_edge("expander", "reviewer")
    graph.add_edge("reviewer", "gatekeeper")

    graph.add_conditional_edges(
        "gatekeeper",
        route_after_gatekeeper,
        {
            "researcher": "researcher",
            "merger": "merger",
        },
    )

    graph.add_edge("merger", END)
    return graph


def build_workflow_app(checkpoint_db_path: str | None = None) -> Any:
    """체크포인터가 바인딩된 컴파일된 LangGraph 애플리케이션 반환."""
    db_path = checkpoint_db_path or os.getenv(
        "LANGGRAPH_CHECKPOINT_DB", "workspace/checkpoints/report_pipeline.sqlite"
    )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()

    graph = create_report_graph()
    return graph.compile(checkpointer=checkpointer)

