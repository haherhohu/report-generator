# src/agents/drafter.py
import yaml
import json
import re

from langchain_core.prompts import ChatPromptTemplate
from src.report_types import get_required_chapter_titles, normalize_report_type
from src.utils.file_manager import save_file_append_only, build_report_artifact_path, register_artifact, coerce_llm_text
from src.utils.model_client import build_llm
from src.utils.parser import extract_text_smartly
from src.utils.prompting import invoke_prompt


DEFAULT_REQUIRED_CHAPTER_TITLES = get_required_chapter_titles()


def _resolve_required_chapter_titles(report_type=None, direction=None):
    return get_required_chapter_titles(report_type=report_type, direction=direction)

def _extract_sections_from_draft(markdown_text):
    """초안 마크다운에서 챕터 섹션 구조를 추출합니다."""
    header_pattern = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
    matches = []
    for m in header_pattern.finditer(markdown_text):
        header_level = len(m.group(1))
        raw_title = m.group(2).strip()
        if header_level > 2:
            continue

        chapter_match = re.match(
            r"^(?:(\d+)\s*장(?:\s+|$)(.*)|(\d+)\s*[\.\)]\s*(?!\d+[\.\)])(.*))$",
            raw_title,
        )
        if not chapter_match:
            continue
        chapter_num_text = chapter_match.group(1) or chapter_match.group(3)
        chapter_num = int(chapter_num_text)
        chapter_name = (chapter_match.group(2) or chapter_match.group(4) or "").strip()
        normalized_title = f"{chapter_num}장 {chapter_name}".strip()
        matches.append((m.start(), m.end(), normalized_title, chapter_num))

    sections = []

    for idx, match in enumerate(matches):
        start_pos, end_pos, title, section_index = match

        start = end_pos
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(markdown_text)
        summary = markdown_text[start:end].strip()[:1000]

        sections.append(
            {
                "title": title,
                "section_index": section_index,
                "previous_summary": summary,
            }
        )

    return sections


def _extract_chapter_body_map(markdown_text):
    """초안 본문에서 장 번호별 원문 일부를 추출합니다."""
    header_pattern = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
    matches = []

    for m in header_pattern.finditer(markdown_text):
        header_level = len(m.group(1))
        if header_level > 2:
            continue
        raw_title = m.group(2).strip()
        chapter_match = re.match(
            r"^(?:(\d+)\s*장(?:\s+|$)(.*)|(\d+)\s*[\.\)]\s*(?!\d+[\.\)])(.*))$",
            raw_title,
        )
        if not chapter_match:
            continue
        chapter_num_text = chapter_match.group(1) or chapter_match.group(3)
        chapter_num = int(chapter_num_text)
        matches.append((m.start(), m.end(), chapter_num))

    chapter_body_map = {}
    for idx, match in enumerate(matches):
        start_pos, end_pos, chapter_num = match
        start = end_pos
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(markdown_text)
        body = markdown_text[start:end].strip()
        if body:
            chapter_body_map[chapter_num] = body
    return chapter_body_map


def _normalize_sections_to_required(sections, topic, direction, report_type=None):
    """초안 섹션을 표준 구조로 정규화합니다."""
    required_titles = _resolve_required_chapter_titles(report_type, direction)
    chapter_indices = sorted(required_titles)
    by_chapter = {}
    for section in sections:
        chapter_num = section.get("section_index")
        if isinstance(chapter_num, int) and chapter_num not in by_chapter:
            by_chapter[chapter_num] = section

    normalized = []
    for chapter_num in chapter_indices:
        if chapter_num in by_chapter:
            existing = dict(by_chapter[chapter_num])
            existing["title"] = required_titles.get(chapter_num, existing.get("title", f"{chapter_num}장"))
            existing["section_index"] = chapter_num
            existing["previous_summary"] = (existing.get("previous_summary") or "").strip()
            normalized.append(existing)
            continue

        normalized.append(
            {
                "title": required_titles[chapter_num],
                "section_index": chapter_num,
                "previous_summary": (
                    f"초안에 {chapter_num}장 본문이 누락되어 기초 골격으로 추가된 장임. "
                    f"주제 '{topic}' 및 방향성 '{direction}'에 맞춰 본문 보강이 필요함."
                )[:1000],
            }
        )
    return normalized


def _build_foundation_markdown(topic, direction, normalized_sections, chapter_body_map, report_type=None):
    """기존 초안을 기반으로 보고서 종류에 맞는 기초 보고서를 생성합니다."""
    required_titles = _resolve_required_chapter_titles(report_type, direction)
    lines = [
        f"# {topic}",
        "",
        "## 작성 메모",
        f"- 본 문서는 기존 초안을 기반으로 {len(required_titles)}장 구조를 정렬한 기초 보고서임.",
        f"- 핵심 방향성: {direction}",
        "",
    ]

    for section in normalized_sections:
        chapter_num = section["section_index"]
        title = section["title"]
        lines.append(f"## {title}")
        lines.append("")

        existing_body = (chapter_body_map.get(chapter_num, "") or "").strip()
        if existing_body:
            lines.append(existing_body)
            lines.append("")
            continue

        summary = (section.get("previous_summary") or "").strip()
        lines.append(
            "[기초 본문] 기존 초안에서 해당 장의 완성 본문이 확인되지 않아, 파이프라인 보강 대상으로 등록함."
        )
        if summary:
            lines.append(f"- 요약 단서: {summary}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_drafter(state):
    # 초안 작성 로직
    state["report_type"] = normalize_report_type(state.get("report_type"), direction=state.get("direction"))
    print(f"  [Drafter] '{state['topic']}' 분석 및 기획 시작... (report_type={state['report_type']})")

    # 1. 설정 및 프롬프트 로드
    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("prompts/drafter_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
        
    # config에 지정된 모델 호출 (기본값 설정 포함)
    drafter_config = config.get("drafter", {})
    model_name = drafter_config.get("model", "gpt-4o-mini")

    # 2. LLM 인스턴스화: provider별 키/엔드포인트 설정 적용
    llm = build_llm(
        agent_name="drafter",
        agent_config=drafter_config,
        default_model=model_name,
        temperature=0.2,
    )

    # [A] 백지 모드: 초안이 없을 때 전체 뼈대 작성
    if state.get("is_blank_slate"):
        print("    -> [모드] 기초 자료 없음. 전체 목차 초안 작성(백지 모드) 실행.")
        with open("prompts/drafter_prompt.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "보고서 주제: {topic}\n요구 방향성: {direction}\n\n위 내용을 바탕으로 보고서의 핵심 뼈대(목차 및 섹션별 간략한 요약)를 마크다운으로 작성해 주세요.\n반드시 각 장 제목은 '## 1장 ...', '## 2장 ...' 형식으로 작성해 주세요.")
        ])
        
        # 3. 프롬프트 체인 구성 및 실행    
        response = (prompt | llm).invoke({"topic": state["topic"], "direction": state["direction"]})
        
        # 스마트 텍스트 추출기 통과
        draft_content = extract_text_smartly(response.content)

        # 4. 파일 저장 (Append-Only 규칙 적용)
        # 파일명에 띄어쓰기가 있을 경우 언더스코어로 치환하여 저장 안정성 확보
        safe_topic = state['topic'].replace("/", "_")
        file_path = build_report_artifact_path(state['topic'], "v1")
        saved_path = save_file_append_only(file_path, draft_content)
        register_artifact(state, artifact_type="draft", title="초안 v1", path=saved_path)
        sections = _extract_sections_from_draft(draft_content)

        # 섹션 추출 실패 대비 빈 껍데기 주입
        extracted_ids = {sec.get("section_index") for sec in sections if sec.get("section_index")}
    
        # 추출에 실패한 챕터는 빈 껍데기로 강제 주입
        for i in range(1, 10):
            if i not in extracted_ids:
                sections.append({
                    "title": f"{i}장", 
                    "section_index": i, 
                    "content": "", 
                    "previous_summary": ""
                })
                
        sections.sort(key=lambda x: x.get("section_index", 99))
        state["sections"] = sections # 혹은 정규화 함수 통과 후 저장

        if not sections:
            raise ValueError("[Drafter] 초안에서 섹션 제목(예: '## 1장 ...')을 추출하지 못했습니다.")
        state["sections"] = _normalize_sections_to_required(
            sections,
            topic=state["topic"],
            direction=state.get("direction", ""),
            report_type=state.get("report_type"),
        )
        
        # 5. 상태(State)에 결과 파일 경로 기록 후 반환
        print(f"    -> [완료] 초안 저장 경로: {saved_path}")
        print(f"    -> [완료] 추출된 섹션 수: {len(sections)}개")
        # print(f"  [Drafter] 초안 작성 완료. 저장 경로: {saved_path}")
        
    # [B] 보강 모드: 기존 초안 기반 갭 분석 및 타겟 키워드 추출
    else:
        print("    -> [모드] 초안 감지됨. 강제 재구조화(v1 생성) 및 타겟 키워드 추출 실행.")
        
        # 주입된 초안 텍스트 취합 (토큰 초과 방지를 위해 최대 8,000자로 제한)
        draft_chunks = []
        for item in state.get("source_materials", []):
            if isinstance(item, dict):
                draft_chunks.append(item.get("content", ""))
            elif isinstance(item, str):
                draft_chunks.append(item)
        draft_content = "\n".join(draft_chunks)
        safe_draft_content = draft_content[:8000] 

        # =================================================================
        # [PATCH] 1. 거친 원문을 무시하고 LLM을 통해 규격화된 v1 초안 강제 생성
        # =================================================================
        print("    -> [실행] 파편화된 기초 자료를 해체하여 1~9장 표준 규격의 v1 초안으로 재작성합니다.")
        
        redraft_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + """
            
            사용자가 파편화된 기초 자료(거친 초안)를 제공했습니다. 
            당신의 임무는 이 자료를 그대로 복사하는 것이 아니라, 제공된 자료를 철저히 해체하고 분석하여 '1장부터 9장까지의 표준 목차 구조'에 맞게 완전히 새롭게 재조립된 1차 초안(v1)을 마크다운으로 작성하는 것입니다.
            자료에 내용이 부족한 장은 뼈대와 향후 조사 방향성만 간략히 적으십시오.
            각 장 제목은 반드시 '## 1장 ...', '## 2장 ...' 형식으로 작성하십시오."""),
            ("human", "보고서 주제: {topic}\n요구 방향성: {direction}\n\n[제공된 기초 자료]\n{draft_content}")
        ])
                
        redraft_response = (redraft_prompt | llm).invoke({
            "topic": state["topic"], 
            "direction": state["direction"],
            "draft_content": safe_draft_content
        })
        
        draft_content_v1 = extract_text_smartly(redraft_response.content)
        
        safe_topic = state["topic"].replace(" ", "_").replace("/", "_")

        # =================================================================
        # Step 1. 기초 초안(v1) 무조건 생성
        # =================================================================
        print("    -> [실행] Step 1: 방향성에 맞춘 1~9장 표준 기초 초안(v1) 생성 시작")
        
        v1_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + """
            당신의 임무는 주제와 방향성을 바탕으로 1장부터 9장까지의 표준 목차 구조를 갖춘 최초 기획 초안(v1)을 작성하는 것입니다.
            각 장 제목은 반드시 '## 1장 서론', '## 2장 필요성' 등 지정된 숫자로 시작해야 합니다.
            내용은 핵심 뼈대 위주로 서술하십시오."""),
            ("human", "보고서 주제: {topic}\n요구 방향성: {direction}")
        ])

        v1_response = (v1_prompt | llm).invoke({"topic": state["topic"], "direction": state["direction"]})
        draft_v1_content = extract_text_smartly(v1_response.content)
        
        v1_path = build_report_artifact_path(state['topic'], "v1")
        save_file_append_only(v1_path, draft_v1_content)
        register_artifact(state, artifact_type="draft", title="초안 v1", path=v1_path)
        print(f"    -> [완료] 기초 초안(v1) 저장: {v1_path}")
        # 기본 타겟 초안은 v1으로 설정
        target_draft_content = draft_v1_content

        # =================================================================
        # [PATCH] 2. 새로 생성된 v1 초안을 바탕으로 섹션 배열 추출
        # Step 2. 사용자 자료 반영을 통한 초안 확장(v2)
        # =================================================================
        if not state.get("is_blank_slate") and state.get("source_materials"):
            print("    -> [실행] Step 2: 사용자 제공 자료를 반영한 업데이트 초안(v2) 생성 시작")
            
            draft_chunks = [item.get("content", "") if isinstance(item, dict) else str(item) for item in state.get("source_materials", [])]
            safe_source_content = "\n".join(draft_chunks)[:8000] # 토큰 방어
            
            v2_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt + """
                당신의 임무는 제공된 '기초 초안(v1)'의 1~9장 목차 구조를 완벽히 유지한 상태에서, 함께 제공된 '사용자 기초 자료'의 팩트와 데이터를 각 장의 적절한 위치에 주입하여 살을 찌운 '업데이트 초안(v2)'을 작성하는 것입니다.
                자료가 없는 장은 기존 v1의 내용을 유지하십시오."""),
                ("human", "보고서 주제: {topic}\n\n[기초 초안 v1]\n{v1_content}\n\n[사용자 기초 자료]\n{source_content}")
            ])
            
            v2_response = (v2_prompt | llm).invoke({
                "topic": state["topic"], 
                "v1_content": draft_v1_content, 
                "source_content": safe_source_content
            })
            
            target_draft_content = extract_text_smartly(v2_response.content)
            
            v2_path = build_report_artifact_path(state['topic'], "v2")
            save_file_append_only(v2_path, target_draft_content)
            register_artifact(state, artifact_type="draft", title="초안 v2", path=v2_path)
            print(f"    -> [완료] 업데이트 초안(v2) 저장: {v2_path}")

        
        # =================================================================
        # Step 3. 최종 초안 기반 섹션 추출 및 타겟 키워드 추출 로직
        # =================================================================
        # 최종 타겟 초안(v2, 자료가 없으면 v1)을 바탕으로 섹션 규격화
        sections = _extract_sections_from_draft(target_draft_content)

        # =================================================================
        # [PATCH 3] 추출 실패 시 빈 껍데기라도 1~9장을 무조건 강제 주입
        # =================================================================
        extracted_ids = {sec.get("section_index") for sec in sections if sec.get("section_index")}
        
        for i in range(1, 10):
            if i not in extracted_ids:
                print(f"    -> [경고] {i}장 추출 실패. 빈 껍데기를 강제 생성하여 파이프라인에 주입합니다.")
                sections.append({
                    "title": f"{i}장", 
                    "section_index": i, 
                    "content": "", 
                    "previous_summary": ""
                })
                
        # 인덱스 순서대로 재정렬
        sections.sort(key=lambda x: x.get("section_index", 99))
        
        # 정규화 후 상태에 저장
        state["sections"] = _normalize_sections_to_required(sections, topic=state["topic"], direction=state["direction"])

        print("    -> [실행] Step 3: 최종 초안 기반 심층 조사 키워드 추출")

        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 수석 기획자입니다. 제공된 초안을 분석하고, 사용자가 제시한 '방향성'과 '타겟 관점'을 철저히 반영하여 추가 조사가 필요한 심층 키워드(조사 항목) 5~8개를 도출하십시오.
            
            [필터링 제약 조건]
            1. 타겟 관점(Perspective)에 어긋나는 키워드는 배제하여도 좋습니다.
            2. 필수 키워드(예: Vantis, FAA)는 단순 명사가 아닌, 타겟 관점에 맞춘 구체적인 질문/조사 항목 형태(예: 'Vantis의 민간 항로 관제 C2 네트워크 안전성 검증 사례')로 변환하십시오.
            3. 본문 팽창을 위해 5~8개의 키워드를 도출하고, 반드시 파이썬 리스트 형태(예: ["키워드1", "키워드2"])의 순수 JSON 배열로만 출력하십시오. 코드 블록(```)은 제외합니다."""),
            ("human", """방향성: {direction}
            타겟 관점: {target_perspective}
            초안 텍스트: {draft_content}""")
        ])            

        # 3. 프롬프트 체인 구성 및 실행    
        response = (prompt | llm).invoke({
            "direction": state["direction"],
            "target_perspective": state.get("target_perspective", "일반"),
            "draft_content": target_draft_content
        })

        # 안정적인 JSON 파싱 및 예외 처리 (환각 방지)
        try:
            response_text = coerce_llm_text(response.content)
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            state["keywords"] = json.loads(match.group(0)) if match else ["기본 키워드 폴백"]
        except Exception:
            state["keywords"] = ["관련 법령 및 규제 동향", "국내외 유사 구축 사례", "핵심 기술 요소 검증"]
            
        print(f"    -> [분석 완료] 도출된 키워드: {state['keywords']}")

        # state 업데이트 보강
        state["foundation_report_path"] = v2_path if not state.get("is_blank_slate") else v1_path

    return state # 상태를 그대로 다음 노드로 넘김    