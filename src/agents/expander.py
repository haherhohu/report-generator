"""Expander Agent: Expands sections via Sub-TOC divide-and-conquer with diagrams and tables."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
import yaml

from src.core.report_types import get_chapter_role
from src.core.state import ReportState, SectionItem
from src.models.client import UnifiedModelClient
from src.models.fallback_engine import generate_fallback_section
from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
)
from src.utils.final_guard import should_reuse_or_create_final
from src.utils.markdown_tools import (
    normalize_markdown_headings,
    sanitize_intermediate_conclusions,
    clean_markdown_text,
)
from src.utils.router import route_section_instruction

logger = logging.getLogger("report_generator.agents.expander")


def _load_config() -> dict:
    for path in ("config/agents_config.yaml", "poc/config/agents_config.yaml"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_prompt() -> str:
    for path in ("prompts/expander_prompt.md", "poc/prompts/expander_prompt.md"):
        if os.path.exists(path):
            return Path(path).read_text(encoding="utf-8")
    return (
        "당신은 대한민국 최고 수준의 국책연구기관 책임연구위원입니다. "
        "제공된 핵심 데이터와 지침을 바탕으로 엄밀한 논리 전개와 실증 데이터, "
        "도식화 인포그래픽 및 정밀 마크다운 표를 포함한 심층 본문을 작성하십시오."
    )


async def _process_single_section(
    section_data: dict[str, Any],
    topic: str,
    direction: str,
    tone: str,
    report_type: str,
    client: UnifiedModelClient,
    system_prompt: str,
    concurrency_limit: asyncio.Semaphore,
    state: ReportState,
) -> dict[str, Any]:
    """단일 절(Section) 비동기 팽창 작성 태스크."""
    async with concurrency_limit:
        sec_title = section_data.get("title", "")
        sec_num = section_data.get("section_number", "1.")
        chap_num = section_data.get("chapter_number", "1장")
        role_type = section_data.get("role_type") or get_chapter_role(report_type, chap_num)

        logger.info(f"[Expander] -> [{chap_num} {sec_num} {sec_title}] (역할: {role_type}) 팽창 착수...")

        # 1. 5회 중복 가드 확인
        guard_res = should_reuse_or_create_final(
            state,
            title=sec_title,
            related_paths=[e.get("path") for e in state.get("artifact_history", []) if str(e.get("title", "")).strip() == sec_title.strip()],
            duplicate_threshold=5,
            summary_only=False,
        )
        if guard_res.get("used_final"):
            logger.info(f"[Expander] -> [재사용] '{sec_title}' 기존 최종 섹션본 사용")
            return {
                "section_id": section_data.get("section_id"),
                "chapter_number": chap_num,
                "section_number": sec_num,
                "title": sec_title,
                "content": guard_res["content"],
                "draft_path": guard_res["path"],
            }

        # 2. 챕터 성격별 동적 라우팅 지침 획득
        ref_summary = "\n".join([
            f"- {m.get('filename')}: {m.get('content', '')[:300]}"
            for m in state.get("source_materials", [])[:6]
        ])
        route_meta = route_section_instruction(
            chapter_role=role_type,
            section_title=sec_title,
            report_type=report_type,
            tone=tone,
            direction=direction,
            source_summary=ref_summary,
        )
        specific_instruction = route_meta["specific_instruction"]

        # 3. 데이터 챕터(부록)는 Sub-TOC 기획 생략하고 바로 작성
        is_appendix = role_type in ("appendix_facts", "appendix_references")
        if is_appendix:
            fallback_text = generate_fallback_section(topic, chap_num, sec_title, role_type, tone)
            norm_content = normalize_markdown_headings(fallback_text, chap_num, sec_num, sec_title)
            file_path = build_report_artifact_path(topic, "v3", section_title=sec_title)
            saved_path = save_file_append_only(file_path, norm_content)
            register_artifact(state, artifact_type="section-expanded", title=sec_title, path=saved_path)
            return {
                "section_id": section_data.get("section_id"),
                "chapter_number": chap_num,
                "section_number": sec_num,
                "title": sec_title,
                "content": norm_content,
                "draft_path": saved_path,
            }

        # 4. Step 1: 세부 목차(Sub-TOC) 선행 기획 (기획된 핵심 토픽 및 표 기반 정밀 세분화)
        key_topics = section_data.get("key_topics", [])
        planned_tables = section_data.get("planned_tables", [])
        planned_case_studies = section_data.get("planned_case_studies", [])

        key_topics_str = "\n".join([f"- {t}" for t in key_topics]) if key_topics else f"- {sec_title} 현안 및 쟁점 분석"
        tables_str = "\n".join([f"- {t}" for t in planned_tables]) if planned_tables else "- 핵심 실증 지표 비교 분석표"
        cases_str = ("\n[기획된 선도 사례]\n" + "\n".join([f"- {c}" for c in planned_case_studies])) if planned_case_studies else ""

        is_conclusion = (role_type == "final_conclusion")
        conclusion_guideline = (
            "본 장은 보고서 전체의 대미를 장식하는 종합 결론 장이므로, 마지막 소주제는 '대정부·산업계 최종 정책 권고사항 및 종합 결론' 형태로 구성하십시오."
            if is_conclusion
            else "본 절은 본문 챕터(1~N-1장)이므로 전체 결론을 미리 내리지 말고, 마지막 소주제는 반드시 '소결: 본 절의 주요 시사점 및 연계 방향' 형태로 구성하여 절 내부 논리를 매듭지으십시오."
        )

        toc_prompt = f"""
전체 보고서 주제: {topic}
작성 대상: {chap_num} > {sec_num} {sec_title}
역할 유형: {role_type}

[기획된 핵심 토픽]
{key_topics_str}

[기획된 필수 데이터 표]
{tables_str}
{cases_str}

[작성 강령]
{specific_instruction}

[참고 데이터 요약]
{ref_summary[:3000]}

지시사항:
1. 위 기획된 핵심 토픽과 필수 데이터 표를 누락 없이 구체적으로 다루기 위해, 본 절의 세부 소주제(Sub-TOC) 3~4개를 기획하십시오.
2. {conclusion_guideline}
3. 반드시 순수 JSON 문자열 배열 형태(예: ["소주제 1", "소주제 2", "소결: 본 절의 주요 시사점 및 연계 방향"])로만 출력하십시오. 코드 블록이나 설명은 배제하십시오.
"""
        sub_tocs = []
        try:
            res_toc = await client.generate_text(toc_prompt, response_mime_type="application/json")
            m = re.search(r"\[.*\]", res_toc.text, re.DOTALL)
            if m:
                sub_tocs = json.loads(m.group(0))
        except Exception as e:
            logger.warning(f"[Expander] Sub-TOC 생성 실패, 지능형 기본값 사용: {e}")

        if not sub_tocs:
            final_sub = "대정부·산업계 최종 정책 권고사항 및 종합 결론" if is_conclusion else "소결: 본 절의 주요 시사점 및 연계 방향"
            if key_topics:
                sub_tocs = [f"{t} 심층 분석" for t in key_topics[:2]]
                if planned_tables:
                    sub_tocs.append(f"{planned_tables[0]} 및 실증 비교")
                sub_tocs.append(final_sub)
            else:
                sub_tocs = [f"{sec_title} 개요 및 현황", f"{sec_title} 실증 분석 및 쟁점", final_sub]

        # 5. Step 2: Sub-TOC 순차 작성 (컨텍스트 다이어트)
        accumulated_summary = f"- 절 제목: {sec_title}"
        section_parts = []

        for sub_toc in sub_tocs:
            part_prompt = f"""
전체 보고서 주제: {topic}
핵심 방향성: {direction}
현재 장 및 절: {chap_num} > {sec_num} {sec_title}
★ 작성 대상 세부 소주제: {sub_toc}

[기획된 핵심 토픽 및 표]
- 핵심 토픽: {', '.join(key_topics) if key_topics else sec_title}
- 권장 수록 표: {', '.join(planned_tables) if planned_tables else '실증 데이터 비교표'}

[이전까지의 맥락 요약]
{accumulated_summary}

[참고 데이터 풀]
{ref_summary[:3000]}

[작성 강령]
{specific_instruction}

지시사항:
1. 오직 지정된 세부 소주제('{sub_toc}')에 대한 심층 본문만 작성하십시오.
2. 【그림 X-X】 도식화 블록(구조도+AI프롬프트+조판규격) 또는 실증 마크다운 표(Table)를 적극 삽입하십시오.
3. [중요] 본 절이 본문 챕터(1~N-1장)인 경우, 보고서 전체 결론을 단독으로 작성하지 마십시오.
4. 소주제 명칭을 '### 1) {sub_toc}' 형식으로 가장 상단에 적고 본문을 서술하십시오.
"""
            try:
                res_part = await client.generate_text(part_prompt, system_instruction=system_prompt)
                part_text = clean_markdown_text(res_part.text)
            except Exception as e:
                logger.warning(f"[Expander] 세부 파트 '{sub_toc}' AI 작성 실패, 폴백 사용: {e}")
                part_text = f"### 1) {sub_toc}\n\n" + generate_fallback_section(topic, chap_num, str(sub_toc), role_type, tone)

            section_parts.append(part_text)
            accumulated_summary += f"\n- {sub_toc}: 작성 완료됨"

        # 6. 본문 조립 및 마크다운 정규화 / 중간 결론 정제
        raw_combined = "\n\n".join(section_parts)
        sanitized = sanitize_intermediate_conclusions(raw_combined, role_type=role_type)
        final_section_md = normalize_markdown_headings(sanitized, chap_num, sec_num, sec_title)

        # 7. 파일 저장 (Append-only)
        file_path = build_report_artifact_path(topic, "v3", section_title=sec_title)
        saved_path = save_file_append_only(file_path, final_section_md)
        register_artifact(state, artifact_type="section-expanded", title=sec_title, path=saved_path)

        logger.info(f"[Expander] -> [{chap_num} {sec_title}] 완료. ({saved_path})")

        return {
            "section_id": section_data.get("section_id"),
            "chapter_number": chap_num,
            "section_number": sec_num,
            "title": sec_title,
            "content": final_section_md,
            "draft_path": saved_path,
        }


async def run_expander_async(state: ReportState) -> ReportState:
    """Expander 비동기 메인 엔트리: 병렬 동시성 제어 및 상태 머지."""
    topic = state["topic"]
    direction = state.get("direction", "")
    direction_str = " ".join(direction) if isinstance(direction, (list, tuple)) else str(direction)
    tone = state.get("tone", "objective_smooth")
    report_type = state.get("report_type", "market_tech_trend")

    all_sections = state.get("sections", [])
    completed_sections = set(state.get("completed_sections", []))

    # Gatekeeper 루프 대상 필터링 (신규 증설된 섹션 우선 작성 및 기존 완료 섹션 보존)
    loop_targets = state.get("target_sections_for_loop", [])
    if loop_targets:
        target_strs = [str(t).strip() for t in loop_targets]
        target_sections = []
        for s in all_sections:
            sec_title = s.get("title", "")
            sec_id = s.get("section_id", "")
            chap_num = s.get("chapter_number", "")

            if any(ts == sec_title or ts == sec_id or ts == chap_num or ts in sec_title for ts in target_strs):
                # 이미 완료된 섹션이고, 섹션 제목이나 ID로 직접 지정된 경우가 아니라면 중복 실행 방지
                if sec_title in completed_sections and not any(ts == sec_title or ts == sec_id for ts in target_strs):
                    continue
                target_sections.append(s)
        logger.info(f"[Expander] Gatekeeper 회귀 루프 감지: 대상 {len(target_sections)}개 절 선별 작성")
    else:
        target_sections = [s for s in all_sections if s.get("title") not in completed_sections]

    if not target_sections:
        logger.info("[Expander] 모든 섹션이 이미 완료되었습니다. 스킵합니다.")
        return state

    max_concurrency = int(state.get("max_concurrency", 4))
    concurrency_limit = asyncio.Semaphore(max(1, max_concurrency))

    config = _load_config()
    exp_config = config.get("expander", {})
    client = UnifiedModelClient("expander", exp_config)
    system_prompt = _load_prompt()

    logger.info(f"[Expander] 총 {len(target_sections)}개 섹션 병렬 팽창 가동 (동시성: {max_concurrency})")

    tasks = [
        _process_single_section(
            sec,
            topic=topic,
            direction=direction_str,
            tone=tone,
            report_type=report_type,
            client=client,
            system_prompt=system_prompt,
            concurrency_limit=concurrency_limit,
            state=state,
        )
        for sec in target_sections
    ]

    results = await asyncio.gather(*tasks)

    # 상태 업데이트
    existing_expanded = {s.get("title"): s for s in state.get("expanded_sections", []) if s.get("title")}
    for res in results:
        existing_expanded[res["title"]] = res
        completed_sections.add(res["title"])

    state["expanded_sections"] = list(existing_expanded.values())
    state["completed_sections"] = list(completed_sections)

    logger.info(f"[Expander] {len(results)}개 섹션 팽창 완료. 총 완료 섹션 수: {len(completed_sections)}개")
    return state


def run_expander(state: ReportState) -> ReportState:
    """LangGraph 동기 호출을 위한 브릿지."""
    return asyncio.run(run_expander_async(state))

