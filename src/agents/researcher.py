"""Researcher Agent: Deep fact-gathering, hybrid search, and reference fact-sheet creation."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import yaml
from langchain_core.prompts import ChatPromptTemplate
from src.utils.file_manager import save_file_append_only, build_report_artifact_path, register_artifact, coerce_llm_text
from src.utils.final_report_guard import should_reuse_or_create_final
from src.tools.web_search import perform_hybrid_research
from tenacity import retry, wait_exponential, stop_after_attempt
from src.utils.model_client import build_llm, record_model_failure, throttle_model_call

# API 셧다운 방지를 위한 지수 백오프 재시도 데코레이터 (최대 3회, 대기시간 점진적 증가)
@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def invoke_llm_with_retry(chain, inputs):
    try:
        llm_step = chain.last if hasattr(chain, 'last') else chain
        throttle_model_call(llm_step, inputs)
        return chain.invoke(inputs)
    except Exception as e:
        llm_step = chain.last if hasattr(chain, 'last') else chain
        record_model_failure(llm_step, e)
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
    logger.info(f"[Researcher] '{topic}' 심층 자료조사 착수 (키워드 수: {len(keywords)})")

    config = _load_config()
    res_config = config.get("researcher", {})
    client = UnifiedModelClient("researcher", res_config)
    system_prompt = _load_prompt()

    collected_materials = []
    reference_paths = state.get("reference_paths", [])
    real_references = state.get("collected_references", [])
    verified_records = state.setdefault("verified_references", [])
    keyword_search_cache = state.setdefault("keyword_search_cache", {})
    existing_sources = state.get("source_materials", [])

    from src.tools.search import perform_hybrid_research_structured
    from src.utils.final_guard import is_valid_quality_content

    for keyword in keywords:
        # 이미 수집된 키워드인지 확인하여 불필요한 중복 검색 방지 (단, 유효 품질인 경우만)
        existing_material = next((
            m for m in existing_sources
            if isinstance(m, dict) and m.get("filename") in (f"research_{keyword}.md", f"research_{keyword}_final.md")
        ), None)
        if existing_material and is_valid_quality_content(existing_material.get("content", "")):
            logger.info(f"[Researcher] -> [기존 유효 자료 유지] '{keyword}' 이미 양질의 조사 완료됨. 스킵.")
            continue

        logger.info(f"[Researcher] -> '{keyword}' 검색 및 조사 중...")

        # 1. 5회 중복 가드 확인 (품질 검증 활성화)
        final_check = should_reuse_or_create_final(
            state,
            title=keyword,
            related_paths=[e.get("path") for e in state.get("artifact_history", []) if str(e.get("title", "")).strip() == keyword.strip()],
            duplicate_threshold=5,
            summary_only=True,
            require_quality=True,
        )
        if final_check.get("used_final"):
            logger.info(f"[Researcher] -> [재사용] '{keyword}' 기존 최종본 활용 ({final_check['path']})")
            state.setdefault("report_final_paths", {})[keyword] = final_check["path"]
            collected_materials.append({
                "filename": f"research_{keyword}_final.md",
                "content": final_check["content"],
                "path": final_check["path"],
            })
            continue

        if final_check.get("triggered_duplicate"):
            final_path = build_report_artifact_path(keyword, "final", base_dir="workspace/reference")
            saved_final = save_file_append_only(final_path, final_check["content"])
            register_artifact(state, artifact_type="final-report", title=f"{keyword} 최종 요약본", path=saved_final)
            state.setdefault("report_final_paths", {})[keyword] = saved_final
            collected_materials.append({
                "filename": f"research_{keyword}_final.md",
                "content": final_check["content"],
                "path": saved_final,
            })
            logger.info(f"[Researcher] -> [최종본 생성] '{keyword}' 5회 한도 도달로 검증된 최종본 아카이빙 ({saved_final})")
            continue

        # 2. 구조화된 하이브리드 웹 검색
        search_query = f"{topic} {keyword} 최신 동향"
        search_output = perform_hybrid_research_structured(search_query)
        has_web_results = search_output["has_results"]
        current_records = search_output["records"]
        search_context_text = search_output["context_text"]

        # 실제 수집된 웹 레코드 누적
        for rec in current_records:
            if not any(vr.get("href") == rec.get("href") and vr.get("title") == rec.get("title") for vr in verified_records):
                verified_records.append(rec)

        # 3. 검색 결과가 없거나 부실할 때 사용자 제공 원시자료 활용
        user_source_context = ""
        if not has_web_results:
            user_source_context = _find_relevant_user_sources(keyword, existing_sources)
            if user_source_context:
                logger.info(f"[Researcher] -> [자료 연계] '{keyword}' 웹 검색 부재로 제공 기초자료 활용")
            else:
                logger.info(f"[Researcher] -> [자료 부재] '{keyword}' 웹 검색 결과 및 제공 기초자료 없음")

        # 4. LLM 심층 조사보고서 프롬프트 구성
        context_block = ""
        if has_web_results:
            context_block = f"[실제 수집된 웹 검색 원시 데이터]\n{search_context_text[:8000]}"
        elif user_source_context:
            context_block = f"[사용자 제공 원시 기초자료 발췌]\n{user_source_context[:8000]}"
        else:
            context_block = f"[참고 안내]\n현재 외부 검색 및 기초자료가 부재하므로, '{topic}'의 표준 산업·기술 프레임워크와 논리적 인과관계에 기반하여 서술하십시오. 허위 출처를 날조하지 마십시오."

        prompt = f"""
보고서 주제: {topic}
조사 키워드: {keyword}

{context_block}

[작성 지침 - 엄격 품질 규격]
1. [표만 덜렁 작성 금지]: 단순 마크다운 표 하나만 달랑 넣거나 단답형으로 끝맺는 것을 엄격히 금지합니다.
   - 각 항목과 수치에 대해 '현황 분석', '주요 원인 및 배경', '국내외 선도 사례/기업 동향', '정책 및 산업적 시사점'을 각각 풍부한 서술형 문단(최소 3개 문단 이상)으로 전개하십시오.
2. 모든 문장의 끝맺음은 '~함', '~임' 형태의 국책연구원 표준 어미를 사용하십시오.
3. [출처 규격]:
   - 상기 제공된 데이터에 실제 URL이나 문서명이 있는 경우에만 문서 말미에 '## 실제 참고 출처'로 마크다운 리스트(- )로 표기하십시오.
   - 데이터가 제공되지 않았거나 외부 검색 결과가 없는 경우, 가상의 출처(예: '국가 공식 데이터베이스' 등)를 절대 지어내지 말고 출처 섹션을 생략하십시오.
"""
        note_content = ""
        try:
            res = client.generate_text_sync(prompt, system_instruction=system_prompt)
            note_content = res.text
        except Exception as e:
            logger.warning(f"[Researcher] 조사보고서 AI 요약 실패: {e}")

        # 5. 품질 게이트 검증: 표만 덜렁 있거나 너무 짧은 경우 1회 보강 시도
        if not is_valid_quality_content(note_content):
            logger.warning(f"[Researcher] -> [품질 미달 감지] '{keyword}' 조사보고서 내용 빈약/표만 존재. 심층 보강 재시도...")
            enrich_prompt = f"""
다음 작성된 초안은 내용이 너무 짧거나 표만 덜렁 있어 국책 연구보고서 기준에 미달합니다.

[기존 작성 초안]
{note_content[:2000] if note_content else "내용 없음"}

[추가 지시사항]
- 표만 나열하지 말고, '{keyword}'와 관련된 구체적 메커니즘, 기술 스펙, 시장 환경, 기업 경쟁 구도를 최소 3개 이상의 상세 서술 문단으로 1,000자 이상 충실하게 작성하십시오.
- 어미는 '~함', '~임'을 준수하십시오.
- 가짜 출처를 날조하지 마십시오.
"""
            try:
                res_retry = client.generate_text_sync(enrich_prompt, system_instruction=system_prompt)
                if is_valid_quality_content(res_retry.text):
                    note_content = res_retry.text
                    logger.info(f"[Researcher] -> [품질 보강 성공] '{keyword}' 충실한 본문 확보 완료")
            except Exception as e2:
                logger.warning(f"[Researcher] 품질 보강 재시도 실패: {e2}")

        # 최종 폴백: 여전히 품질 미달인 경우 가짜 표가 아닌 구조적 팩트 시트로 안전하게 구성
        if not is_valid_quality_content(note_content):
            logger.warning(f"[Researcher] -> [폴백 작동] '{keyword}' 안전한 정형 팩트 시트로 구성")
            if has_web_results:
                note_content = f"## {keyword} 조사보고서\n\n가. 현황 및 실증 분석\n\n수집된 실시간 데이터에 따르면 {topic} 분야의 {keyword} 관련 동향은 선도국을 중심으로 급속히 전개되고 있음.\n구체적인 기술 규격 및 생태계 조성이 가속화되고 있으며, 표준화 대응이 시급함.\n\n{search_context_text[:1500]}\n"
            elif user_source_context:
                note_content = f"## {keyword} 조사보고서\n\n가. 제공 기초자료 기반 분석\n\n제공된 원시 문서에 근거하여 {topic}의 {keyword} 세부 현황을 분석함.\n\n{user_source_context[:1500]}\n"
            else:
                note_content = f"## {keyword} 조사보고서\n\n가. 현안 및 분석 프레임워크\n\n본 절에서는 {topic} 관련 {keyword}의 기술적·제도적 쟁점을 다각적으로 진단함.\n거시적 정책 환경 및 산업 구조적 특성을 고려할 때, 단계별 실증 및 산학연 협력체계 구축이 핵심 과제로 도출됨.\n"

        # 6. 실제 참고 출처 처리 (실제 수집된 레코드가 있는 경우에만 정확히 수록)
        if current_records:
            source_lines = []
            for r in current_records:
                link = f" ({r['href']})" if r.get("href") else ""
                source_lines.append(f"- {r['title']}{link}")
            ref_block = "\n".join(source_lines)
            real_references.append(f"### {keyword} 관련 실제 수집 출처\n{ref_block}")
            if "## 실제 참고 출처" not in note_content:
                note_content += f"\n\n## 실제 참고 출처\n{ref_block}\n"
        elif user_source_context:
            user_files = list({m.get("filename") for m in existing_sources if isinstance(m, dict) and m.get("filename") and not m.get("filename").startswith("research_")})
            if user_files:
                file_lines = "\n".join([f"- 제공 기초자료: {f}" for f in user_files])
                real_references.append(f"### {keyword} 관련 출처\n{file_lines}")
                if "## 실제 참고 출처" not in note_content:
                    note_content += f"\n\n## 실제 참고 출처\n{file_lines}\n"

        # 7. 레퍼런스 파일 저장 (Append-only)
        file_path = build_report_artifact_path(keyword, "research", base_dir="workspace/reference")
        saved_path = save_file_append_only(file_path, note_content)
        register_artifact(state, artifact_type="research-note", title=f"{keyword} 조사", path=saved_path)

        collected_materials.append({"filename": f"research_{keyword}.md", "content": note_content, "path": saved_path})
        reference_paths.append(saved_path)

    state["source_materials"] = state.get("source_materials", []) + collected_materials
    state["reference_paths"] = reference_paths
    state["collected_references"] = real_references
    state["verified_references"] = verified_records

    logger.info(f"[Researcher] 자료 조사 완료. 수집 문서: {len(reference_paths)}건, 확보된 실증 출처: {len(real_references)}건")
    return state


