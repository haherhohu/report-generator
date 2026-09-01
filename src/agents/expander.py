# src/agents/expander.py
import json
import re
import yaml
import asyncio

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_openai.chat_models.base import OpenAIAPIError

from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
)
from src.utils.router import map_references_to_sections
from src.utils.model_client import build_llm
from src.utils.parser import extract_text_smartly
from src.utils.prompting import ainvoke_prompt, trim_prompt_context


DEFAULT_MAX_CONCURRENCY = 3


def _normalize_section_key(value):
    """완료 상태 비교를 위해 섹션 제목을 안전하게 정규화합니다."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[\s\-_/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_title(value):
    """입력된 섹션 제목을 저장용으로 정리합니다."""
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def _chapter_number_from_title(title):
    text = str(title or "").strip()
    if not text:
        return None
    if "장" in text:
        prefix = text.split("장", 1)[0].strip()
        if prefix.isdigit():
            return int(prefix)
    return None


def _merge_expanded_sections(existing_sections, updated_sections):
    """루프 재작성 시 전체 장 상태를 보존하면서 변경된 장만 갱신합니다."""
    merged_by_index = {}

    for section in existing_sections or []:
        chapter_num = section.get("section_index")
        if chapter_num is None:
            chapter_num = _chapter_number_from_title(section.get("title", ""))
        if chapter_num is not None:
            merged_by_index[int(chapter_num)] = dict(section)

    for section in updated_sections or []:
        chapter_num = section.get("section_index")
        if chapter_num is None:
            chapter_num = _chapter_number_from_title(section.get("title", ""))
        if chapter_num is not None:
            merged_by_index[int(chapter_num)] = dict(section)

    return [merged_by_index[idx] for idx in sorted(merged_by_index.keys())]


# 503, 504 등의 OpenAIAPIError 발생 시 최대 3번, 2초~8초 간격으로 지수 백오프 재시도
@retry(
    stop=stop_after_attempt(1),
    wait=wait_exponential(multiplier=2, min=5, max=30), # API 과부하 방지를 위해 대기 시간 대폭 늘림
    retry=retry_if_exception_type(OpenAIAPIError),
    reraise=True # 3번 모두 실패하면 최종적으로 에러를 던져 파이프라인 중단
)
async def process_single_section(section_data, global_topic, global_direction, llm, system_prompt, concurrency_limit):
    """개별 섹션을 보강하는 비동기 함수 (Map 역할)"""
    """분할 정복(Divide & Conquer)이 적용된 개별 섹션 보강 비동기 함수"""
    async with concurrency_limit:
        print(f"    -> [Expander] '{section_data['title']}' 섹션 기획(Sub-TOC) 및 보강 시작...")
        
        # 1. 청킹(Chunking)된 컨텍스트 조립
        # Rule: 전체가 아닌 '해당 섹션용 자료'만 주입하여 중언부언 차단
        raw_context = section_data.get('context_data', section_data.get('reference_content', '할당된 참고 자료 없음.'))
        specific_instruction = section_data.get("specific_instruction", "지시사항을 엄격히 준수하여 섹션 본문을 작성할 것.")
        section_context = trim_prompt_context(
            raw_context,
            max_chars=max_context_chars,
            required_fragments=[
                f"전체 보고서 주제: {global_topic}",
                f"핵심 방향성: {global_direction}",
                f"지시사항: {specific_instruction}",
            ],
        )
        
        # [추가] 챕터 성격 분류 (8장 부록, 9장 참고문헌 식별)
        section_index = section_data.get("section_index", 99)
        is_data_chapter = section_index in [8, 9] or "참고문헌" in section_data['title'] or "부록" in section_data['title']

        # =================================================================
        # Step 0: 데이터 챕터 분리
        # =================================================================
        if is_data_chapter:
            print(f"      -> [우회] '{section_data['title']}'은(는) 데이터 취합 챕터이므로 세부 목차 기획을 생략합니다.")

            response = await ainvoke_prompt(
                llm,
                system_prompt,
                """
                전체 보고서 주제: {topic}
                핵심 방향성: {direction}

                [현재 섹션 참고 자료] (이 데이터를 기반으로 사실적이고 구체적으로 작성할 것)
                {section_context}

                작성할 섹션 제목: {section_title}

                지시사항:
                1. 분량을 요약하거나 축약하지 말고, 위 참고 자료의 데이터와 예시를 세분화하여 논리적으로 팽창시키시오.
                2. 모든 문장의 끝맺음은 '~함', '~임' 형태의 공식적인 톤앤매너를 유지하시오.
                3. 가독성을 위해 개조식을 적절히 혼용하되, 본문은 설명조로 구체적으로 서술하시오.
                4. 시각 자료가 필요한 위치에는 [이미지 프롬프트: 설명] 형태로 주석을 남기시오.
                """,
                topic=global_topic,
                direction=global_direction,
                section_context=section_context,
                section_title=section_data['title'],
            )

            file_path = build_report_artifact_path(global_topic, "v3", section_title=section_data['title'])
            saved_path = save_file_append_only(file_path, response.content)
            print(f"    -> [Expander] '{section_data['title']}' 완료. ({saved_path})")

            return {
                "section_id": section_data.get("section_id"),
                "title": section_data['title'],
                "section_index": section_data.get("section_index", 99),
                "draft_path": saved_path,
                "content": response.content,
            }

        # else 
        # =================================================================
        # Step 1: 세부 목차(Sub-TOC) 선행 기획
        # =================================================================
        toc_response = await ainvoke_prompt(
            llm,
            system_prompt + "\n\n당신은 수석 기획자입니다. 전체를 다 쓰지 말고 목차만 기획하십시오.",
            """
            전체 주제: {topic}
            작성할 챕터(섹션): {section_title}
            챕터별 추가 지시사항: {specific_instruction}

            [참고 자료]
            {section_context}

            지시사항:
            위 참고 자료를 바탕으로, 이 챕터 안에서 논리를 전개하기 위한 세부 목차(Sub-TOC)를 기획하십시오.
            출력은 반드시 파이썬 리스트 형태의 순수 JSON 배열로만 하십시오. (예: ["목차 1", "목차 2"])
            코드 블록(```)은 절대 사용하지 마십시오.
            """,
            topic=global_topic,
            section_title=section_data['title'],
            specific_instruction=specific_instruction,
            section_context=section_context,
        )
        
        try:
            # JSON 배열 추출 안전장치
            match = re.search(r'\[.*\]', toc_response.content, re.DOTALL)
            if match:
                sub_tocs = json.loads(match.group(0))
            else:
                raise ValueError("JSON 매칭 실패")
        except Exception as e:
            print(f"      -> [경고] Sub-TOC 파싱 실패. 강제 기본 목차로 진행합니다. ({e})")
            sub_tocs = [f"{section_data['title']} 개요", "상세 분석", "시사점 및 결론"]

        print(f"      -> 기획된 세부 목차: {sub_tocs}")

        # =================================================================
        # Step 2: 세부 목차별 순차 작성 (컨텍스트 다이어트) 및 Append-Only 저장
        # =================================================================
        file_path = build_report_artifact_path(global_topic, "v3", section_title=section_data['title'])

        accumulated_summary = section_data.get('previous_summary', '이전 섹션 내용 없음.')
        final_full_content = ""

        for sub_toc in sub_tocs:
            print(f"      -> [{section_data['title']}] '{sub_toc}' 파트 팽창 중...")
            # [추가] 데이터 챕터와 일반 챕터의 프롬프트 완전 분리
            human_prompt = """
            전체 보고서 주제: {topic}
            핵심 방향성: {direction}
            현재 챕터: {section_title}
            ★ 지금 당신이 작성할 세부 목차: {sub_toc}
            
            [이전까지의 맥락 요약] (이 내용은 중복 작성하지 말 것)
            {accumulated_summary}
            
            [현재 챕터 참고 자료]
            {section_context}
            
            지시사항:
            1. 챕터를 통째로 쓰지 마십시오! 오직 지정된 세부 목차('{sub_toc}')에 대한 본문만 작성하십시오.
            2. {specific_instruction}
            3. 참고 자료의 팩트를 바탕으로 논리를 전개하되, 억지스러운 분량 팽창은 삼가십시오.
            4. 모든 문장은 '~함', '~임'으로 끝내십시오.
            5. 제목(세부 목차)을 마크다운(###)으로 가장 상단에 한 번만 적고 내용을 시작하십시오.
            """

            content_response = await ainvoke_prompt(
                llm,
                system_prompt,
                human_prompt,
                topic=global_topic,
                direction=global_direction,
                section_title=section_data['title'],
                sub_toc=sub_toc,
                accumulated_summary=accumulated_summary,
                section_context=section_context,
                specific_instruction=specific_instruction,
            )
            
            # [수정] 껍데기 벗기기: 파일 저장 전 스마트 추출기로 순수 텍스트만 확보
            safe_content = extract_text_smartly(content_response.content)
            
            # 콘텐츠 누적 (파일 저장은 루프 종료 후 한 번만 수행)
            final_full_content += f"\n\n{safe_content}"
            
            # 컨텍스트 다이어트: 전체 글을 들고 다니지 않고, 방금 쓴 목차가 끝났다는 한 줄 메모만 누적
            accumulated_summary += f"\n- {sub_toc} : 작성 완료됨."

        # 루프 종료 후 전체 콘텐츠를 한 번에 파일로 저장
        saved_path = save_file_append_only(file_path, final_full_content.strip())
        print(f"    -> [Expander] '{section_data['title']}' 모든 세부 목차 완료. ({saved_path})")
        
        return {
            "section_id": section_data.get("section_id"),
            "title": section_data['title'],
            "section_index": section_data.get("section_index", 99),
            "draft_path": saved_path,
            "content": final_full_content # 전체 취합본을 State로 리턴
        }        
    

async def run_expander_async(state):
    """LangGraph에서 호출될 병렬 처리 래퍼 함수"""
    completed_sections = state.get('completed_sections', [])
    completed_keys = {_normalize_section_key(title) for title in completed_sections if title is not None}
    all_sections = state.get('sections', [])
    print(f"  [Expander] 총 {len(all_sections)}개 섹션 중 {len(completed_sections)}개 완료됨. 병렬 보강 시작...")

    max_concurrency = int(state.get("max_concurrency", DEFAULT_MAX_CONCURRENCY))
    concurrency_limit = asyncio.Semaphore(max(1, max_concurrency))

    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("prompts/expander_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    expander_config = config.get("expander", {})
    model_name = expander_config.get("model", "gpt-4o")
    max_input_tokens = int(expander_config.get("max_input_tokens", 8000))
    max_context_chars = max(2000, max_input_tokens // 2)

    llm = build_llm(
        agent_name="expander",
        agent_config=expander_config,
        default_model=model_name,
        temperature=0.4,
    )

    routed_sections = map_references_to_sections(
        all_sections,
        state.get('source_materials', []),
        state.get('direction', '')
    )

    loop_targets = list(state.get("target_sections_for_loop", []))
    if loop_targets:
        routed_sections = [
            s for s in routed_sections
            if any(str(s.get("title", "")).startswith(str(target)) for target in loop_targets)
        ]

    routed_sections = [
        s for s in routed_sections
        if _normalize_section_key(s.get('title')) not in completed_keys
    ]

    if not routed_sections:
        print("  [Expander] 모든 대상 섹션이 이미 완료되었습니다. 스킵합니다.")
        return state

    tasks = [
        process_single_section(
            section,
            state['topic'],
            state.get('direction', ''),
            llm,
            system_prompt,
            concurrency_limit,
        )
        for section in routed_sections
    ]
    expanded_results = await asyncio.gather(*tasks) if tasks else []

    state["expanded_sections"] = _merge_expanded_sections(
        state.get("expanded_sections", []),
        expanded_results,
    )

    normalized_completed = [
        _canonical_title(title)
        for title in completed_sections + [res['title'] for res in expanded_results]
        if title is not None
    ]
    state["completed_sections"] = list(dict.fromkeys(normalized_completed))

    for result in expanded_results:
        register_artifact(
            state,
            artifact_type="section-expanded",
            title=result.get("title", "section"),
            path=result.get("draft_path", ""),
            detail=f"section_index={result.get('section_index', 0)}",
        )

    print(f"  [Expander] {len(expanded_results)}개 섹션 보강 완료. 총 {len(state['completed_sections'])}개 섹션 완료됨.")

    return state

# LangGraph 동기(Sync) 노드 환경을 위한 브릿지 함수
def run_expander(state):
    # 병렬 섹션 보강 로직
    return asyncio.run(run_expander_async(state))