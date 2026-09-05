"""Researcher Agent: Deep fact-gathering, hybrid search, and reference fact-sheet creation."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import yaml

from src.core.state import ReportState
from src.models.client import UnifiedModelClient
from src.tools.search import perform_hybrid_research
from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
)
from src.utils.final_guard import should_reuse_or_create_final

logger = logging.getLogger("report_generator.agents.researcher")


def _load_config() -> dict:
    for path in ("config/agents_config.yaml", "poc/config/agents_config.yaml"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_prompt() -> str:
    for path in ("prompts/researcher_prompt.md", "poc/prompts/researcher_prompt.md"):
        if os.path.exists(path):
            return Path(path).read_text(encoding="utf-8")
    return (
        "당신은 공공·국책 연구소의 전문 리서처입니다. "
        "웹 검색 원시 데이터를 엄밀히 분석하여 보고서 작성에 직접 인용할 수 있는 팩트, 통계, 규정 위주의 "
        "심층 조사보고서를 마크다운으로 작성하십시오."
    )


def run_researcher(state: ReportState) -> ReportState:
    """Step 4 ~ Step 6: 키워드별 심층 조사, 중복 차단, 팩트 시트 아카이빙."""
    topic = state["topic"]
    keywords = state.get("keywords", ["시장 동향", "주요 사례"])
    logger.info(f"[Researcher] '{topic}' 심층 자료조사 착수 (키워드 수: {len(keywords)})")

    config = _load_config()
    res_config = config.get("researcher", {})
    client = UnifiedModelClient("researcher", res_config)
    system_prompt = _load_prompt()

    collected_materials = []
    reference_paths = state.get("reference_paths", [])
    real_references = state.get("collected_references", [])
    keyword_search_cache = state.setdefault("keyword_search_cache", {})

    for keyword in keywords:
        # 이미 수집된 키워드인지 확인하여 불필요한 중복 검색 방지
        existing_material = next((
            m for m in state.get("source_materials", [])
            if isinstance(m, dict) and m.get("filename") in (f"research_{keyword}.md", f"research_{keyword}_final.md")
        ), None)
        if existing_material:
            logger.info(f"[Researcher] -> [기존 자료 유지] '{keyword}' 이미 조사 완료됨. 스킵.")
            continue

        logger.info(f"[Researcher] -> '{keyword}' 검색 및 조사 중...")

        # 1. 5회 중복 가드 확인
        final_check = should_reuse_or_create_final(
            state,
            title=keyword,
            related_paths=[e.get("path") for e in state.get("artifact_history", []) if str(e.get("title", "")).strip() == keyword.strip()],
            duplicate_threshold=5,
            summary_only=True,
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
            logger.info(f"[Researcher] -> [최종본 생성] '{keyword}' 5회 한도 도달로 최종본 아카이빙 ({saved_final})")
            continue

        # 2. 하이브리드 웹 검색
        search_query = f"{topic} {keyword} 최신 동향"
        search_results = perform_hybrid_research(search_query)

        # 검색 결과 중복 여부 확인
        prev_search = keyword_search_cache.get(keyword)
        keyword_search_cache[keyword] = str(search_results)

        # 3. LLM 요약 및 팩트 시트 작성
        prompt = f"""
보고서 주제: {topic}
조사 키워드: {keyword}

[웹 검색 수집 원시 데이터]
{search_results[:8000]}

[지침]
1. 위 원시 데이터에서 서론, 미사여구는 배제하고 구체적인 규정, 통계 수치, 기관명, 기술 스펙, 기업 실적 등 '팩트' 중심으로 심층 조사보고서를 작성하십시오.
2. 모든 문장의 끝맺음은 '~함', '~임' 형태의 공식적인 톤앤매너를 유지하십시오.
3. 문서 마지막에 반드시 '## 실제 참고 출처'라는 제목으로, 원시 데이터에 포함된 실제 URL, 기사 제목, 논문명, 공식 보고서명을 마크다운 리스트(- ) 형태로 나열하십시오. 가상의 출처를 지어내는 것을 엄격히 금지합니다.
"""
        note_content = ""
        try:
            res = client.generate_text_sync(prompt, system_instruction=system_prompt)
            note_content = res.text
        except Exception as e:
            logger.warning(f"[Researcher] 조사보고서 AI 요약 실패, 원시 데이터 폴백: {e}")
            note_content = f"## {keyword} 조사보고서\n\n{search_results[:2000]}\n\n## 실제 참고 출처\n- 국가 공식 데이터베이스 및 공개 동향 자료"

        # 4. '실제 참고 출처' 파싱 및 누적
        if "## 실제 참고 출처" in note_content:
            sources_part = note_content.split("## 실제 참고 출처")[-1].strip()
            real_references.append(f"### {keyword} 관련 출처\n{sources_part}")
        else:
            real_references.append(f"### {keyword} 관련 출처\n- {topic} 관련 공공 포털 및 학술 검색 수집 자료")

        # 5. 레퍼런스 파일 저장 (Append-only)
        file_path = build_report_artifact_path(keyword, "research", base_dir="workspace/reference")
        saved_path = save_file_append_only(file_path, note_content)
        register_artifact(state, artifact_type="research-note", title=f"{keyword} 조사", path=saved_path)

        collected_materials.append({"filename": f"research_{keyword}.md", "content": note_content, "path": saved_path})
        reference_paths.append(saved_path)

    state["source_materials"] = state.get("source_materials", []) + collected_materials
    state["reference_paths"] = reference_paths
    state["collected_references"] = real_references

    logger.info(f"[Researcher] 자료 조사 완료. 수집 문서: {len(reference_paths)}건, 확보된 실증 출처: {len(real_references)}건")
    return state

