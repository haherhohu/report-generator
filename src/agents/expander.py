# src/agents/expander.py
import json
import re
import yaml
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type # 추가
from langchain_openai.chat_models.base import OpenAIAPIError # 추가
from src.utils.file_manager import save_file_append_only
from src.utils.router import map_references_to_sections
from src.utils.model_client import build_llm
from src.utils.parser import extract_text_smartly


DEFAULT_MAX_CONCURRENCY = 3


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
        section_context = section_data.get('context_data', section_data.get('reference_content', '할당된 참고 자료 없음.'))
        # previous_summary = section_data.get('previous_summary', '첫 번째 섹션입니다.')
        specific_instruction = section_data.get("specific_instruction", "지시사항을 엄격히 준수하여 섹션 본문을 작성할 것.")
        
        
        # =================================================================
        # Step 1: 세부 목차(Sub-TOC) 선행 기획
        # =================================================================
        toc_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + "\n\n당신은 수석 기획자입니다. 전체를 다 쓰지 말고 목차만 기획하십시오."),
            ("human", """
            전체 주제: {topic}
            작성할 챕터(섹션): {section_title}
            챕터별 추가 지시사항: {specific_instruction}
            
            [참고 자료]
            {section_context}
            
            지시사항:
            위 참고 자료를 바탕으로, 이 챕터 안에서 논리를 전개하기 위한 세부 목차(Sub-TOC) 3~5개를 기획하십시오.
            출력은 반드시 파이썬 리스트 형태의 순수 JSON 배열로만 하십시오. (예: ["1. 현황 및 문제점 분석", "2. 주요 사례", "3. 개선 전략 도출"])
            코드 블록(```)은 절대 사용하지 마십시오.
            """)
        ])

        # 비동기 LLM 호출
        toc_response = await (toc_prompt | llm).ainvoke({
            "topic": global_topic,
            "section_title": section_data['title'],
            "specific_instruction": specific_instruction,
            "section_context": section_context
        })
        
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
        # 파일 저장 (Append-Only)
        safe_title = section_data['title'].replace(" ", "_").replace("/", "_")
        file_path = f"workspace/report/{global_topic}_v3_{safe_title}_v1.md"
        
        accumulated_summary = section_data.get('previous_summary', '이전 섹션 내용 없음.')
        final_full_content = ""
        
        for sub_toc in sub_tocs:
            print(f"      -> [{section_data['title']}] '{sub_toc}' 파트 팽창 중...")
            
            content_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", """
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
                3. 참고 자료의 팩트를 쪼개어 구체적인 설명조로 분량을 충분히 팽창시키십시오.
                4. 모든 문장은 '~함', '~임'으로 끝내십시오.
                5. 제목(세부 목차)을 마크다운(###)으로 가장 상단에 한 번만 적고 내용을 시작하십시오.
                """)
            ])            
            # 비동기 LLM 호출
            # API 호출 (Sub-TOC 단위로 가볍게 호출)
            content_response = await (content_prompt | llm).ainvoke({
                "topic": global_topic,
                "direction": global_direction,
                "section_title": section_data['title'],
                "sub_toc": sub_toc,
                "accumulated_summary": accumulated_summary,
                "section_context": section_context,
                "specific_instruction": specific_instruction
            })
            
            # [수정] 껍데기 벗기기: 파일 저장 전 스마트 추출기로 순수 텍스트만 확보
            safe_content = extract_text_smartly(content_response.content)
            
            # 물리적 파일에 이어붙이기 (Append-Only)
            # [수정] response.content 대신 safe_content를 넘김
            saved_path = save_file_append_only(file_path, f"\n\n{safe_content}")
            final_full_content += f"\n\n{safe_content}"
            
            # 컨텍스트 다이어트: 전체 글을 들고 다니지 않고, 방금 쓴 목차가 끝났다는 한 줄 메모만 누적
            accumulated_summary += f"\n- {sub_toc} : 작성 완료됨."

        print(f"    -> [Expander] '{section_data['title']}' 모든 세부 목차 완료. ({saved_path})")
        
        return {
            "title": section_data['title'],
            "section_index": section_data.get("section_index", 99),
            "draft_path": saved_path,
            "content": final_full_content # 전체 취합본을 State로 리턴
        }        
    

async def run_expander_async(state):
    """LangGraph에서 호출될 병렬 처리 래퍼 함수"""
    print(f"  [Expander] 총 {len(state.get('sections', []))}개 섹션 병렬 보강 시작...")

    max_concurrency = int(state.get("max_concurrency", DEFAULT_MAX_CONCURRENCY))
    concurrency_limit = asyncio.Semaphore(max(1, max_concurrency))

    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("prompts/expander_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    expander_config = config.get("expander", {})
    # 팽창을 위해서는 컨텍스트 윈도우가 크고 논리력이 좋은 모델 필요
    model_name = expander_config.get("model", "gpt-4o")

    llm = build_llm(
        agent_name="expander",
        agent_config=expander_config,
        default_model=model_name,
        temperature=0.4, # 창의적인 팽창을 위해 온도 소폭 상승
    )

    # 1. 라우팅: 챕터 성격에 맞게 데이터와 지침 분배
    routed_sections = map_references_to_sections(
        state.get('sections', []), 
        state.get('source_materials', []),
        state.get('direction', '')
    )

    loop_targets = list(state.get("target_sections_for_loop", []))
    if loop_targets:
        routed_sections = [
            s
            for s in routed_sections
            # [수정된 부분] target을 강제로 문자열(str)로 변환하여 타입 에러 방지
            if any(str(s.get("title", "")).startswith(str(target)) for target in loop_targets)
        ]

    if not routed_sections:
        raise ValueError("[Expander] 보강할 섹션이 없습니다. Drafter에서 sections 생성 여부를 확인하세요.")

    # 2. 비동기(Async) Map-Reduce 실행
    full_run = not bool(loop_targets)
    if full_run:
        chapter_1_sections = [s for s in routed_sections if s.get("section_index") == 1]
        non_intro_sections = [s for s in routed_sections if s.get("section_index") != 1]

        tasks = [
            process_single_section(
                section,
                state['topic'],
                state.get('direction', ''),
                llm,
                system_prompt,
                concurrency_limit
            )
            for section in non_intro_sections
        ]
        expanded_results = await asyncio.gather(*tasks) if tasks else []

        if chapter_1_sections:
            chapter_summary = "\n".join(
                [
                    f"- {item.get('title', '')}: {(item.get('content', '')[:400]).strip()}"
                    for item in expanded_results
                ]
            )
            intro_section = dict(chapter_1_sections[0])
            intro_section["context_data"] = (
                intro_section.get("context_data", "")
                + "\n\n[2~9장 작성 결과 요약]\n"
                + chapter_summary
            )
            intro_result = await process_single_section(
                intro_section,
                state['topic'],
                state.get('direction', ''),
                llm,
                system_prompt,
                concurrency_limit,
            )
            expanded_results.append(intro_result)
    else:
        tasks = [
            process_single_section(
                section,
                state['topic'],
                state.get('direction', ''),
                llm,
                system_prompt,
                concurrency_limit
            )
            for section in routed_sections
        ]
        expanded_results = await asyncio.gather(*tasks)
    
    # 4. 상태(State) 업데이트
    state["expanded_sections"] = _merge_expanded_sections(
        state.get("expanded_sections", []),
        expanded_results,
    )
    print("  [Expander] 모든 섹션 병렬 보강 완료.")
    
    return state # 상태를 그대로 다음 노드로 넘김

# LangGraph 동기(Sync) 노드 환경을 위한 브릿지 함수
def run_expander(state):
    # 병렬 섹션 보강 로직
    return asyncio.run(run_expander_async(state))