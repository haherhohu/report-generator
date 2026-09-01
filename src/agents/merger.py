import os

from src.report_types import get_required_chapter_titles, normalize_report_type
from src.utils.file_manager import save_file_append_only, build_report_artifact_path, register_artifact
from src.utils.final_report_guard import get_final_path_for_title, read_text_if_exists


DEFAULT_REQUIRED_CHAPTER_TITLES = get_required_chapter_titles()


def _normalize_expanded_sections(expanded_sections, report_type=None, direction=None):
    required_titles = get_required_chapter_titles(report_type=report_type, direction=direction)
    by_index = {}
    for section in expanded_sections or []:
        idx = section.get("section_index")
        if isinstance(idx, int) and idx not in by_index:
            by_index[idx] = section

    normalized = []
    for idx in sorted(required_titles):
        if idx in by_index:
            normalized.append(by_index[idx])
            continue

        normalized.append(
            {
                "title": required_titles[idx],
                "section_index": idx,
                "content": (
                    f"## {required_titles[idx]}\n\n"
                    "[자동 보강 메모] 해당 장은 생성 결과가 누락되어 기본 플레이스홀더를 삽입함."
                ),
            }
        )
    return normalized


def run_merger(state):
    state["report_type"] = normalize_report_type(state.get("report_type"), direction=state.get("direction"))
    print(f"  [Merger] '{state['topic']}' 최종 보고서 병합 및 참고문헌 자동 생성 시작... (report_type={state['report_type']})")

    existing_final = state.get("final_report_path")
    if existing_final and os.path.exists(existing_final):
        print(f"    -> [재사용] 기존 최종 보고서가 존재하여 재사용합니다. ({existing_final})")
        return state

    sections = state.get('expanded_sections', [])
    if not sections:
        raise ValueError("[Merger] 병합할 챕터 데이터가 없습니다. 파이프라인 오류입니다.")

    # 1. 목차 순서에 맞게 섹션 정렬 (section_index 기준/비동기 처리로 뒤섞인 순서 복구)
    sections = _normalize_expanded_sections(sections, report_type=state.get("report_type"), direction=state.get("direction"))
    for section in sections:
        title = section.get('title')
        if not title:
            continue
        section_final_path = state.get('section_final_paths', {}).get(title) or get_final_path_for_title(state, title=title)
        if section_final_path and os.path.exists(section_final_path):
            section['content'] = read_text_if_exists(section_final_path)
    sections.sort(key=lambda x: x.get('section_index', 99))

    # 2. 내용 취합 (가감 및 요약 일절 금지)
    merged_content = f"# {state['topic']}\n\n"

    # 보고서 종류에 맞는 장들만 취합
    for section in sections:
        merged_content += f"{section.get('content', '')}\n\n"

    report_title = get_required_chapter_titles(report_type=state.get("report_type"), direction=state.get("direction"))
    last_reference_title = "9장 참고문헌, 약어표" if report_title.get(9) else "7장 통계 및 참고자료"
    merged_content += f"---\n\n## {last_reference_title}\n\n"

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

    # 3. 최종 파일 저장 (Append-Only 규칙 적용)
    file_path = build_report_artifact_path(state['topic'], 'v3_final')
    saved_path = save_file_append_only(file_path, merged_content)
    register_artifact(state, artifact_type='final-report', title='최종 보고서', path=saved_path)

    state["final_report_path"] = saved_path
    print(f"  [Merger] ✅ 최종 보고서 취합 완료. 저장 경로: {saved_path}")

    return state # 상태를 그대로 다음 노드로 넘김


