import os
from src.utils.file_manager import save_file_append_only


REQUIRED_CHAPTER_TITLES = {
    1: "1장 서론",
    2: "2장 필요성",
    3: "3장 사례 연구/분석",
    4: "4장 전략 및 정책 제언",
    5: "5장 수행내역(세부과제)",
    6: "6장 추진체계/일정 및 예산",
    7: "7장 기대효과 및 결론",
    8: "8장 부록 (통계 및 법령 등)",
    9: "9장 참고문헌, 약어표",
}


def _normalize_expanded_sections(expanded_sections):
    by_index = {}
    for section in expanded_sections or []:
        idx = section.get("section_index")
        if isinstance(idx, int) and idx not in by_index:
            by_index[idx] = section

    normalized = []
    for idx in range(1, 10):
        if idx in by_index:
            normalized.append(by_index[idx])
            continue

        normalized.append(
            {
                "title": REQUIRED_CHAPTER_TITLES[idx],
                "section_index": idx,
                "content": (
                    f"## {REQUIRED_CHAPTER_TITLES[idx]}\n\n"
                    "[자동 보강 메모] 해당 장은 생성 결과가 누락되어 기본 플레이스홀더를 삽입함."
                ),
            }
        )
    return normalized

def run_merger(state):
    # 병합 로직
    print(f"  [Merger] '{state['topic']}' 최종 보고서 병합 및 참고문헌 자동 생성 시작...")
    
    sections = _normalize_expanded_sections(state.get('expanded_sections', []))
    # 1. 목차 순서에 맞게 섹션 정렬 (비동기 처리로 뒤섞인 순서 복구)
    sections.sort(key=lambda x: x.get('section_index', 99))
    
    # 2. 내용 취합 (가감 및 요약 일절 금지)
    merged_content = f"# {state['topic']}\n\n"
    
    # 3. 1장~8장 내용 취합
    for section in sections:
        # 각 챕터 사이에 명확한 구분을 위한 수평선 삽입
        merged_content += f"---\n\n"
        merged_content += f"{section.get('content', '')}\n\n"
        
    # 2. 9장(참고문헌) 기계적 자동 생성 및 부착 (LLM 환각 원천 차단)
    merged_content += f"---\n\n## 9장 참고문헌\n\n"

    # 기초 자료 파일명 취합
    source_files = [item['filename'] for item in state.get('source_materials', [])]
    # 자료조사 에이전트가 생성한 레퍼런스(또는 URL) 취합
    research_refs = state.get('reference_paths', []) 
    
    all_references = set(source_files + research_refs) # 중복 제거
    
    if all_references:
        for idx, ref in enumerate(all_references, 1):
            merged_content += f"{idx}. {ref}\n"
    else:
        merged_content += "1. 제공된 기초 벤치마킹 자료 및 웹 수집 자료 일체\n"

    # 4. 최종 파일 저장 (Append-Only 규칙 적용)
    safe_topic = state['topic'].replace(" ", "_").replace("/", "_")
    file_path = f"workspace/report/{safe_topic}_v3_final.md"
    saved_path = save_file_append_only(file_path, merged_content)
    
    state["final_report_path"] = saved_path
    print(f"  [Merger] ✅ 최종 보고서 취합 완료. 저장 경로: {saved_path}")
    
    return state # 상태를 그대로 다음 노드로 넘김

    
    