import os
import sqlite3

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import ReportState
from src.agents.drafter import run_drafter
from src.agents.researcher import run_researcher
from src.agents.expander import run_expander
from src.agents.reviewer import run_reviewer
from src.agents.merger import run_merger
from src.agents.gatekeeper import run_gatekeeper

def route_after_gatekeeper(state: ReportState) -> str:
    next_step = state.get("next_step")
    # researcher로 가기 전, 리뷰어 검증을 거치도록 강제함
    if next_step == "researcher":
        return "researcher" 
    return "merger"

# 워크플로우 정의
workflow = StateGraph(ReportState)

# 노드 등록 (각 에이전트 연결)
workflow.add_node("drafter", run_drafter)
workflow.add_node("researcher", run_researcher)
workflow.add_node("expander", run_expander)
workflow.add_node("reviewer", run_reviewer)
workflow.add_node("gatekeeper", run_gatekeeper)
workflow.add_node("merger", run_merger)

# 엣지 연결 (순차적 흐름)
workflow.set_entry_point("drafter")
workflow.add_edge("drafter", "researcher")
workflow.add_edge("researcher", "expander")
workflow.add_edge("expander", "reviewer")
workflow.add_edge("reviewer", "gatekeeper")
workflow.add_conditional_edges(
    "gatekeeper",
    route_after_gatekeeper,
    {
        "researcher": "researcher",
        "merger": "merger",
    },
)

# 그리고 workflow에 리뷰어 재진입 엣지 혹은 분기 연결을 명확히 함
workflow.add_edge("merger", END)

# 그래프 컴파일
checkpoint_db_path = os.getenv("LANGGRAPH_CHECKPOINT_DB", "workspace/checkpoints/langgraph.sqlite")
os.makedirs(os.path.dirname(checkpoint_db_path), exist_ok=True)
_checkpoint_conn = sqlite3.connect(checkpoint_db_path, check_same_thread=False)
_checkpointer = SqliteSaver(_checkpoint_conn)
_checkpointer.setup()

app = workflow.compile(checkpointer=_checkpointer)