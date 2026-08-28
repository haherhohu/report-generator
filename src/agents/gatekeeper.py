import re

# src/agents/gatekeeper.py
DEFAULT_SECTION_6_MIN_LENGTH = 3000
DEFAULT_TOTAL_MIN_LENGTH = 50000
DEFAULT_MAX_LOOPS = 2

def _chapter_number(title):
    text = str(title or "").strip()
    match = re.match(r"^(\d+)\s*장", text)
    return int(match.group(1)) if match else None

def check_length(sections, chapter_number):
    """특정 챕터 번호에 해당하는 섹션들의 전체 본문 길이를 합산합니다."""
    return sum(
        len(section.get("content", ""))
        for section in sections
        if _chapter_number(section.get("title")) == chapter_number
    )

def run_gatekeeper(state):
    # 루프 통제 로직
    print("  [Gatekeeper] 4~6장 코어 논리 연계 및 전체 분량 심사 시작...")

    sections = state.get('expanded_sections', [])
    if not sections:
        raise ValueError("[Gatekeeper] expanded_sections가 비어 있어 품질 심사를 진행할 수 없습니다.")

    # =================================================================
    # [PATCH 1] KeyError 방지 및 리뷰어 피드백 최우선 존중 (덮어쓰기 방지)
    # =================================================================

    # [수정] 리뷰어의 챕터 누락/재작업 지시를 최우선으로 존중 (덮어쓰기 방지)
    target_for_loop = state.get("target_sections_for_loop", [])
    if target_for_loop:
        print(f"    -> [긴급] 리뷰어 누락/수정 지시 감지: 타겟 챕터 {target_for_loop}")
        print("    -> [조치] 분량 심사를 건너뛰고 누락/수정 챕터 생성을 위해 회귀합니다.")
        # 리뷰어가 이미 state['target_sections_for_loop']에 누락 챕터를 담아두었으므로 그대로 반환
        state["next_step"] = "researcher"
        return state
    
    reviewer_feedback = state.get("reviewer_feedback", "")
    
    if "누락된 챕터" in reviewer_feedback:
        print(f"    -> [긴급] 리뷰어 누락 경고 감지: {reviewer_feedback}")
        print("    -> [조치] 챕터가 아예 없습니다! 분량 심사를 건너뛰고 누락 챕터 생성을 위해 회귀합니다.")
        state["next_step"] = "researcher"
        return state

    # =================================================================
    # [PATCH 2] 코어 논리가 0자일 경우의 방어 로직 (풍선 효과 차단)
    # =================================================================
    len_4 = check_length(sections, 4)
    len_5 = check_length(sections, 5)
    len_6 = check_length(sections, 6)
    core_total_length = len_4 + len_5 + len_6
    
    # 만약 코어가 0자라면, 분량이 부족한 게 아니라 생성 자체가 안 된 비정상 상태입니다.
    if core_total_length == 0:
        print("    -> [오류] 4~6장 코어 논리가 0자입니다. (생성 누락)")
        print("    -> [조치] 2,3,7장 팽창을 취소하고 4~6장 생성을 강제합니다.")
        state['target_sections_for_loop'] = [4, 5, 6]
        state['next_step'] = "researcher"
        return state

    loop_targets = [] # 재보강(루프)을 지시할 챕터 목록

   
    # 1. 4~5장 (코어 전략) 방어율 체크
    core_content = "".join(
        [s.get("content", "") for s in sections if _chapter_number(s.get("title")) in {4, 5}]
    )
    core_has_tables = "|" in core_content # 마크다운 표 포함 여부 
    core_has_images = "[이미지 프롬프트" in core_content
    
    # 4, 5장이 어느 정도 구조화(표/이미지)를 갖췄다면 텍스트 분량이 다소 적어도 절대 루프시키지 않음 (환각 방지)
    if core_has_tables and core_has_images:
        print("    -> [통과] 4~5장 논리적 구조화 및 시각화 방어 확인. (환각 리스크 차단)")

     # 1. [수정된 로직] 4, 5, 6장을 하나의 유기적인 코어 블록으로 합산 평가
    len_4 = check_length(sections, 4)
    len_5 = check_length(sections, 5)
    len_6 = check_length(sections, 6)
    core_total_length = len_4 + len_5 + len_6

    # config의 target_6_min_length(3000)를 기준으로 3개 장의 합산 목표치를 33000으로 설정
    # 최소 4장 30장 5장 40장에 6장 5장 정도를 본다면 
    # 2. 4-6~7장 연동 분량 체크
    # 4-6장이 팩트 위주라 짧다면, 7장(기대효과)을 루프 타겟으로 지정하여 부풀림
    target_single = state.get("target_6_min_length", DEFAULT_SECTION_6_MIN_LENGTH)
    target_core_total = target_single * 15

    # 회장님 지시사항: 코어 블록이 목표치의 70% 미만일 경우 주변부 확장
    threshold_70 = target_core_total * 0.7 

    if core_total_length < threshold_70:
        print(f"    -> [판단] 4~6장 코어 논리 분량 부족 (현재 {core_total_length}자 / 목표 70% {threshold_70}자 미달).")
        print("    -> [조치] 4~6장 억지 확장에 따른 환각 방지. 2장(배경), 3장(사례), 7장(기대효과)을 확장하여 전체 논리 보강 지시.")
        loop_targets.extend(['2장', '3장', '7장'])
    else:
        print(f"    -> [통과] 4~6장 코어 논리 분량 확보 (현재 {core_total_length}자).")

    # 2. 전체 분량 방어 (설정값 100,000자 기준) (2~3장에 전가)
    total_length = sum(len(s.get('content', '')) for s in sections)
    # total_length = sum(len(s['content']) for s in sections)
    target_total = state.get("target_total_min_length", DEFAULT_TOTAL_MIN_LENGTH)
    
    if total_length < target_total:
        print(f"    -> [판단] 전체 분량 미달 (현재 {total_length}자 / 목표 {target_total}자). 2~3장에 신규 조사 키워드 투입.")
        loop_targets.extend(['2장', '3장'])

        
    # 3. 상태 분기 및 루프 제어
    max_loops = state.get("max_loops", DEFAULT_MAX_LOOPS)
    loop_targets = list(dict.fromkeys(loop_targets)) # 중복 제거
    
    if loop_targets and state.get('loop_count', 0) < max_loops:
        state['loop_count'] += 1
        state['target_sections_for_loop'] = loop_targets # 특정 챕터만 다시 돌리도록 상태 저장
        # state['target_sections_for_loop'] = list(dict.fromkeys(loop_targets)) 
        state["next_step"] = "researcher"
        print(f"    -> [루프 진입] {loop_targets} 보강을 위해 Researcher로 회귀 (현재 루프 {state['loop_count']}/{max_loops})")
        return state # 필요한 자료조사부터 재실행
        
    print("    -> [승인] 모든 제약 조건 통과(또는 루프 소진). 최종 검토 단계로 이동.")
    state["next_step"] = "merger"

    return state # 상태를 그대로 다음 노드로 넘김
    
    