
import os
from src.utils.file_manager import save_file_append_only

# LLM 클라이언트 임포트가 필요하다면 여기에 추가 (예: from langchain_... import ...)

# src/agents/reviewer.py
def run_reviewer(state):
    # 검토 로직
    print("\n=== [Reviewer] 검토 프로세스 시작 ===")
    
    # 1. 현재까지 완성된 챕터 목록 확보 (ReportState 기반)
    expanded_sections = state.get("expanded_sections", [])
    
    # dict 내에 'chapter_id'나 'title' 같은 식별자가 있다고 가정합니다.
    # (실제 데이터 구조에 맞게 키값을 조정하셔야 합니다)
    current_chapter_ids = {sec.get("chapter_id") for sec in expanded_sections if sec.get("chapter_id")}
    #current_chapter_ids = {sec.get("section_index") for sec in expanded_sections if sec.get("section_index")}

    # 2. 필수 챕터 누락 여부 검증 (Hard-coded Python Logic), 9장은 AI생성 안함.
    expected_body_ids = {1, 2, 3, 4, 5, 6, 7, 8}
    missing_body_ids = expected_body_ids - current_chapter_ids
    
    # 3. 상태 분기에 따른 피드백 및 루프 제어
    target_for_loop = state.get("target_sections_for_loop", [])
    
    if missing_body_ids:
        # 본문 챕터가 누락된 경우 -> 강제로 루프를 돌려 다시 만들어오라고 지시
        print(f"  [Reviewer] 치명적 오류: 챕터 누락 발생 {list(missing_body_ids)}")
        state["reviewer_feedback"] = f"누락된 챕터 {list(missing_body_ids)}를 반드시 포함하여 다시 생성하십시오."
        
        # 누락된 챕터를 다시 작업 목록에 밀어 넣음
        state["target_sections_for_loop"] = list(missing_body_ids)
        # Gatekeeper가 이 피드백을 보고 next_step을 'researcher'로 돌리도록 유도
        
    #elif 1 not in current_chapter_ids:
        # 본문(2~9)은 다 있는데 1장(개요)이 없는 경우 -> 1장 작성 지시
        #print("  [Reviewer] 2~9장 본문 생성 확인. 1장(종합 개요) 생성 프로세스로 진입해야 함.")
        #state["reviewer_feedback"] = "2~9장의 내용을 종합하여 1장(개요 및 요약)을 생성하십시오."
        #state["target_sections_for_loop"] = [1]
        
    else:
        # 모든 챕터(1~9)가 존재하는 경우 -> LLM을 통한 정성적 품질 평가로 진입 (필요시)
        print("  [Reviewer] 1~9장 모든 구조적 누락 없음. 품질 검토 패스.")
        state["reviewer_feedback"] = "승인(Approved). 모든 챕터가 요건을 갖추었습니다."
        state["target_sections_for_loop"] = []

    print("=== [Reviewer] 검토 완료 ===")
    return state # 상태를 그대로 다음 노드로 넘김