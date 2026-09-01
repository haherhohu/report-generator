# src/agents/researcher.py
import yaml
from langchain_core.prompts import ChatPromptTemplate
from src.utils.file_manager import save_file_append_only, build_report_artifact_path, register_artifact
from src.utils.final_report_guard import should_reuse_or_create_final
from src.tools.web_search import perform_hybrid_research
from tenacity import retry, wait_exponential, stop_after_attempt
from src.utils.model_client import build_llm

# API 셧다운 방지를 위한 지수 백오프 재시도 데코레이터 (최대 3회, 대기시간 점진적 증가)
@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def invoke_llm_with_retry(chain, inputs):
    try:
        return chain.invoke(inputs)
    except Exception as e:
        print("\n================ [에러 추적 리포트] ================")
        print(f"1. 에러 원문: {str(e)}")
        
        # 체인 내부에 바인딩된 LLM 객체에서 모델명 추출
        try:
            # chain이 프롬프트|LLM 구조일 경우 step 뒤쪽에 LLM이 있음
            llm_step = chain.last if hasattr(chain, 'last') else chain
            if hasattr(llm_step, 'model_name'):
                print(f"2. 전송된 모델명: {llm_step.model_name}")
            else:
                print("2. 전송된 모델명: (직접 속성 확인 불가)")
        except:
            pass
        print("====================================================\n")
        
        # tenacity가 재시도할 수 있도록 에러를 다시 던짐
        raise e


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
    model_name = researcher_config.get("model", "google/gemma-4-31b-it")
    
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
    keyword_search_cache = state.setdefault("keyword_search_cache", {})

    for keyword in keywords:
        print(f"    - '{keyword}' 키워드 검색 중...")

        final_state = should_reuse_or_create_final(
            state,
            title=keyword,
            related_paths=[entry.get("path") for entry in state.get("artifact_history", []) or [] if str(entry.get("title", "")).strip() == str(keyword).strip()],
            duplicate_threshold=5,
            summary_only=True,
        )
        if final_state["used_final"]:
            state.setdefault("report_final_paths", {})[keyword] = final_state["path"]
            state.setdefault("source_materials", []).append({
                "filename": f"research_{keyword}_final.md",
                "content": final_state["content"],
                "path": final_state["path"],
            })
            print(f"    -> [재사용] '{keyword}' 이미 존재하는 최종본을 사용합니다. ({final_state['path']})")
            continue
        if final_state.get("triggered_duplicate"):
            final_path = build_report_artifact_path(keyword, "final", base_dir="workspace/reference")
            final_saved_path = save_file_append_only(final_path, final_state["content"])
            register_artifact(state, artifact_type="final-report", title=f"{keyword} 최종 요약본", path=final_saved_path)
            state.setdefault("report_final_paths", {})[keyword] = final_saved_path
            state.setdefault("source_materials", []).append({
                "filename": f"research_{keyword}_final.md",
                "content": final_state["content"],
                "path": final_saved_path,
            })
            print(f"    -> [최종본 생성] '{keyword}' 최종 요약본을 생성했습니다. ({final_saved_path})")
            continue

        # 실제 웹 검색 수행
        search_query = f"{state['topic']} {keyword} 최신 동향"
        raw_search_results = search_with_retry(search_query)
        previous_cache = keyword_search_cache.get(keyword)
        keyword_search_cache[keyword] = str(raw_search_results)
        if previous_cache == keyword_search_cache[keyword]:
            print(f"    -> [중복 차단] '{keyword}' 검색 결과가 이전과 동일하여 최종본 재사용 경로로 전환합니다.")
            final_path = build_report_artifact_path(keyword, "final", base_dir="workspace/reference")
            reuse_content = should_reuse_or_create_final(state, title=keyword, related_paths=[item.get("path") for item in state.get("artifact_history", []) or [] if str(item.get("title", "")).strip() == str(keyword).strip()], duplicate_threshold=5, summary_only=True)
            if reuse_content["used_final"]:
                state.setdefault("report_final_paths", {})[keyword] = reuse_content["path"]
                continue
            if reuse_content.get("triggered_duplicate"):
                final_saved_path = save_file_append_only(final_path, reuse_content["content"])
                register_artifact(state, artifact_type="final-report", title=f"{keyword} 최종 요약본", path=final_saved_path)
                state.setdefault("report_final_paths", {})[keyword] = final_saved_path
                continue

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
        file_path = build_report_artifact_path(keyword, "research", base_dir="workspace/reference")
        saved_path = save_file_append_only(file_path, content)
        register_artifact(state, artifact_type="research-note", title=f"{keyword} 조사", path=saved_path)
        collected_materials.append(
            {"filename": f"research_{keyword}.md", "content": content, "path": saved_path}
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
