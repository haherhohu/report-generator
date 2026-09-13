"""Report type definitions, template loading, and chapter specifications."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
import yaml

from src.core.state import ChapterItem, SectionItem

DEFAULT_REPORT_TYPE = "market_tech_trend"

@dataclass(frozen=True)
class ChapterTemplate:
    index: int
    chapter_number: str
    title: str
    role_type: str  # "intro", "background_trend", "empirical_case", "core_strategy", "action_plans", "roadmap", "implication", "final_conclusion", "appendix_facts", "appendix_references"
    target_ratio: float
    is_core: bool
    allowed_conclusions: bool

@dataclass(frozen=True)
class ReportTypeConfig:
    type_id: str
    label: str
    default_tone: Literal["official_formal", "objective_smooth"]
    chapters: list[ChapterTemplate]


BUILTIN_TEMPLATES: dict[str, dict] = {
    "research_policy": {
        "type_id": "research_policy",
        "label": "정부제출용 연구기관 보고서",
        "default_tone": "official_formal",
        "chapters": [
            {"index": 1, "chapter_number": "Ⅰ", "title": "서론 및 추진 필요성", "role_type": "intro", "target_ratio": 0.05, "is_core": False, "allowed_conclusions": False},
            {"index": 2, "chapter_number": "Ⅱ", "title": "국내외 환경변화 및 기술·산업 동향 분석", "role_type": "background_trend", "target_ratio": 0.15, "is_core": False, "allowed_conclusions": False},
            {"index": 3, "chapter_number": "Ⅲ", "title": "국내 실증 현황 진단 및 한계·문제점 도출", "role_type": "empirical_case", "target_ratio": 0.20, "is_core": False, "allowed_conclusions": False},
            {"index": 4, "chapter_number": "Ⅳ", "title": "비전, 추진목표 및 전략적 추진체계(거버넌스)", "role_type": "core_strategy", "target_ratio": 0.15, "is_core": True, "allowed_conclusions": False},
            {"index": 5, "chapter_number": "Ⅴ", "title": "중점 추진전략별 세부수행과제(Action Plans) 기획", "role_type": "action_plans", "target_ratio": 0.20, "is_core": True, "allowed_conclusions": False},
            {"index": 6, "chapter_number": "Ⅵ", "title": "단계별·연도별 추진 로드맵 및 재정 투자 계획", "role_type": "roadmap", "target_ratio": 0.05, "is_core": True, "allowed_conclusions": False},
            {"index": 7, "chapter_number": "Ⅶ", "title": "종합 결론 및 정책적 제언 (기대효과 포함)", "role_type": "final_conclusion", "target_ratio": 0.10, "is_core": False, "allowed_conclusions": True},
            {"index": 8, "chapter_number": "Ⅷ", "title": "부록 (통계 및 관계 법령 발췌)", "role_type": "appendix_facts", "target_ratio": 0.08, "is_core": False, "allowed_conclusions": False},
            {"index": 9, "chapter_number": "Ⅸ", "title": "참고문헌 및 주요 약어표", "role_type": "appendix_references", "target_ratio": 0.02, "is_core": False, "allowed_conclusions": False},
        ],
    },
    "market_tech_trend": {
        "type_id": "market_tech_trend",
        "label": "민간기관용 연구/동향조사 원고",
        "default_tone": "objective_smooth",
        "chapters": [
            {"index": 1, "chapter_number": "Ⅰ", "title": "조사 배경 및 산업·기술 정의", "role_type": "intro", "target_ratio": 0.08, "is_core": False, "allowed_conclusions": False},
            {"index": 2, "chapter_number": "Ⅱ", "title": "글로벌 시장 규모 및 산업 생태계 동향", "role_type": "background_trend", "target_ratio": 0.16, "is_core": False, "allowed_conclusions": False},
            {"index": 3, "chapter_number": "Ⅲ", "title": "최신 기술 동향 및 표준화·특허 분석", "role_type": "background_trend", "target_ratio": 0.16, "is_core": False, "allowed_conclusions": False},
            {"index": 4, "chapter_number": "Ⅳ", "title": "주요국 정책 동향 및 글로벌 투자 벤치마킹", "role_type": "empirical_case", "target_ratio": 0.14, "is_core": False, "allowed_conclusions": False},
            {"index": 5, "chapter_number": "Ⅴ", "title": "국내 현황 및 경쟁력 격차 실증 진단", "role_type": "empirical_case", "target_ratio": 0.14, "is_core": False, "allowed_conclusions": False},
            {"index": 6, "chapter_number": "Ⅵ", "title": "핵심 종합 시사점 및 미래 전망", "role_type": "implication", "target_ratio": 0.14, "is_core": True, "allowed_conclusions": False},
            {"index": 7, "chapter_number": "Ⅶ", "title": "대응 전략 및 실행 권고사항", "role_type": "final_conclusion", "target_ratio": 0.12, "is_core": True, "allowed_conclusions": True},
            {"index": 8, "chapter_number": "Ⅷ", "title": "부록 (참고문헌 및 주요 약어표)", "role_type": "appendix_references", "target_ratio": 0.06, "is_core": False, "allowed_conclusions": False},
        ],
    },
    "global_market_expansion": {
        "type_id": "global_market_expansion",
        "label": "해외시장진출 전략보고서",
        "default_tone": "objective_smooth",
        "chapters": [
            {"index": 1, "chapter_number": "Ⅰ", "title": "개요 및 해외 진출 추진 배경", "role_type": "intro", "target_ratio": 0.08, "is_core": False, "allowed_conclusions": False},
            {"index": 2, "chapter_number": "Ⅱ", "title": "글로벌 타겟 시장 환경 및 산업 트렌드 분석", "role_type": "background_trend", "target_ratio": 0.16, "is_core": False, "allowed_conclusions": False},
            {"index": 3, "chapter_number": "Ⅲ", "title": "국내 기업 해외 진출 현황 및 구조적 애로사항", "role_type": "empirical_case", "target_ratio": 0.14, "is_core": False, "allowed_conclusions": False},
            {"index": 4, "chapter_number": "Ⅳ", "title": "주요국 시장 진출 지원 프로그램 및 제도 조사", "role_type": "empirical_case", "target_ratio": 0.16, "is_core": False, "allowed_conclusions": False},
            {"index": 5, "chapter_number": "Ⅴ", "title": "해외 시장 진출 전략 및 맞춤형 트랙 설계", "role_type": "core_strategy", "target_ratio": 0.18, "is_core": True, "allowed_conclusions": False},
            {"index": 6, "chapter_number": "Ⅵ", "title": "진출 실행 가이드라인 및 통상·인증 리스크 관리 방안", "role_type": "core_strategy", "target_ratio": 0.14, "is_core": True, "allowed_conclusions": False},
            {"index": 7, "chapter_number": "Ⅶ", "title": "기대효과 및 종합 결론", "role_type": "final_conclusion", "target_ratio": 0.08, "is_core": False, "allowed_conclusions": True},
            {"index": 8, "chapter_number": "Ⅷ", "title": "부록 (현지 법령·인증 규정, 참고문헌 및 주요 약어표)", "role_type": "appendix_references", "target_ratio": 0.06, "is_core": False, "allowed_conclusions": False},
        ],
    },
}


def normalize_report_type(report_type: str | None, direction: str | list[str] | None = None) -> str:
    """사용자 입력 또는 방향성 텍스트를 분석하여 표준화된 보고서 유형 키 반환."""
    text = (report_type or "").strip().lower().replace("-", "_")
    direction_str = " ".join(direction) if isinstance(direction, (list, tuple)) else str(direction or "")
    dir_lower = direction_str.lower()

    if text in BUILTIN_TEMPLATES:
        return text

    if any(k in text for k in ("trend", "동향", "market", "technology_trend")):
        return "market_tech_trend"
    if any(k in text for k in ("global", "해외", "expansion", "진출")):
        return "global_market_expansion"
    if any(k in text for k in ("policy", "research", "정책", "연구", "국책")):
        return "research_policy"

    # direction 텍스트에서 감지
    if "해외" in direction_str or "진출" in direction_str or "global" in dir_lower:
        return "global_market_expansion"
    if "동향" in direction_str or "trend" in dir_lower or "시장" in direction_str:
        return "market_tech_trend"
    if "정책" in direction_str or "과제" in direction_str or "연구기관" in direction_str:
        return "research_policy"

    return DEFAULT_REPORT_TYPE


def load_template_yaml(type_id: str, templates_dir: str = "config/templates") -> dict | None:
    path = os.path.join(templates_dir, f"{type_id}.yaml")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "chapters" in data:
                    return data
        except Exception:
            pass
    return None


def get_report_type_config(report_type: str | None, direction: str | list[str] | None = None) -> ReportTypeConfig:
    norm_type = normalize_report_type(report_type, direction=direction)
    data = load_template_yaml(norm_type) or BUILTIN_TEMPLATES.get(norm_type, BUILTIN_TEMPLATES[DEFAULT_REPORT_TYPE])

    chapter_objs = [
        ChapterTemplate(
            index=c["index"],
            chapter_number=c.get("chapter_number", f"{c['index']}장"),
            title=c["title"],
            role_type=c.get("role_type", "background_trend"),
            target_ratio=float(c.get("target_ratio", 0.1)),
            is_core=bool(c.get("is_core", False)),
            allowed_conclusions=bool(c.get("allowed_conclusions", False)),
        )
        for c in data.get("chapters", [])
    ]

    return ReportTypeConfig(
        type_id=norm_type,
        label=data.get("label", norm_type),
        default_tone=data.get("default_tone", "official_formal"),
        chapters=chapter_objs,
    )


def get_required_chapter_titles(report_type: str | None = None, direction: str | list[str] | None = None) -> dict[int, str]:
    config = get_report_type_config(report_type, direction=direction)
    return {c.index: f"{c.chapter_number} {c.title}" for c in config.chapters}


def get_chapter_role(report_type: str, chapter_index: int | str) -> str:
    config = get_report_type_config(report_type)
    try:
        idx = int(chapter_index)
        for c in config.chapters:
            if c.index == idx:
                return c.role_type
    except (ValueError, TypeError):
        c_str = str(chapter_index).strip()
        for c in config.chapters:
            if c.chapter_number in c_str or str(c.index) in c_str or c.title in c_str:
                return c.role_type
    return "background_trend"


def build_initial_chapters(report_type: str, target_pages: int = 200, target_chars: int = 250000) -> list[ChapterItem]:
    config = get_report_type_config(report_type)
    chapters: list[ChapterItem] = []

    for c in config.chapters:
        chap_pages = max(1, round(target_pages * c.target_ratio))
        chap_chars = max(2000, round(target_chars * c.target_ratio))

        # 기본 2개 절 구성 (Drafter가 추가 세분화 가능)
        sec_pages = max(1, chap_pages // 2)
        sec_chars = max(1000, chap_chars // 2)

        sec1: SectionItem = {
            "section_id": f"sec_{c.index}_1",
            "chapter_number": c.chapter_number,
            "section_number": "1.",
            "title": f"{c.title} 개요 및 기초 분석",
            "target_pages": sec_pages,
            "target_chars": sec_chars,
            "key_topics": [f"{c.title} 관련 핵심 이슈", "주요 현황 및 팩트 분석"],
            "planned_tables": [f"{c.title} 핵심 지표 요약표"],
            "planned_case_studies": [f"{c.title} 선도 사례 분석"],
            "status": "pending",
        }
        sec2: SectionItem = {
            "section_id": f"sec_{c.index}_2",
            "chapter_number": c.chapter_number,
            "section_number": "2.",
            "title": f"{c.title} 세부 실증 분석 및 시사점",
            "target_pages": chap_pages - sec_pages,
            "target_chars": chap_chars - sec_chars,
            "key_topics": ["세부 데이터 실증 분석", "향후 파급효과"],
            "planned_tables": [f"{c.title} 세부 비교 분석표"],
            "planned_case_studies": [],
            "status": "pending",
        }

        chap_item: ChapterItem = {
            "chapter_id": f"chap_{c.index}",
            "chapter_number": c.chapter_number,
            "title": c.title,
            "target_pages": chap_pages,
            "target_chars": chap_chars,
            "role_type": c.role_type,
            "is_core_chapter": c.is_core,
            "allowed_conclusions": c.allowed_conclusions,
            "sections": [sec1, sec2],
        }
        chapters.append(chap_item)

    return chapters

