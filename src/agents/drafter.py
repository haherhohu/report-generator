"""Drafter Agent: Creates report master outline (v1/v2) and extracts research keywords."""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
import yaml

from src.core.report_types import (
    normalize_report_type,
    get_report_type_config,
    build_initial_chapters,
)
from src.core.state import ReportState, ChapterItem, SectionItem
from src.models.client import UnifiedModelClient
from src.models.fallback_engine import generate_fallback_outline
from src.utils.file_manager import (
    save_file_append_only,
    build_report_artifact_path,
    register_artifact,
)

logger = logging.getLogger("report_generator.agents.drafter")


def _load_config() -> dict:
    for path in ("config/agents_config.yaml", "poc/config/agents_config.yaml"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_prompt() -> str:
    for path in ("prompts/drafter_prompt.md", "poc/prompts/drafter_prompt.md"):
        if os.path.exists(path):
            return Path(path).read_text(encoding="utf-8")
    return (
        "당신은 대한민국 국가 연구기관 및 공공기관의 수석 기획총괄위원입니다. "
        "주제와 요구 방향성을 철저히 분석하여 보고서 유형에 최적화된 마스터 아웃라인을 설계하십시오."
    )


def run_drafter(state: ReportState) -> ReportState:
    """Step 1 & Step 2: 아웃라인 기획, v1/v2 초안 작성, 심층 키워드 도출."""
    topic = state["topic"]
    direction = state.get("direction", "")
    direction_str = " ".join(direction) if isinstance(direction, (list, tuple)) else str(direction)
    target_perspective = state.get("target_perspective", "일반 연구기관 관점")

    report_type = normalize_report_type(state.get("report_type"), direction=direction)
    state["report_type"] = report_type
    type_config = get_report_type_config(report_type, direction=direction)
    state["tone"] = state.get("tone") or type_config.default_tone

    target_pages = int(state.get("target_pages", 200))
    target_chars = int(state.get("target_chars", target_pages * 1250))

    logger.info(f"[Drafter] '{topic}' 기획 착수 (유형: {report_type}, 어조: {state['tone']})")

    config = _load_config()
    drafter_config = config.get("drafter", {})
    client = UnifiedModelClient("drafter", drafter_config)
    system_prompt = _load_prompt()

    # 1. 뼈대 아웃라인 객체 사전 구축
    initial_chapters = build_initial_chapters(report_type, target_pages=target_pages, target_chars=target_chars)

    # 2. Step 1: 최초 기획 초안(v1) 작성
    v1_prompt = f"""
[보고서 기획 의뢰]
- 보고서 명칭: {topic}
- 보고서 유형: {type_config.label} ({report_type})
- 핵심 방향성: {direction_str}
- 타겟 관점: {target_perspective}
- 목표 분량: 약 {target_pages}페이지 ({target_chars:,}자)
- 어조: {state['tone']}

[지침]
위 표준 목차 체계({len(type_config.chapters)}개 장)에 따라 각 장의 번호('## Ⅰ. ...' 또는 '## 1장 ...')와 세부 추진 배경, 핵심 조사 방향성을 마크다운으로 작성하십시오.
"""
    v1_content = ""
    try:
        res_v1 = client.generate_text_sync(v1_prompt, system_instruction=system_prompt)
        v1_content = res_v1.text
    except Exception as e:
        logger.warning(f"[Drafter] v1 AI 생성 실패, 결정론적 폴백 적용: {e}")
        v1_chapters = generate_fallback_outline(report_type, topic, target_pages)
        lines = [f"# {topic} (초안 v1)\n", f"- 방향성: {direction_str}\n"]
        for ch in v1_chapters:
            lines.append(f"## {ch['chapter_number']} {ch['title']}")
            lines.append(f"- 역할: {ch['role_type']} (목표: {ch['target_pages']}p)\n")
        v1_content = "\n".join(lines)

    v1_path = build_report_artifact_path(topic, "v1")
    v1_saved = save_file_append_only(v1_path, v1_content)
    register_artifact(state, artifact_type="draft", title="초안 v1", path=v1_saved)
    logger.info(f"[Drafter] Step 1 기초 초안(v1) 저장: {v1_saved}")

    target_content = v1_content
    v2_saved = None

    # 3. Step 2: 사용자 기초 자료 반영 업데이트(v2)
    source_materials = state.get("source_materials", [])
    if source_materials and not state.get("is_blank_slate"):
        source_texts = []
        for sm in source_materials:
            c = sm.get("content", "") if isinstance(sm, dict) else str(sm)
            source_texts.append(c)
        source_bundle = "\n\n".join(source_texts)[:10000]

        v2_prompt = f"""
[기초 초안 v1]
{v1_content[:4000]}

[사용자 제공 기초 자료]
{source_bundle}

[지침]
기초 초안(v1)의 목차 구조를 그대로 유지한 상태에서, 사용자 제공 자료의 구체적 팩트, 법령, 기술 사양을 각 장에 적절히 주입하여 살을 찌운 업데이트 초안(v2)을 마크다운으로 작성하십시오.
"""
        try:
            res_v2 = client.generate_text_sync(v2_prompt, system_instruction=system_prompt)
            target_content = res_v2.text
        except Exception as e:
            logger.warning(f"[Drafter] v2 AI 보강 실패, v1 유지: {e}")
            target_content = v1_content + f"\n\n## 사용자 제공 자료 요약\n{source_bundle[:2000]}"

        v2_path = build_report_artifact_path(topic, "v2")
        v2_saved = save_file_append_only(v2_path, target_content)
        register_artifact(state, artifact_type="draft", title="초안 v2", path=v2_saved)
        logger.info(f"[Drafter] Step 2 업데이트 초안(v2) 저장: {v2_saved}")

    state["foundation_report_path"] = v2_saved or v1_saved

    # 4. Step 3: 심층 조사 키워드 매트릭스 도출 (5~8건)
    keyword_prompt = f"""
당신은 수석 리서치 기획자입니다.
다음 보고서 주제, 방향성, 타겟 관점을 바탕으로 본문 팽창 및 실증 근거 수집을 위해 추가 조사가 필요한 구체적이고 전문적인 조사 키워드 5~8개를 도출하십시오.

- 보고서 주제: {topic}
- 핵심 방향성: {direction_str}
- 타겟 관점: {target_perspective}

[제약사항]
1. 단순 명사가 아닌, 타겟 관점에 맞춘 구체적인 질문/조사 항목 형태로 작성하십시오 (예: 'Vantis의 민간 항로 관제 C2 네트워크 안전성 검증 사례').
2. 반드시 순수 JSON 문자열 배열 형태(예: ["키워드1", "키워드2", ...])로만 출력하십시오. 코드 블록(```)이나 부가 설명은 일체 배제하십시오.
"""
    keywords: list[str] = []
    try:
        res_kw = client.generate_text_sync(keyword_prompt, response_mime_type="application/json")
        cleaned_kw = res_kw.text.strip()
        match = re.search(r"\[.*\]", cleaned_kw, re.DOTALL)
        if match:
            keywords = json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"[Drafter] 키워드 AI 추출 실패, 기본 폴백 적용: {e}")

    if not keywords:
        keywords = [
            f"{topic} 글로벌 최신 시장 동향 및 통계",
            f"{topic} 주요국 정책 및 제도적 지원 체계",
            f"{topic} 핵심 원천기술 TRL 성숙도 및 특허 분석",
            f"{topic} 국내 산업 생태계 현황 및 경쟁력 격차",
            f"{topic} 실증 체계 구축 및 핵심 리스크 관리 방안",
        ]

    state["keywords"] = keywords
    logger.info(f"[Drafter] Step 3 조사 키워드 {len(keywords)}건 도출: {keywords}")

    # 5. 상태 객체에 아웃라인 챕터 및 섹션 리스트 바인딩
    state["chapters"] = initial_chapters
    # Expander 호환용 플랫 섹션 목록
    flattened_sections = []
    for chap in initial_chapters:
        for sec in chap["sections"]:
            sec_dict = dict(sec)
            sec_dict["role_type"] = chap["role_type"]
            flattened_sections.append(sec_dict)
    state["sections"] = flattened_sections

    return state

