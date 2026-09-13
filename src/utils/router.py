"""Dynamic context and instruction router based on chapter role type and report style."""
from __future__ import annotations

from typing import Any

def route_section_instruction(
    chapter_role: str,
    section_title: str,
    report_type: str,
    tone: str,
    direction: str,
    source_summary: str = "",
) -> dict[str, Any]:
    """챕터 성격(role_type)에 맞춘 전문 작성 지침과 컨텍스트 배정."""
    is_formal = (tone == "official_formal")
    verb_rule = "모든 문장의 끝맺음은 '~함', '~임' 형태의 국책연구원 표준 어미를 사용하십시오." if is_formal else "문장의 끝맺음은 독자가 읽기 편한 '~한다', '~이다', '~된다' 형태의 서술어 어미를 중심으로 작성하십시오."

    base_rule = (
        f"1. 어미 규칙: {verb_rule}\n"
        "2. 시각화 의무화: 본문 내에 반드시 【그림 X-X】 도식화 블록(구조도 + AI 이미지 프롬프트 + 조판규격)을 최소 1개 이상 인용구(>)로 수록하십시오.\n"
        "3. 데이터 표 의무화: 세부 수치, 연도, 비교 기준이 포함된 마크다운 표(Table)를 1개 이상 작성하십시오.\n"
        "4. [중요] 단일 보고서 일체감: 본 절 내부에 전체 종합 결론을 반복 작성하지 마십시오. 오직 본 절 분석 내용에 기반한 '[소결: 본 절의 주요 시사점]'으로 정리하고 후속 연구와의 연결고리만 서술하십시오.\n"
        "5. [중요] 개별 참고문헌/약어표 생성 금지: 본문 내에는 [1], [2] 인용 부호만 기재하고, 독립된 참고문헌 리스트나 약어 정의 목록은 절대 작성하지 마십시오."
    )

    if chapter_role == "intro":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [서론/배경 작성 지침]: 왜 지금 이 연구와 국가적·산업적 대응이 시급한지 거시적 환경 변화와 당위성을 강력하게 설득조로 서술하십시오."
        )
    elif chapter_role == "background_trend":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [시장/기술 동향 지침]: 수집된 통계와 글로벌 시장 지표(CAGR, 시장 규모), 선도 기업 포트폴리오를 구체적으로 인용하여 사실 위주로 분량을 풍부하게 팽창시키십시오."
        )
    elif chapter_role == "empirical_case":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [실증 사례 및 격차 진단 지침]: 주요 선도국의 정책·사업 사례를 벤치마킹하고, 국내 주력 기술 수준과의 격차(년수, %) 및 구조적 병목 요인을 날카롭게 진단하십시오."
        )
    elif chapter_role == "core_strategy":
        specific_instruction = (
            f"{base_rule}\n"
            f"6. [핵심 전략 수립 지침]: 사용자가 제시한 핵심 방향성('{direction}')을 적극 반영하여, 실행 가능한 전략 체계와 산학연관 추진 거버넌스를 설계하십시오."
        )
    elif chapter_role == "action_plans":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [세부수행과제 지침]: 실제 정부 R&D 제안서 수준으로 과제명, 추진 기간, 소요 예산 구조, 단계별 목표치를 기획형 사업계획서 형식으로 정밀하게 제시하십시오."
        )
    elif chapter_role == "implication":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [핵심 시사점 도출 지침]: 억지 과제사업이나 예산표를 만들지 마십시오! 1) 정책·제도적 시사점, 2) 산업·시장적 시사점, 3) R&D·기술적 시사점, 4) 글로벌 공급망 시사점으로 범주를 나누어 심층 시사점을 도출하십시오."
        )
    elif chapter_role == "final_conclusion":
        specific_instruction = (
            f"{base_rule}\n"
            "6. [종합 결론 및 정책 제언 지침]: [본 보고서의 대미를 장식하는 핵심 종합 장] 앞서 분석된 모든 장의 핵심을 총괄 요약하고, 정부 및 정책 입안자가 즉각 채택할 수 있는 실효성 있는 종합 정책 권고사항을 단기/중장기로 나누어 제언하십시오."
        )
    elif chapter_role in ("appendix_facts", "appendix_references"):
        specific_instruction = (
            "1. 순수 팩트 나열 지침: 주관적인 시사점, 전망, 정책 제언을 일체 작성하지 마십시오.\n"
            "2. 오직 객관적 사실, 통계 데이터시트, 법령 조항 목록만 100% 사실적으로 정리하십시오.\n"
            "3. 마크다운 표(Table)와 불릿 리스트 형태로만 출력하십시오."
        )
    else:
        specific_instruction = f"{base_rule}\n6. 표준 국책연구 보고서 양식에 따라 밀도 높은 실증 분석을 수행하십시오."

    return {
        "specific_instruction": specific_instruction,
        "context_summary": source_summary[:4000] if source_summary else "",
    }

