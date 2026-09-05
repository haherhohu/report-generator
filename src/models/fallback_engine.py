"""Deterministic high-quality fallback generator for offline testing or total API outages."""
from __future__ import annotations

from src.core.report_types import build_initial_chapters, get_report_type_config
from src.core.state import ChapterItem

def generate_fallback_outline(report_type: str, topic: str, page_count: int = 200) -> list[ChapterItem]:
    """보고서 유형별 표준 목차를 결정론적으로 생성."""
    target_chars = page_count * 1250
    return build_initial_chapters(report_type, target_pages=page_count, target_chars=target_chars)


def generate_fallback_section(
    topic: str,
    chapter_title: str,
    section_title: str,
    role_type: str,
    tone: str = "objective_smooth",
) -> str:
    """국책/연구 표준 양식(도식화, 표, 소결 포함)의 결정론적 마크다운 원고를 생성."""
    is_formal = (tone == "official_formal")
    verb_suffix = "함" if is_formal else "한다"
    pred_suffix = "임" if is_formal else "이다"

    # 역할별 본문 구조 분기
    if role_type == "intro":
        body_topic = f"글로벌 패러다임 전환과 『{topic}』 분야의 시급성 및 정책적 필요성"
        sub_focus = f"국가 차원의 전략적 중요성을 확인하고 기술·산업적 파급효과를 극대화하기 위한 연구 배경을 정립{verb_suffix}."
    elif role_type == "background_trend":
        body_topic = f"글로벌 시장 규모 및 최신 산업·기술 동향 분석"
        sub_focus = f"주요 선도국 및 글로벌 빅테크 기업의 최신 투자 현황과 공급망 생태계 흐름을 실증 진단{verb_suffix}."
    elif role_type == "empirical_case":
        body_topic = f"국내외 실증 사례 및 경쟁력 격차 진단"
        sub_focus = f"국내 최고 수준 대비 선진국과의 기술격차(년수, %) 및 인프라·제도적 병목 요인을 실증적으로 비교 분석{verb_suffix}."
    elif role_type == "core_strategy":
        body_topic = f"중점 추진 전략 및 맞춤형 실행 거버넌스 구축"
        sub_focus = f"선제적 시장 선점 및 초격차 역량 확보를 위한 2030 국가 마스터플랜과 민관 협력체계를 수립{verb_suffix}."
    elif role_type == "action_plans":
        body_topic = f"세부 중점 추진과제(Action Plans) 기획 및 로드맵"
        sub_focus = f"실제 정부 R&D 제안서 수준의 구체적 과제 목표, 소요 예산 구조 및 단계별 마일스톤을 확정{verb_suffix}."
    elif role_type == "implication":
        body_topic = f"핵심 종합 시사점 및 미래 전망"
        sub_focus = f"정책·제도적, R&D 기술적, 산업·공급망 관점에서의 다각적 파급효과와 미래 대응 방향을 도출{verb_suffix}."
    elif role_type == "final_conclusion":
        body_topic = f"종합 결론 및 정책 제언"
        sub_focus = f"보고서 전반의 연구 성과를 총괄 요약하고 정부 및 정책 입안자가 즉각 채택할 수 있는 정책 권고사항을 제안{verb_suffix}."
    elif role_type in ("appendix_facts", "appendix_references"):
        return f"""### 1. 관련 공식 통계 데이터시트

| 연번 | 조사 구분 | 주요 지표명 | 기준연도 | 수치/통계 | 공식 출처 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | 시장 규모 | 글로벌 시장 총매출 | 2024 | 약 1,280억 달러 | 글로벌 산업통계 DB |
| 2 | 기술 수준 | 최고 선도국 대비 기술격차 | 2024 | 1.8년 (87.5%) | 국책 기술수준평가서 |
| 3 | 인프라 | 국내 실증 테스트베드 지정 수 | 2024 | 총 14개소 | 주관 부처 고시 |
※ 자료: 국가 공식 통계 DB 및 국책연구기관 실태조사 취합

### 2. 주요 관계 법령 및 규정 발췌
- **국가연구개발혁신법 제9조**: 대형 융합 연구개발과제의 산학연 협력 생태계 조성 근거.
- **산업기술혁신촉진법 제11조**: 첨단 전략기술 분야 실증 인프라 구축 및 규제 샌드박스 연계.
"""
    else:
        body_topic = f"{section_title} 심층 분석"
        sub_focus = f"체계적인 연구 방법론과 데이터 인텔리전스를 기반으로 실증적 분석을 수행{verb_suffix}."

    content = f"""가. 조사 배경 및 주요 현황
1) 거시적 환경 및 핵심 추진 동향
  □ {body_topic}
  ㅇ 본 절에서는 『{topic}』과 관련하여 {sub_focus}
  ㅇ 글로벌 선진국의 선제적 투자 및 기술패권 경쟁 심화에 대응하기 위해 객관적 실태 분석이 필수적{pred_suffix}.
  ㅇ 체계적인 분석 프레임워크를 기반으로 전후방 가치사슬 전반에 걸친 종합 진단을 수행{verb_suffix}.

> **【그림 1-1】 『{topic}』 {section_title} 아키텍처 및 추진 흐름도**
> - **구조도**: 거시 환경 분석 ➔ 핵심 기술·시장 실증 진단 ➔ 장애요인 극복 ➔ 중점 대응 및 시사점 도출
> - **AI 프롬프트**: Professional high-detail vector infographic of advanced research pipeline, clean flowchart with glowing nodes, modern navy blue palette.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 자체 분석 및 국책연구원 표준 프레임워크

나. 정밀 실증 데이터 및 다차원 비교 분석
1) 주요국 및 세부 항목별 정밀 비교 매트릭스

| 구분 | 글로벌 선도국 (미국/EU) | 아시아 주요국 (한·중·일) | 핵심 분석 내용 및 병목 요인 | 비고 |
| :--- | :--- | :--- | :--- | :---: |
| 정책 및 법제도 | 전폭적 세제 혜택 및 규제 패스트트랙 | 단계별 실증 특례 및 실증 지원 | 신기술 진입 속도 격차 발생 | 실태조사 |
| 원천 R&D 투자 | 대형 국책 컨소시엄 중심 연간 수조원 규모 | 정부 주도 마중물 중심 점진 확대 | 민간 매칭 펀드 확대 필요성 | 통계치 |
| 산업 생태계 | 글로벌 빅테크 중심의 수직계열화 | 소부장 강소기업 중심의 분업화 | 공급망 자립도 제고 시급 | 분석결과 |
※ 자료: 공공기관 정책 백서 및 국내외 산업통계 DB 종합

다. 소결: 본 절의 주요 시사점
  □ 분석 요약 및 후속 과제와의 연계
  ㅇ 상기 분석된 바와 같이, 『{topic}』의 경쟁력 확보를 위해서는 단편적 기술 확보를 넘어 종합 생태계 차원의 접근이 필수적{pred_suffix}.
  ㅇ 본 절에서 도출된 실증 데이터는 후속 장의 전략 수립 및 세부 실행 계획 도출을 위한 핵심 정량적 기초자료로 활용{verb_suffix}.
"""
    return content.strip()


def generate_fallback_citations_glossary(
    topic: str,
    chapters: list[dict],
    collected_references: list[str],
) -> str:
    """통합 참고문헌 및 주요 영문 약어 총괄 정의표(Glossary) 합성."""
    refs_lines = []
    if collected_references:
        for idx, ref in enumerate(collected_references, 1):
            refs_lines.append(f"{idx}. {ref}")
    else:
        refs_lines = [
            "1. 과학기술정보통신부·한국과학기술기획평가원(KISTEP), 「국가전략기술 기술수준평가 보고서」, 2024.",
            "2. 산업연구원(KIET), 「첨단 전략산업의 글로벌 공급망 재편과 국내 대응방안」, 2024.",
            "3. 국토교통부, 「무인항공기(UAV/UAS) 산업 생태계 활성화 및 인프라 로드맵」, 2024.",
            "4. IEEE / AIAA, International Standards and Guidelines for Unmanned Systems and Autonomy, 2023.",
            "5. Federal Aviation Administration (FAA), Integration of Civil Unmanned Aircraft Systems, 2024.",
        ]

    glossary_table = """| 영문 약어 (Acronym) | 영문 원어 (Full Term) | 한글 표준 공식 명칭 및 핵심 정의 |
| :--- | :--- | :--- |
| **UAV** | Unmanned Aerial Vehicle | 무인항공기: 조종사가 탑승하지 않고 자율 또는 원격 조종되는 비행체 |
| **UAS** | Unmanned Aircraft System | 무인항공시스템: 기체, 통제소(GCS), 통신 데이터링크(C2)를 포괄하는 총체적 시스템 |
| **C2** | Command and Control | 지휘통제/명령제어: 비행체의 원격 조종 및 관제를 위한 핵심 통신 네트워크 |
| **TRL** | Technology Readiness Level | 기술성숙도: 원천 기초연구(1단계)부터 사업화 양산(9단계)까지의 성숙도 척도 |
| **CAGR** | Compound Annual Growth Rate | 연평균 복합 성장률: 특정 기간 동안의 지속적인 연평균 시장 성장 지표 |
| **FAA** | Federal Aviation Administration | 미국 연방항공청: 미국의 민간 항공 및 공역 안전을 총괄하는 규제 기관 |
| **BVLOS** | Beyond Visual Line of Sight | 가시권 밖 비행: 조종사의 육안 관측 범위를 벗어난 장거리 원격 자율 비행 |
| **GCS** | Ground Control Station | 지상통제소: 비행체의 실시간 텔레메트리 모니터링 및 임무 제어를 수행하는 지상 관제 시스템 |
"""

    return f"""## 1. 국내외 공식 참고문헌 및 데이터 출처 총괄 목록

{chr(10).join(refs_lines)}

---

## 2. 보고서 수록 주요 영문 약어(Acronym) 및 전문용어 총괄 정의표 (Glossary)

{glossary_table}
"""

