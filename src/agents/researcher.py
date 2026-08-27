# src/agents/researcher.py
import yaml
from langchain_core.prompts import ChatPromptTemplate
from src.utils.file_manager import save_file_append_only
from src.tools.web_search import perform_hybrid_research
from tenacity import retry, wait_exponential, stop_after_attempt
from src.utils.model_client import build_llm

# API 셧다운 방지를 위한 지수 백오프 재시도 데코레이터 (최대 3회, 대기시간 점진적 증가)
@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def invoke_llm_with_retry(chain, inputs):
    return chain.invoke(inputs)


@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def search_with_retry(query):
    return perform_hybrid_research(query)


def run_researcher(state):
    # 자료 조사 로직
    print(f"  [Researcher] '{state['topic']}' 관련 기초 자료 조사 시작...")
    
    # 1. 설정 및 프롬프트 로드
    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("prompts/researcher_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
        
    researcher_config = config.get("researcher", {})
    model_name = researcher_config.get("model", "gpt-4o-mini")
    
    # 2. LLM 인스턴스화 (GitHub Models 연동 유지)
    llm = build_llm(
        agent_name="researcher",
        agent_config=researcher_config,
        default_model=model_name,
        temperature=0.3, # 팩트 위주의 서술을 위해 온도를 약간 낮춤
    )
    
    # 3. (임시) 키워드 추출 노드를 건너뛰었으므로 임의 키워드 세팅
    keywords = state.get("keywords", ["시장 동향", "주요 사례"])
    
    collected_materials = []
    reference_paths = []

    # =================================================================
    # [PATCH 1] 9장을 위한 '진짜 출처' 글로벌 리스트 초기화
    # =================================================================
    real_references = state.get("collected_references", []) 
    
    for keyword in keywords:
        print(f"    - '{keyword}' 키워드 검색 중...")
        
        # 실제 웹 검색 수행
        search_query = f"{state['topic']} {keyword} 최신 동향"
        raw_search_results = search_with_retry(search_query)

        # 4. LLM을 통한 조사 내용 요약 및 분석 체인 실행
        # =================================================================
        # [PATCH 2] 프롬프트에 '실제 참고 출처' 강제 작성 지시 추가
        # =================================================================
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """보고서 주제: {topic}
            조사 키워드: {keyword}
            
            [웹 검색 원시 데이터]
            {search_data}
            
            위 데이터를 분석하여, 본 보고서 작성에 직접적으로 인용할 수 있는 팩트 및 인사이트 위주의 조사보고서를 마크다운으로 작성해 주세요. (반드시 '~함', '~임' 체 사용)
            
            [중요 지시사항]
            문서 마지막에 반드시 '## 실제 참고 출처'라는 제목으로, 원시 데이터에 포함된 실제 URL, 기사 제목, 논문명 등을 마크다운 리스트(- ) 형태로 나열하십시오. 가상의 출처를 지어내는 것을 엄격히 금지합니다.""")
        ])
        
        chain = prompt | llm
        
        # 재시도 로직이 적용된 LLM 호출
        response = invoke_llm_with_retry(chain, {
            "topic": state["topic"],
            "keyword": keyword,
            "search_data": raw_search_results
        })

        # =================================================================
        # [PATCH 3] 응답 텍스트에서 '실제 참고 출처' 부분만 잘라내서 누적
        # =================================================================
        content = response.content
        if "## 실제 참고 출처" in content:
            sources_part = content.split("## 실제 참고 출처")[-1].strip()
            real_references.append(f"### {keyword} 관련 출처\n{sources_part}")


        # 5. 조사 결과 파일 저장 (Append-Only)
        safe_keyword = keyword.replace(" ", "_")
        file_path = f"workspace/reference/research_{safe_keyword}_v1.md"
        saved_path = save_file_append_only(file_path, content)
        collected_materials.append(
            {"filename": f"research_{safe_keyword}.md", "content": content, "path": saved_path}
        )
        reference_paths.append(saved_path)
    
    # 6. 상태(State)에 레퍼런스 경로 업데이트
    state["source_materials"] = state.get("source_materials", []) + collected_materials
    state["reference_paths"] = state.get("reference_paths", []) + reference_paths

    # =================================================================
    # [PATCH 4] 수집된 진짜 출처 리스트를 State에 저장 (Expander 9장 워커에게 전달됨)
    # =================================================================
    state["collected_references"] = real_references 

    print(f"  [Researcher] 자료 조사 완료. 수집된 문서 수: {len(reference_paths)}건, 확보된 실제 출처 블록: {len(real_references)}건")
    
    return state # 상태를 그대로 다음 노드로 넘김   
