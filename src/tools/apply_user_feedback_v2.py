"""Comprehensive User Feedback Processor (v2 update).

Implements 4 core user requirements:
1. Reconciles in-body table and figure cross-references to match actual tables/figures in context.
2. Strips leading chapter/section numbers (e.g., '1.', '2.1.', '제1절') from table and figure titles.
3. Physical AI & RAMS aggressive hotfix:
   - Fact-finding sections (Chapters Ⅰ~Ⅴ): Eradicates 'Physical AI 기반 RAMS' pseudo-projects, replacing with standard terms.
   - Strategy / Implications sections (Chapters Ⅵ~Ⅶ): Eradicates 'RAMS 사업' (0 instances), softens tone for Physical AI/RAMS.
   - Cleans Goheung / JeonnamTP / launch vehicle leftovers.
4. Saves as new versions (_v2.md, _v3.md, _v5.md) for clean comparison.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.fact_stance_hotfix import clean_fact_stance_all
from src.tools.comprehensive_report_cleaner import (
    clean_anomalies_and_foreign_text,
    strip_narrative_table_prefixes,
    clean_long_caption_descriptions,
    inject_us_report_figures,
    clean_empty_appendix_sections,
    populate_comprehensive_acronym_table,
    clean_and_expand_bibliography,
    rebuild_front_matter_and_toc,
)
from src.utils.markdown_cleaner import indent_body_paragraphs


def strip_leading_section_num(title: str) -> str:
    """Removes leading section numbers like '1.', '1.1.', '2.1.', '제1절' from titles while preserving years."""
    cleaned = re.sub(
        r"^(?:(?:제\s*\d+\s*[장절편]|제\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ]+\s*[장절편]|\d+(?:[\.\-]\d+)+[\.\-]?|\d+\.(?!\d)|[ⅠⅡⅢⅣⅤⅥⅦⅧ]+(?:[\.\-]\d+)*[\.\-]?)\s*)+",
        "",
        title
    ).strip()
    return cleaned


def deep_hotfix_physical_ai_and_rams(doc_text: str) -> str:
    """
    Applies aggressive fact vs stance corrections on Physical AI & RAMS:
    - Purges pseudo-projects ('무인기 고신뢰성 시험평가(RAMS) 인프라 확충(안)', '전남TP/고흥군')
    - Fact-finding (Chapters Ⅰ~Ⅴ): Replaces Physical AI RAMS with standard aerospace terms.
    - Strategy (Chapters Ⅵ~Ⅶ): Eradicates 'RAMS 사업', lowers tone of Physical AI RAMS.
    """
    # 1. Clean general leftovers first
    text = doc_text
    general_cleanups = [
        (r"고흥·영월·화성\s*등\s*분산,\s*통합\s*운영\s*미흡", "국내 시험장 인프라의 고고도·특수환경 실증 한계"),
        (r"국내\s*시험\s*데이터\(고흥/RAMS\s*인프라\)", "국내 무인기 시험평가 데이터"),
        (r"전남TP/고흥군", "한국항공우주연구원, 한국산업기술시험원"),
        (r"전남테크노파크\(전남TP\)\s*주관으로\s*추진된\s*표준화\s*연구\s*용역과", "국내 공인 표준화 연구 용역과"),
        (r"국내\s*RAMS\s*센터-콜로라도\s*시험장\s*데이터\s*교환\s*MOU", "국내 시험평가 기관-콜로라도 시험장 간 시험 데이터 상호 교환 검토"),
        (r"국가\s*전략\s*인프라\s*사업으로\s*추진해야\s*한다", "중장기 정책 과제로 면밀히 검토해 볼 필요가 있다"),
        (r"국내\s*사전검증\(Physical\s*AI\s*RAMS\s*센터\)", "국내 사전검증(공인 시험평가 체계)"),
    ]
    for pat, repl in general_cleanups:
        text = re.sub(pat, repl, text)

    # 2. Process chapter by chapter
    ch_pattern = re.compile(r"(?m)(^##\s+[ⅠⅡⅢⅣⅤⅥⅦⅧ]\.\s*.*?$)")
    parts = ch_pattern.split(text)

    is_fact_chap = True
    new_parts = []

    for part in parts:
        m_heading = re.match(r"^##\s+([ⅠⅡⅢⅣⅤⅥⅦⅧ])\.\s*(.*)", part)
        if m_heading:
            rom = m_heading.group(1)
            is_fact_chap = rom in ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"]
            new_parts.append(part)
            continue

        mod = part
        if is_fact_chap:
            # Fact-finding chapters (Ⅰ~Ⅴ)
            fact_pats = [
                (r"#####\s*5\.\s*무인기\s*고신뢰성\s*시험평가\(RAMS\)\s*인프라\s*확충\(안\)\s*연계성\s*검토",
                 "##### 5. 국내 무인기 감항인증 및 안전성(RAMS) 검증 인프라 연계성 검토"),
                (r"국내에서\s*추진\s*중인\s*[\'\"‘“]?무인기\s*고신뢰성\s*시험평가\(RAMS\)\s*인프라\s*확충\(안\)[\'\"’”]?(?:\s*및\s*[\'\"‘“]?사이버\s*신뢰\s*기반\s*디지털\s*시험평가\s*체계[\'\"’”]?)?\s*구축\s*사업과",
                 "국내 무인기 산업의 신뢰도·안전성(RAMS) 검증 체계 및 사이버 신뢰 시험평가 고도화 수요와"),
                (r"국내에서\s*추진\s*중인\s*[\'\"‘“]?무인기\s*고신뢰성\s*시험평가\(RAMS\)\s*인프라\s*확충\(안\)[\'\"’”]과",
                 "국내 무인기 산업의 신뢰도·안전성(RAMS) 검증 체계 확충 필요성과"),
                (r"무인기\s*고신뢰성\s*시험평가\(RAMS\)\s*인프라\s*확충\(안\)", "무인기 신뢰도·안전성(RAMS) 검증 체계"),
                (r"Physical\s*AI\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:시험·?평가\s*)?(?:센터|인프라|체계|역량)?", "무인기 신뢰도·안전성(RAMS) 검증 체계"),
                (r"Physical\s*AI[·/&]RAMS", "자율비행 및 안전성(RAMS)"),
                (r"Physical\s*AI\s*(?:및\s*)?RAMS", "자율비행 및 신뢰성(RAMS)"),
                (r"Physical\s*AI\s*기반\s*(?:자율\s*)?(?:무인체계|무인기|UAS|드론)", "AI 기반 첨단 자율 무인체계"),
                (r"Physical\s*AI\s*기반\s*자율비행", "고신뢰성 AI 자율비행"),
                (r"Physical\s*AI\s*기반\s*자율\s*(?:시스템|운용)", "첨단 AI 자율 시스템"),
                (r"Physical\s*AI\s*자율비행", "AI 자율비행"),
                (r"Physical\s*AI\s*기술", "인공지능(AI) 자율운용 기술"),
                (r"Physical\s*AI\s*생태계", "첨단 무인기 AI 생태계"),
                (r"Physical\s*AI\s*시대", "AI 자율비행 시대"),
                (r"Physical\s*AI", "인공지능(AI) 기반 자율비행"),
            ]
            for pat, repl in fact_pats:
                mod = re.sub(pat, repl, mod, flags=re.IGNORECASE)
        else:
            # Strategy / Implications chapters (Ⅵ, Ⅶ, Ⅷ)
            strat_pats = [
                (r"무인기\s*고신뢰성\s*시험평가\(RAMS\)\s*인프라\s*확충\(안\)", "차세대 무인기 신뢰성·안전성(RAMS) 검증 인프라"),
                (r"Physical\s*AI\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:구축\s*)?사업\s*(?:과의\s*연계|과\s*연계|연계)?", "차세대 무인기 신뢰성(RAMS) 검증 체계 연계 방안"),
                (r"Physical\s*AI\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:시험·?평가\s*)?센터\s*구축\s*(?:사업)?", "차세대 무인기 신뢰성·안전성(RAMS) 시험평가 인프라 확충 방안"),
                (r"Physical\s*AI\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:구축\s*)?사업", "차세대 무인기 신뢰성(RAMS) 시험·평가 체계 검토 방안"),
                (r"RAMS\s*(?:구축\s*)?사업\s*(?:과의\s*연계|과\s*연계|연계)?", "무인기 신뢰성(RAMS) 검증 체계 연계 방안"),
                (r"RAMS\s*(?:구축\s*)?사업", "무인기 신뢰성(RAMS) 시험·평가 체계 검토 방안"),
                (r"Physical\s*AI[·/&]RAMS\s*(?:기반)?", "자율비행 및 신뢰성(RAMS) "),
                (r"Physical\s*AI\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:평가\s*체계|검증\s*인프라)", "차세대 자율비행 및 신뢰성(RAMS) 검증 인프라"),
                (r"Physical\s*AI\s*UAS", "자율 무인기(UAS)"),
                (r"Physical\s*AI·UAS", "자율비행 무인기(UAS)"),
                (r"Physical\s*AI\s*보안성", "자율비행 AI 보안성"),
                (r"Physical\s*AI\s*기반\s*디지털\s*트윈", "디지털 트윈 기반"),
                (r"Physical\s*AI\s*기반\s*RAMS\s*시험평가\s*인프라", "차세대 무인기 신뢰성(RAMS) 시험평가 인프라"),
                (r"Physical\s*AI\s*실증\s*얼라이언스", "자율비행 실증 얼라이언스"),
                (r"(?:Physical\s*AI|피지컬\s*AI)\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:체계|기술|검증)?(?:의\s*도입|의\s*구축)?(?:을\s*신속히\s*추진해야\s*한다|을\s*추진해야\s*한다|이\s*필수적이다|이\s*불가피하다)",
                 "물리적 인공지능(Physical AI) 및 신뢰도(RAMS) 기술의 도입 필요성을 중장기적 관점에서 면밀히 고려해 볼 필요가 있다"),
                (r"(?:Physical\s*AI|피지컬\s*AI)\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:체계|기술)?(?:와의\s*연계가\s*필수적이다|와\s*연계하여야\s*한다|와\s*연계하여\s*추진해야\s*한다)",
                 "차세대 자율비행 및 신뢰성(RAMS) 기술과의 연계 가능성을 선제적으로 검토해 볼 필요가 있다"),
                (r"반드시\s*Physical\s*AI\s*기반\s*RAMS\s*(?:체계를\s*)?구축해야\s*한다",
                 "중장기적으로 Physical AI 및 RAMS 검증 기술 도입을 검토해 볼 필요가 있다"),
                (r"Physical\s*AI\s*기반\s*자율비행", "인공지능(AI) 기반 자율비행"),
            ]
            for pat, repl in strat_pats:
                mod = re.sub(pat, repl, mod, flags=re.IGNORECASE)

        new_parts.append(mod)

    return "".join(new_parts)


def normalize_all_tables_v2(doc_text: str) -> str:
    """Normalizes all markdown tables, applies section number stripping to titles, and ensures sequential indexing."""
    ch_pattern = re.compile(r"(?m)^##\s+([ⅠⅡⅢⅣⅤⅥⅦⅧ])\.\s*(.*?)$")
    ch_matches = list(ch_pattern.finditer(doc_text))
    if not ch_matches:
        return doc_text

    front_part = doc_text[:ch_matches[0].start()]
    new_chapters = []
    doc_used_titles: dict[str, int] = {}

    KNOWN_DUPLICATE_FIXES = {
        "드론 특구 지정 면적": "유타 주 vs 주요 경합 주(애리조나·텍사스) UAS 진출 환경 비교 분석표",
        "전체 민간용 UAS 시장 규모": "글로벌 민간 UAS 시장 규모 및 AI 기술 적용 전망 비교 분석표",
        "응용 분야": "유타 주 주요 응용 분야별 시장 규모 및 진입 장벽 분석표",
        "1. 인프라 및 실증 환경": "국내 무인기 산업 vs 유타 주 타겟 환경 3대 축별 실증 비교 분석표",
        "UAS 시험 범위 수 (FAA 지정)": "유타 주 항공우주·방위산업 핵심 인프라 및 고용 지표 비교 분석표",
        "3대 진입 트랙의 전략적 목표": "유타 주 맞춤형 3대 진입 트랙별 전략적 목표 및 핵심 지표 비교 분석표",
        "트랙 1: 조기 상용화 트랙": "진출 트랙별 핵심 RAMS 검증 니즈 및 유타 주 활용 인프라 비교 분석표",
        "기대 수익 모델": "유타 주 맞춤형 3대 진입 트랙별 비즈니스 모델 및 활용 자원 비교 분석표",
        "연방 자금 연계 전략": "유타 주 3대 진출 트랙별 지원 프로그램 및 연방 자금 연계 매트릭스",
        "Physical AI·RAMS 실증 연계 전략": "유타 주 자율비행·RAMS 실증 연계 단계별 세부 실행 및 인프라 매핑표",
        "법인세율 (Corporate Tax)": "유타 vs 주요 경합 주(캘리포니아·텍사스·플로리다) 조세 및 비즈니스 환경 비교 분석표",
        "소프트랜딩(Soft-Landing) 및 생태계 편입": "유타 주 2대 축별(진출 로드맵 vs 리스크 관리) 전략적 연계 종합 평가표",
        "항공우주 부품 제조(NAICS 336413)": "콜로라도 주 진출 한국 기업의 업종별 분포 및 산업 특화도 비교표",
        "콜로라도 주 vs 주요 경쟁 주": "콜로라도 주 vs 주요 경쟁 주(캘리포니아, 텍사스, 플로리다) UAS 진출 환경 비교 분석표",
        "글로벌 타겟 시장 환경 및 콜로라도 클러스터": "글로벌 타겟 시장 환경 및 콜로라도 클러스터 핵심 지표 요약 및 시사점",
        "콜로라도 주 내 국내 항공우주·방산 기업 진출 현황": "콜로라도 주 내 국내 항공우주·방산 기업 진출 현황 비교 분석표",
        "지역별 UAV 시장 규모 추이": "지역별 UAV 시장 규모 추이 및 세그먼트별 구조 분석표 (2023~2028)",
        "BVLOS(가시권 밖 비행) 정례 승인 건수": "한국 vs 콜로라도 주 무인기 제도·규제 및 실증 환경 격차 비교표",
        "AeroVironment, Lockheed Mar": "콜로라도 주 및 주요 타겟 지역별 시장 규모·성장률 비교 분석표",
        "시험공간 밀도": "미국 주요 주별 항공우주·무인기 지원 환경 및 경쟁력 비교 분석표",
        "국내 무인기 기업의 미국 진출 시 직면하는 핵심 애로사항": "국내 무인기 기업의 미 진출 핵심 애로사항 및 버지니아 주 대응 역량 1:1 매핑표",
        "밸리 오브 데스": "미국·유럽·한국 시장 진출 지원 프로그램 및 제도 비교 분석표",
        "5점 만점 기준": "버지니아 주 vs 타 주요 주 주요 지원 항목 및 규제 부담 비교 평가표",
        "버지니아 주 산업 생태계의 정량적 비교 우위": "버지니아 주 산업 생태계의 정량적 비교 우위 및 맞춤형 인센티브 실증 분석표",
        "항공우주·방산 기업 수 (개)": "버지니아 vs 경쟁 주(텍사스·캘리포니아) 항공우주·방산 클러스터 비교표",
        "1. 진출 실행 전략": "버지니아 주 진출 실행 전략 및 리스크 관리 핵심 메커니즘 분석표",
        "SAM.gov 등록 및 CAGE 코드 보유 기업 수": "국내 기업군 텍사스 진출 핵심 준비도 지표 비교 분석표",
        "주 GDP $2.4T": "텍사스 주 항공우주·UAS 시장 환경 및 시사점 다차원 분석표",
        "텍사스 기업 성장 펀드 및 세액 공제": "텍사스 주 진출 기대효과 및 정량 지표 시뮬레이션 분석표",
        "텍사스 이동성 기금(TMF": "한·미(텍사스)·EU UAS 지원 프로그램 및 정책 제도 비교 분석표",
        "텍사스 émerging 기술 보조금": "텍사스 vs 주요 주(캘리포니아·뉴욕) UAS 지원 환경 비교 평가표",
        "FAA Part 23/33": "캘리포니아 주 UAS 위험 기반 인증 체계 및 정책·제도 핵심 이슈 분석표",
        "글로벌 UAV 산업 주요 세그먼트별 시장 규모": "글로벌 UAV 산업 주요 세그먼트별 시장 규모 및 전망 분석표",
        "UAV 보수교육 체계의 핵심 지표": "주요국 및 기구별 UAV 보수교육 체계 핵심 지표 종합 비교표",
        "Replicator Initiative, 드론 혁신획득체계": "글로벌 무인기 산업 생태계 파급효과 및 핵심 동인 분석표",
        "AI/자율비행 기초 교육과정 개설": "UAV 보수교육 체계 고도화에 따른 단계별 작전 운용 파급효과 분석표",
        "2024년 시장 규모 (추정)": "주요국(미국·EU·중국) UAV 시장 규모 및 교육 수요 비교 분석표",
        "보수교육 의무화 주기 및 법적 강제력": "글로벌 선도국 대비 국내 UAV 보수교육 법·제도 거버넌스 격차 분석표",
        "자격 체계 모듈화 및 거버넌스 민첩성": "UAV 보수교육 정책·제도 핵심 이슈 및 미래 전망 요약표",
        "보수교육 법제도의 '모듈형·실시간화'": "선도국 동향 근거 기반 보수교육 모듈형 전환 핵심 시사점 분석표",
        "위 5개국을 대상으로": "비NATO 5개국 UAV 하드웨어·SW·통신·공급망·통합 인증 5대 영역 핵심 지표 비교표",
        "주요국 UAV 인증 체계 및 핵심 지표": "글로벌 주요국 UAV 인증 체계 및 핵심 지표 종합 비교 분석표",
        "UAS 분야 글로벌 특허 동향": "UAS 분야 글로벌 패밀리 특허 출원 추이 및 핵심 권리자 비교 분석표",
        "중남미 주요국 UAV 인증·운영 정책 핵심 지표": "중남미 주요국 UAV 인증·운영 정책 핵심 지표 요약표",
        "중남미 주요국 UAV 인증·운영 정책 동향": "중남미 주요국 UAV 인증·운영 정책 동향 및 규제 프레임워크 비교 분석 세부 실증 비교 분석표",
        "IEC 62485, 환경 가혹도 시험": "중남미 무인기 부품·소재 신뢰성 기준 및 국내 비교 분석표",
        "1단계: 기체 중심 정적 인증": "무인기 정적 기체 감항성 대비 시스템·SW 보안 인증 패러다임 전환 비교표",
        "Physical AI·UAS 관련 특허 출원 건수": "중남미 및 글로벌 연도별 자율비행·UAS 특허 출원 추이 분석표",
        "국가별 인증 파편화 (브라질/멕시코/아르헨티나": "중남미 무인기 시장 구조적 병목 및 한국 기업 레버리지 전략 분석표",
        "부품 단위 인증 의무화 비율": "글로벌 주요국 부품 단위 인증 및 신뢰성 평가 기준 비교표",
        "5대 영역별로 차등화된 추격 전략": "대 캐나다 UAV 5대 핵심 영역별 기술 격차 및 추격 전략 매트릭스",
        "DO-178C Level A/B 보유 기종 수": "캐나다 vs 주요국 무인기 핵심 기술 수준 및 비행제어 SW 인증 레벨 비교표",
        "DO-160G Env. Test, DO-311A Battery": "글로벌 선도국 대비 캐나다 무인기 부품·소재 신뢰성 기술 격차 분석표",
        "As-Is와 목표 수준": "호주 무인기 산업 현황(As-Is) 대비 목표(To-Be) 5대 영역 격차 분석표",
        "Fortune Business": "글로벌 UAV 시장 세그먼트별 규모 및 성장률 전망 분석표",
        "최근 5년간 국내·외 주요 UAS 인증·시험평가 인프라": "한-호주 주요 UAS 인증·시험평가 인프라 및 시험 역량 비교 분석표",
        "4대 범주로 구조화하여": "호주 UAV 시장 진출 정책·제도·R&D·공급망 4대 범주 핵심 시사점 종합 분석표",
        "Physical AI 특허 수": "주요 글로벌 기업/기관별 자율비행 특허 보유 현황 비교표",
        "인증 가능 인력 < 50명": "국내 vs 글로벌 선도국 항공 SW 인증 역량 격차 실증 비교표",
        "부품 국산화·공급망 다변화": "호주 무인기 시장 진출 핵심 대응 전략 및 단계별 실행 권고사항 종합표",
    }

    for idx, m in enumerate(ch_matches):
        roman = m.group(1)
        ch_title = m.group(2).strip()
        start_pos = m.start()
        end_pos = ch_matches[idx + 1].start() if idx + 1 < len(ch_matches) else len(doc_text)
        ch_text = doc_text[start_pos:end_pos]

        lines = ch_text.splitlines()
        new_lines = []
        tbl_counter = 0

        i = 0
        n = len(lines)
        current_section_title = ch_title

        while i < n:
            line = lines[i]

            h_m = re.match(r"^#{2,5}\s+(\d+[\.\)]?\s*[^\n]+)", line)
            if h_m:
                current_section_title = h_m.group(1).strip()

            if line.strip().startswith("|") and ("|" in line.strip()[1:]):
                tbl_counter += 1
                table_lines = []
                while i < n and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1

                table_content_str = "\n".join(table_lines)

                extracted_title = ""
                while True:
                    prev_idx = len(new_lines) - 1
                    while prev_idx >= 0 and not new_lines[prev_idx].strip():
                        prev_idx -= 1
                    if prev_idx < 0:
                        break
                    cand = new_lines[prev_idx].strip()
                    m_cap = re.search(
                        r"(?i)(?:<p[^>]*>)?\s*(?:\*{0,2}|<strong>)?\s*(?:\[표\s*[^\]]+\]|【표\s*[^】]+】|<표\s*[^>]+>|표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\.\-]+:?|\[표\])\s*(?:</strong>|\*{0,2})?\s*(.*?)(?:</p>)?$",
                        cand,
                    )
                    if m_cap:
                        cand_title = m_cap.group(1).strip().strip("*").strip("<>").strip(":").strip()
                        is_narrative = (
                            any(cand_title.startswith(c) for c in ("은 ", "는 ", "이 ", "가 ", "에서 ", "과 같다", "와 같다", "참조", "와 같이", "에 따르면"))
                            or any(v in cand for v in ("상기 표에서", "위 표에서", "도출되는 시사점", "정리한 것이다", "확인할 수 있다", "비교한 것이다", "종합한 것이다"))
                        )
                        if cand_title and not is_narrative and len(cand_title) < 70 and not extracted_title:
                            extracted_title = cand_title
                        new_lines.pop(prev_idx)
                    else:
                        break

                next_idx = i
                while next_idx < n and not lines[next_idx].strip():
                    next_idx += 1
                if next_idx < n:
                    next_cand = lines[next_idx].strip()
                    m_next = re.search(
                        r"(?i)^\s*(?:\*{0,2}|<strong>)?(?:\[표\s*[^\]]+\]|【표\s*[^】]+】|<표\s*[^>]+>|표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\.\-]+:?)\s*(?:</strong>|\*{0,2})?\s*(.*?)$",
                        next_cand,
                    )
                    if m_next:
                        cand_title = m_next.group(1).strip().strip("*").strip("<>").strip(":").strip()
                        is_narrative = any(cand_title.startswith(c) for c in ("은 ", "는 ", "이 ", "가 ", "에서 ", "과 같다", "와 같다", "참조"))
                        if not is_narrative:
                            if not extracted_title and len(cand_title) < 70:
                                extracted_title = cand_title
                        i = next_idx + 1

                for key_snippet, resolved_title in KNOWN_DUPLICATE_FIXES.items():
                    if key_snippet in table_content_str or (extracted_title and key_snippet in extracted_title):
                        extracted_title = resolved_title
                        break

                if roman == "Ⅷ" and ("영문 약어" in table_content_str or "약어" in current_section_title or "Acronym" in current_section_title):
                    extracted_title = "주요 영문 약어(Acronym) 및 국문 정의 총괄표"

                is_generic = (
                    not extracted_title
                    or len(extracted_title) < 4
                    or any(gt in extracted_title for gt in (
                        "종합 소결", "소결", "핵심 지표 요약표", "기초 현황 분석 종합",
                        "거시·미시 환경", "대정부·산업계 최종 정책 권고사항",
                        "향후 파급효과", "세부 데이터 실증 분석",
                        "대응 전략 및 실행 권고사항", "최신 기술 동향 및 표준화·특허 분석",
                        "해외 시장 진출 전략 및 맞춤형 트랙 설계",
                        "진출 실행 가이드라인 및 통상·인증 리스크 관리 방안",
                    ))
                )

                if is_generic:
                    sec_clean = re.sub(r"^\d+[\.\)]?\s*", "", current_section_title).strip()
                    if "소결" in sec_clean or "소결" in extracted_title:
                        extracted_title = f"{ch_title} 종합 소결 및 전략적 시사점 핵심 요약표"
                    elif "약어" in sec_clean or "Acronym" in sec_clean:
                        extracted_title = "주요 영문 약어(Acronym) 및 국문 정의 총괄표"
                    elif any(sec_clean.endswith(tail) for tail in ("분석표", "요약표", "비교표", "매트릭스", "구조도")):
                        extracted_title = f"{sec_clean}"
                    else:
                        extracted_title = f"{sec_clean} 세부 실증 비교 분석표"

                # Strip leading section numbers ('1.', '2.1.', '제1절' etc.)
                extracted_title = strip_leading_section_num(extracted_title)

                if extracted_title in doc_used_titles:
                    doc_used_titles[extracted_title] += 1
                    cnt = doc_used_titles[extracted_title]
                    clean_cap = f"**[표 {roman}-{tbl_counter}]** {extracted_title} (추진 지표 {cnt})"
                else:
                    doc_used_titles[extracted_title] = 1
                    clean_cap = f"**[표 {roman}-{tbl_counter}]** {extracted_title}"

                if new_lines and new_lines[-1].strip():
                    new_lines.append("")
                new_lines.append(clean_cap)
                new_lines.append("")
                new_lines.extend(table_lines)
                continue

            new_lines.append(line)
            i += 1

        new_chapters.append("\n".join(new_lines))

    return front_part + "\n".join(new_chapters)


def normalize_all_figures_v2(doc_text: str) -> str:
    """Normalizes all figures, strips leading section numbers from titles, and preserves subtitles."""
    ch_pattern = re.compile(r"(?m)^##\s+([ⅠⅡⅢⅣⅤⅥⅦⅧ])\.\s*(.*?)$")
    ch_matches = list(ch_pattern.finditer(doc_text))
    if not ch_matches:
        return doc_text

    front_part = doc_text[:ch_matches[0].start()]
    new_chapters = []
    doc_used_figure_titles: dict[str, int] = {}

    for idx, m in enumerate(ch_matches):
        roman = m.group(1)
        ch_title = m.group(2).strip()
        start_pos = m.start()
        end_pos = ch_matches[idx + 1].start() if idx + 1 < len(ch_matches) else len(doc_text)
        ch_text = doc_text[start_pos:end_pos]

        lines = ch_text.splitlines()
        new_lines = []
        fig_counter = 0

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]

            fig_match = re.match(
                r"^\s*(?:>\s*)*(?:#{3,5}\s*)?\*{0,2}【그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)】\*{0,2}\s*(.*?)$",
                line
            )
            if fig_match and not any(line.strip().startswith(c) for c in (">", "|", "-")):
                raw_title = fig_match.group(2).strip().strip("*").strip()
                fig_counter += 1

                is_narrative = any(raw_title.startswith(c) for c in ("은 ", "는 ", "이 ", "가 ", "에서 ", "과 같다", "와 같다", "참조"))
                if is_narrative:
                    new_lines.append(f"【그림 {roman}-{fig_counter}】 {raw_title}")
                    i += 1
                    continue

                clean_title = raw_title
                next_idx = i + 1
                while next_idx < n and not lines[next_idx].strip():
                    next_idx += 1

                if next_idx < n:
                    cand_sub = lines[next_idx].strip()
                    if not cand_sub.startswith(">") and not cand_sub.startswith("#") and not cand_sub.startswith("|") and len(cand_sub) > 5 and len(cand_sub) < 100:
                        if not any(cand_sub.startswith(c) for c in ("-", "*", "※", "본 도식화", "본 그림", "이 그림")):
                            clean_title = cand_sub
                            i = next_idx

                if not clean_title or len(clean_title) < 4:
                    clean_title = f"{ch_title} 주요 도식화 프레임워크"

                clean_title = re.sub(r"^\s*-\s*\*\*구조도\*\*:\s*", "", clean_title)
                clean_title = re.sub(r"\s*\(추진 모델 \d+\)", "", clean_title)
                # Strip leading section numbers ('1.', '2.1.', '제1절' etc.)
                clean_title = strip_leading_section_num(clean_title)

                if clean_title in doc_used_figure_titles:
                    doc_used_figure_titles[clean_title] += 1
                    cnt = doc_used_figure_titles[clean_title]
                    clean_title = f"{clean_title} (추진 모델 {cnt})"
                else:
                    doc_used_figure_titles[clean_title] = 1

                new_lines.append(f"**【그림 {roman}-{fig_counter}】** {clean_title}")
                i += 1
            else:
                new_lines.append(line)
                i += 1

        new_chapters.append("\n".join(new_lines))

    return front_part + "\n".join(new_chapters)


def reconcile_in_body_cross_references(doc_text: str) -> tuple[str, int]:
    """
    Reconciles in-body references like '<표 Ⅱ-1-1>', '[표 Ⅲ-1-3]', '<그림 Ⅳ-1-1>'
    to match the exact normalized table and figure tags in context.
    """
    lines = doc_text.splitlines()
    tables = []
    figures = []
    for idx, l in enumerate(lines):
        m_t = re.match(r"^\s*\*{0,2}\[표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)\]\*{0,2}\s*(.*)", l)
        if m_t:
            tables.append((idx, m_t.group(1), m_t.group(2).strip()))
        m_f = re.match(r"^\s*\*{0,2}【그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)】\*{0,2}\s*(.*)", l)
        if m_f:
            figures.append((idx, m_f.group(1), m_f.group(2).strip()))

    ch1_match = re.search(r"(?m)^##\s+Ⅰ\.", doc_text)
    body_start_line = 0
    if ch1_match:
        body_start_line = len(doc_text[:ch1_match.start()].splitlines())

    total_changes = 0
    new_lines = []

    for idx, l in enumerate(lines):
        if idx < body_start_line or re.match(r"^\s*\*{0,2}(\[표|【그림)", l):
            new_lines.append(l)
            continue

        mod_l = l

        # Tables
        t_pattern = re.compile(r"(<표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)>|\[표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)\]|(?<![가-힣\w])표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)(?![가-힣\w]))")
        def replace_t(match):
            nonlocal total_changes
            raw = match.group(0)
            num = match.group(2) or match.group(3) or match.group(4)
            m_rom = re.match(r"^([ⅠⅡⅢⅣⅤⅥⅦⅧ])", num)
            cands = [t for t in tables if t[1].startswith(m_rom.group(1))] if m_rom else tables
            if not cands:
                cands = tables

            is_prior = any(k in l for k in ["상기", "앞서", "위의", "분석 결과", "도출된 바", "확인되듯", "나타난 바", "식별된", "제시한"])
            is_next = any(k in l for k in ["다음", "아래", "과 같다", "와 같다", "제시한다"])
            if is_prior and not is_next:
                p_cands = [t for t in cands if t[0] < idx]
                best = min(p_cands, key=lambda t: idx - t[0]) if p_cands else min(cands, key=lambda t: abs(t[0] - idx))
            elif is_next and not is_prior:
                n_cands = [t for t in cands if t[0] > idx]
                best = min(n_cands, key=lambda t: t[0] - idx) if n_cands else min(cands, key=lambda t: abs(t[0] - idx))
            else:
                best = min(cands, key=lambda t: abs(t[0] - idx))

            target_num = best[1]
            if raw.startswith("<"):
                res = f"<표 {target_num}>"
            elif raw.startswith("["):
                res = f"[표 {target_num}]"
            else:
                res = f"표 {target_num}"
            if raw != res:
                total_changes += 1
            return res

        mod_l = t_pattern.sub(replace_t, mod_l)

        # Figures
        f_pattern = re.compile(r"(<그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)>|【그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)】|(?<![가-힣\w])그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)(?![가-힣\w]))")
        def replace_f(match):
            nonlocal total_changes
            raw = match.group(0)
            num = match.group(2) or match.group(3) or match.group(4)
            m_rom = re.match(r"^([ⅠⅡⅢⅣⅤⅥⅦⅧ])", num)
            cands = [f for f in figures if f[1].startswith(m_rom.group(1))] if m_rom else figures
            if not cands:
                cands = figures

            is_prior = any(k in l for k in ["상기", "앞서", "위의", "분석 결과", "도출된 바", "확인되듯", "나타난 바", "제시한"])
            is_next = any(k in l for k in ["다음", "아래", "과 같다", "와 같다", "제시한다"])
            if is_prior and not is_next:
                p_cands = [f for f in cands if f[0] < idx]
                best = min(p_cands, key=lambda f: idx - f[0]) if p_cands else min(cands, key=lambda f: abs(f[0] - idx))
            elif is_next and not is_prior:
                n_cands = [f for f in cands if f[0] > idx]
                best = min(n_cands, key=lambda f: f[0] - idx) if n_cands else min(cands, key=lambda f: abs(f[0] - idx))
            else:
                best = min(cands, key=lambda f: abs(f[0] - idx))

            target_num = best[1]
            if raw.startswith("<"):
                res = f"<그림 {target_num}>"
            elif raw.startswith("【"):
                res = f"【그림 {target_num}】"
            else:
                res = f"그림 {target_num}"
            if raw != res:
                total_changes += 1
            return res

        mod_l = f_pattern.sub(replace_f, mod_l)
        new_lines.append(mod_l)

    return "\n".join(new_lines), total_changes


def process_report_file(src_path: Path, dest_path: Path) -> dict:
    """Full processing pipeline for a single report producing a new version file."""
    text = src_path.read_text(encoding="utf-8")
    is_us = "미국" in src_path.name

    # Step 0: Fact stance hotfixes + Deep Physical AI & RAMS purge
    step0, _ = clean_fact_stance_all(text)
    step0 = deep_hotfix_physical_ai_and_rams(step0)

    # Step 1: Anomalies and prompt leakages
    step1 = clean_anomalies_and_foreign_text(step0)

    # Step 2: Strip narrative table tags
    step2 = strip_narrative_table_prefixes(step1)

    # Step 3: Clean long caption descriptions
    step3 = clean_long_caption_descriptions(step2)

    # Step 4: Inject US report figures if US
    if is_us:
        step3 = inject_us_report_figures(step3)

    # Step 5: Clean empty appendix sections
    step4 = clean_empty_appendix_sections(step3)

    # Step 6: Update acronym table
    step5 = populate_comprehensive_acronym_table(step4)

    # Step 7: Normalize all tables (with section number stripping)
    step6 = normalize_all_tables_v2(step5)

    # Step 8: Normalize all figures (with section number stripping)
    step7 = normalize_all_figures_v2(step6)

    # Step 9: Reconcile in-body cross-references to match actual table/figure tags
    step8, ref_changes = reconcile_in_body_cross_references(step7)

    # Step 10: Clean and expand bibliography
    step9 = clean_and_expand_bibliography(step8, is_us_report=is_us)

    # Step 11: Rebuild front matter and TOC
    step10 = rebuild_front_matter_and_toc(step9)

    # Step 12: Indent body paragraphs
    try:
        final_text = indent_body_paragraphs(step10)
    except Exception:
        final_text = step10

    # Save to NEW version path
    dest_path.write_text(final_text, encoding="utf-8")

    # Audit statistics
    lines = final_text.splitlines()
    body_tables = len(re.findall(r"(?m)^\s*\*{0,2}\[표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)\]", final_text))
    toc_tables = len([l for l in lines[:500] if re.match(r"^\s*-\s*\*\*\[표", l)])
    body_figs = len(re.findall(r"(?m)^\s*\*{0,2}【그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)】", final_text))
    toc_figs = len([l for l in lines[:500] if re.match(r"^\s*-\s*\*\*【그림", l)])

    # Duplicates
    table_titles = [re.sub(r"^\s*\*{0,2}\[표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+\]\*{0,2}\s*", "", l).strip() for l in lines if re.match(r"^\s*\*{0,2}\[표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+\]", l)]
    t_dups = len(table_titles) - len(set(table_titles))
    fig_titles = [re.sub(r"^\s*\*{0,2}【그림\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+】\*{0,2}\s*", "", l).strip() for l in lines if re.match(r"^\s*\*{0,2}【그림\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+】", l)]
    f_dups = len(fig_titles) - len(set(fig_titles))

    # Leading section numbers in TOC
    toc_lines = [l for l in lines[:500] if re.match(r"^\s*-\s*\*\*(\[표|【그림)", l)]
    leading_sec_in_toc = 0
    for l in toc_lines:
        if re.search(r"^\s*-\s*\*\*(?:\[표|【그림)\s*[^\]】]+(?:\s*\]|\s*】)\*\*\s*(?:<[^>]+>\s*)?((?:제\s*\d+\s*[장절편]|제\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ]+\s*[장절편]|\d+(?:[\.\-]\d+)+[\.\-]?|\d+\.(?!\d)|[ⅠⅡⅢⅣⅤⅥⅦⅧ]+(?:[\.\-]\d+)*[\.\-]?)\s+)", l):
            leading_sec_in_toc += 1

    rams_project_count = len(re.findall(r"(?:Physical\s*AI\s*(?:기반\s*)?)?(?:UAS\s*)?RAMS\s*(?:구축\s*)?사업", final_text, re.IGNORECASE))
    centers = len(re.findall(r"<center>", final_text, re.IGNORECASE))

    return {
        "src_name": src_path.name,
        "dest_name": dest_path.name,
        "body_tables": body_tables,
        "toc_tables": toc_tables,
        "table_match": body_tables == toc_tables and body_tables > 0,
        "body_figs": body_figs,
        "toc_figs": toc_figs,
        "fig_match": body_figs == toc_figs and body_figs > 0,
        "t_dups": t_dups,
        "f_dups": f_dups,
        "leading_sec_in_toc": leading_sec_in_toc,
        "ref_changes": ref_changes,
        "rams_project_count": rams_project_count,
        "centers": centers,
    }


def main():
    file_map = [
        (Path("workspace/report/유타_주_내_국내기업_진출_가이드라인_p5_final_v4.md"),
         Path("workspace/report/유타_주_내_국내기업_진출_가이드라인_p5_final_v5.md")),
        (Path("workspace/report/버지니아_주_내_국내기업_진출_가이드라인_p5_final_v1.md"),
         Path("workspace/report/버지니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md")),
        (Path("workspace/report/콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v1.md"),
         Path("workspace/report/콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v2.md")),
        (Path("workspace/report/텍사스_주_내_국내기업_진출_가이드라인_p5_final_v1.md"),
         Path("workspace/report/텍사스_주_내_국내기업_진출_가이드라인_p5_final_v2.md")),
        (Path("workspace/report/캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v1.md"),
         Path("workspace/report/캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v2.md")),
        (Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v1.md"),
         Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v2.md")),
        (Path("workspace/report/변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v1.md"),
         Path("workspace/report/변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v2.md")),
    ]

    print("=== Processing Reports with User Feedback Improvements ===")
    results = []
    for src, dest in file_map:
        if not src.exists():
            print(f"[SKIP] Source not found: {src.name}")
            continue
        res = process_report_file(src, dest)
        results.append(res)
        print(f"[DONE] {src.name} -> {dest.name}")
        print(f"       Tables: {res['body_tables']} (Match: {res['table_match']}) | Figs: {res['body_figs']} (Match: {res['fig_match']})")
        print(f"       Ref changes: {res['ref_changes']} | TOC Leading Sec: {res['leading_sec_in_toc']} | RAMS 사업: {res['rams_project_count']}")

    print("\n=== SUMMARY TABLE ===")
    print(f"| 신규 버전 보고서명 | 본문 표 | 표 목차 | 일치 | 본문 그림 | 그림 목차 | 일치 | 목차 절번호 잔류 | 본문 참조 교정 | RAMS 사업 |")
    print(f"|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for r in results:
        t_m = "✅" if r["table_match"] else "❌"
        f_m = "✅" if r["fig_match"] else "❌"
        sec_m = f"{r['leading_sec_in_toc']}건"
        ref_m = f"{r['ref_changes']}건 교정"
        proj_m = f"{r['rams_project_count']}건"
        print(f"| {r['dest_name']} | {r['body_tables']} | {r['toc_tables']} | {t_m} | {r['body_figs']} | {r['toc_figs']} | {f_m} | {sec_m} | {ref_m} | {proj_m} |")


if __name__ == "__main__":
    main()
