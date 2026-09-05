"""Gatekeeper Agent: Audits core logic vs empirical volume, and governs the expansion loop."""
from __future__ import annotations

import logging
from src.core.report_types import get_report_type_config
from src.core.state import ReportState

logger = logging.getLogger("report_generator.agents.gatekeeper")

DEFAULT_TOTAL_MIN_LENGTH = 50000
DEFAULT_MAX_LOOPS = 2


def _create_expansion_sections(
    state: ReportState,
    target_chapter_numbers: list[str],
    loop_idx: int,
) -> tuple[list[str], list[str]]:
    """
    기존 작성된 섹션을 덮어쓰거나 축소하지 않고,
    선택된 챕터에 '신규 세부 목차(Section)'를 증설하여 단조 증가(Monotonic Growth) 분량 확장을 보장.
    반환값: (증설된 섹션 제목 목록, 신규 추가된 키워드 목록)
    """
    topic = state.get("topic", "")
    new_section_titles: list[str] = []
    new_keywords: list[str] = []

    for chap_num in target_chapter_numbers:
        chap = next((c for c in state.get("chapters", []) if c.get("chapter_number") == chap_num), None)
        if not chap:
            continue

        existing_secs = chap.get("sections", [])
        next_idx = len(existing_secs) + 1
        new_sec_num = f"{next_idx}."
        chap_id = chap.get("chapter_id", chap_num)
        new_sec_id = f"sec_{chap_id}_{next_idx}_loop{loop_idx}"
        chap_title = chap.get("title", "")
        role_type = chap.get("role_type", "background_trend")

        # 챕터 성격별 차별화된 신규 심층 섹션 제목 부여
        if role_type == "background_trend":
            new_sec_title = f"{chap_title} 관련 글로벌 선도 사례 및 실증 지표 심층 비교 (확장 {loop_idx}차)"
        elif role_type == "empirical_case":
            new_sec_title = f"{chap_title} 분야별 세부 장애요인 및 기업 격차 실태조사 (확장 {loop_idx}차)"
        elif role_type == "core_strategy":
            new_sec_title = f"{chap_title} 세부 거버넌스 및 다자간 협력 모델 구체화 (확장 {loop_idx}차)"
        elif role_type == "action_plans":
            new_sec_title = f"{chap_title} 연계 핵심 과제 및 인프라 구축 방안 (확장 {loop_idx}차)"
        elif role_type == "roadmap":
            new_sec_title = f"{chap_title} 연도별 마일스톤 및 리스크 관리 계획 (확장 {loop_idx}차)"
        elif role_type == "implication":
            new_sec_title = f"{chap_title} 분야별 중장기 파급효과 및 대응 제언 (확장 {loop_idx}차)"
        else:
            new_sec_title = f"{chap_title} 세부 실증 분석 및 심층 벤치마킹 (확장 {loop_idx}차)"

        new_sec = {
            "section_id": new_sec_id,
            "chapter_number": chap["chapter_number"],
            "section_number": new_sec_num,
            "title": new_sec_title,
            "target_pages": max(5, int(chap.get("target_pages", 20) // 2)),
            "target_chars": max(5000, int(chap.get("target_chars", 25000) // 2)),
            "key_topics": [
                f"{new_sec_title} 기초 현황 및 팩트 분석",
                f"{chap_title} 관련 글로벌 비교 실증 및 시사점",
            ],
            "planned_tables": [f"{new_sec_title} 상세 비교 통계표"],
            "planned_case_studies": [f"{new_sec_title} 선도 실증 사례"],
            "role_type": role_type,
            "status": "pending",
        }

        # 1. 챕터 객체에 신규 섹션 증설
        chap.setdefault("sections", []).append(new_sec)

        # 2. 전체 섹션 목록에도 신규 섹션 증설
        sec_flat = dict(new_sec)
        state.setdefault("sections", []).append(sec_flat)

        # 3. 신규 조사 키워드 도출
        kw = f"{topic} {chap_title} 실증 사례 및 통계 (확장 {loop_idx})"
        new_keywords.append(kw)
        new_section_titles.append(new_sec_title)

    return new_section_titles, new_keywords


def run_gatekeeper(state: ReportState) -> ReportState:
    """Step 9: 코어 70% 방어선 및 실증 분량 심사, 무한 루프 통제 (Hard Limit)."""
    logger.info("[Gatekeeper] === 분량 및 코어 논리 연계 심사 시작 ===")

    sections = state.get("expanded_sections", [])
    if not sections:
        raise ValueError("[Gatekeeper] expanded_sections가 비어 있어 심사를 진행할 수 없습니다.")

    # 1. Reviewer가 누락 챕터 등으로 루프를 지정한 경우 최우선 존중
    target_for_loop = state.get("target_sections_for_loop", [])
    if target_for_loop:
        logger.warning(f"[Gatekeeper] -> [긴급] Reviewer 재작업 지시 감지: {target_for_loop}")
        state["next_step"] = "researcher"
        return state

    report_type = state.get("report_type", "market_tech_trend")
    direction = state.get("direction", "")
    type_config = get_report_type_config(report_type, direction=direction)

    # 2. 챕터별 실질 글자 수 집계 (본문 vs 부록 동적 분류)
    core_chapter_numbers = {c.chapter_number for c in type_config.chapters if c.is_core}
    empirical_chapter_numbers = {
        c.chapter_number for c in type_config.chapters
        if not c.is_core and not c.role_type.startswith("appendix")
    }

    core_chars = 0
    empirical_chars = 0
    total_chars = 0

    for sec in sections:
        c_text = sec.get("content", "")
        sec_len = len(c_text)
        total_chars += sec_len

        chap_num = sec.get("chapter_number", "")
        if chap_num in core_chapter_numbers:
            core_chars += sec_len
        elif chap_num in empirical_chapter_numbers:
            empirical_chars += sec_len

    target_total = state.get("target_total_min_length", DEFAULT_TOTAL_MIN_LENGTH)
    core_ratio = sum(c.target_ratio for c in type_config.chapters if c.is_core) or 0.3
    core_target_chars = target_total * core_ratio
    core_70_threshold = core_target_chars * 0.7

    logger.info(
        f"[Gatekeeper] 전체 분량: {total_chars:,}자 (목표: {target_total:,}자) | "
        f"코어 분량: {core_chars:,}자 (70% 기준: {core_70_threshold:,.0f}자)"
    )

    # 3. 코어 0자 결함 방어
    if core_chars == 0 and core_chapter_numbers:
        logger.warning("[Gatekeeper] -> [오류] 코어 전략 장이 0자입니다. 코어 챕터 작성을 강제합니다.")
        state["target_sections_for_loop"] = list(core_chapter_numbers)
        state["next_step"] = "researcher"
        return state

    loop_chapter_targets: list[str] = []

    # 4. 코어 논리 방어 평가 (코어 장 억지 팽창 차단 -> 실증/배경 챕터 증설)
    if core_chars < core_70_threshold:
        logger.info(
            f"[Gatekeeper] -> [판단] 코어 논리 분량 미달 ({core_chars:,}자 < {core_70_threshold:,.0f}자). "
            "환각 방지를 위해 코어 장을 억지 확장하지 않고, 배경 및 실증 사례 챕터를 확장합니다."
        )
        loop_chapter_targets.extend(list(empirical_chapter_numbers)[:2])
    else:
        logger.info("[Gatekeeper] -> [통과] 코어 논리 분량 안정권 확보 (환각 방지 충족).")

    # 5. 전체 분량 미달 시 실증/배경 챕터로 팽창 유도
    if total_chars < target_total:
        logger.info(f"[Gatekeeper] -> [판단] 전체 분량 미달 ({total_chars:,}자 < {target_total:,}자). 실증 데이터 보강 필요.")
        loop_chapter_targets.extend(list(empirical_chapter_numbers))

    # 중복 제거된 대상 챕터
    unique_target_chapters = list(dict.fromkeys(loop_chapter_targets))

    # 6. 루프 제어 (Hard limit: 기본 2회)
    max_loops = state.get("max_loops", DEFAULT_MAX_LOOPS)
    current_loops = state.get("loop_count", 0)

    if unique_target_chapters and current_loops < max_loops:
        next_loop = current_loops + 1
        state["loop_count"] = next_loop

        # ★ 사용자 피드백 반영: 기존 섹션 덮어쓰기 금지 -> 신규 목차(Section) 증설로 단조 증가 보장
        new_titles, new_kws = _create_expansion_sections(
            state=state,
            target_chapter_numbers=unique_target_chapters,
            loop_idx=next_loop,
        )

        # 신규 키워드 추가 및 루프 타겟 지정
        state.setdefault("keywords", []).extend(new_kws)
        state["target_sections_for_loop"] = new_titles
        state["next_step"] = "researcher"

        logger.info(
            f"[Gatekeeper] -> [신규 목차 증설 루프 진입] 기존 본문 보존 및 신규 섹션 {len(new_titles)}개 증설: {new_titles} "
            f"(진행 루프: {next_loop}/{max_loops})"
        )
        return state

    logger.info("[Gatekeeper] -> [최종 승인] 모든 조건 충족 (또는 최대 루프 소진). Merger 단계로 이관.")
    state["target_sections_for_loop"] = []
    state["next_step"] = "merger"
    return state

