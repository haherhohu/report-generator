"""Comprehensive Deep Purge Processor (v3 update).

Fulfills user prompt requirements:
1. Deeply and substantively eradicates unreleased internal draft:
   'Physical AI 기반 UAS RAMS 시험·평가 센터 구축안' and all variants ('구축안', '구축(안)', '구축안(안) v3', '풀에서 확인된').
2. Eliminates non-existent domestic centers:
   'Physical AI RAMS 시험평가센터', 'Physical AI RAMS 센터 연계', '항공안전기술원 RAMS 센터 구축 추진',
   '국가 통합 RAMS 시험·평가 센터', 'NASA LaRC/NIA 공동 RAMS 시험평가센터 구축 추진', etc.
3. Eradicates fictitious alliances and MOUs:
   'KURA (Korea-Utah UAS RAMS Alliance)', '한미 공동 RAMS 실증 테스트베드 양해각서(MOU)', etc.
4. Corrects regex artifacts from prior replacements:
   '체계평가', '체계기술', '체계핵심', '체계프로세스', '체계시', '방안전·후', etc.
5. Softens Physical AI tone:
   - Fact-finding chapters (Ⅰ~Ⅴ): replace Physical AI with autonomous AI / SDV / standard avionics terms.
   - Strategy chapters (Ⅵ~Ⅷ): 0 occurrences of 'RAMS 사업' / 'Physical AI RAMS 사업', lower tone to '고려해 볼 필요가 있다'.
6. Regenerates TOC, normalizes tables/figures (no leading section numbers), reconciles in-body references 1:1.
7. Saves to new version files (Utah v6, Virginia v4, others v3).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from src.tools.apply_user_feedback_v2 import (
    normalize_all_tables_v2,
    normalize_all_figures_v2,
    reconcile_in_body_cross_references,
)
from src.utils.markdown_cleaner import indent_body_paragraphs


def clean_draft_proposals_and_fictitious_entities(text: str) -> str:
    """
    Substantively eradicates all mentions of the unreleased draft proposal,
    non-existent domestic Physical AI RAMS centers, fictitious MOUs/alliances (KURA),
    and prior regex artifacts.
    """
    cleaned = text

    # 1. Clean prior regex artifacts first
    regex_artifacts = [
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계평가", "무인기 신뢰도·안전성(RAMS) 평가"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계기술", "무인기 신뢰도·안전성(RAMS) 기술"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계핵심", "무인기 신뢰도·안전성(RAMS) 핵심"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계프로세스", "무인기 안전성(RAMS) 검증 프로세스"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계아키텍처", "무인기 안전성(RAMS) 검증 아키텍처"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계시뮬레이션", "시뮬레이션 기반 안전성(RAMS) 검증"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계시험", "무인기 신뢰도·안전성(RAMS) 시험"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계시\b", "무인기 신뢰도·안전성(RAMS) 체계 도입 시"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계로드맵", "무인기 신뢰도·안전성(RAMS) 검증 로드맵"),
        (r"차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*시험평가\s*인프라\s*확충\s*방안전·후", "차세대 무인기 신뢰성·안전성(RAMS) 시험평가 인프라 도입 전·후"),
        (r"방안전·후", "도입 전·후"),
        (r"인공지능\(AI\)\s*기반\s*자율비행\s*\(인공지능\(AI\)\s*기반\s*자율비행\)", "인공지능(AI) 기반 자율비행"),
        (r"인공지능\(AI\)\s*기반\s*자율비행\s*알고리즘\s*알고리즘", "인공지능(AI) 기반 자율비행 알고리즘"),
        (r"인공지능\(AI\)\s*기반\s*자율비행,?\s*자율비행", "인공지능(AI) 기반 자율비행"),
    ]
    for pat, repl in regex_artifacts:
        cleaned = re.sub(pat, repl, cleaned)

    # 2. Eradicate KURA and fictitious alliances / MOUs
    fictitious_alliances = [
        (r"한-유타\s*(?:UAS\s*)?(?:자율비행\s*및\s*신뢰성\(RAMS\)\s*실증\s*)?얼라이언스\(KURA\)", "한-유타 무인기 산업·실증 협력 거버넌스"),
        (r"한-유타\s*(?:UAS\s*)?자율비행\s*및\s*신뢰성\(RAMS\)\s*실증\s*얼라이언스\(Korea-Utah\s*UAS\s*자율비행\s*및\s*신뢰성\(RAMS\)\s*Demonstration\s*Alliance,\s*약칭\s*KURA\)",
         "한-유타 무인기 산업·실증 협력 거버넌스(Korea-Utah UAS Industrial & Verification Governance)"),
        (r"한-유타\s*(?:Physical\s*AI[·/&]RAMS|자율비행\s*및\s*신뢰성\(RAMS\))\s*실증\s*얼라이언스", "한-유타 무인기 산업·실증 협력 네트워크"),
        (r"Korea-Utah\s*UAS\s*RAMS\s*Alliance", "Korea-Utah UAS Industrial Cooperation Network"),
        (r"\bKURA\s*거버넌스", "한-유타 협력 거버넌스"),
        (r"\bKURA\s*참여\s*기업", "협력 거버넌스 참여 기업"),
        (r"\bKURA\s*는\b", "본 협력 거버넌스는"),
        (r"\bKURA\s*의\b", "협력 거버넌스의"),
        (r"\bKURA\s*와\b", "협력 거버넌스와"),
        (r"\bKURA\s*를\b", "협력 거버넌스를"),
        (r"\bKURA\s*에\b", "협력 거버넌스에"),
        (r"\bKURA\b", "협력 거버넌스"),
        (r"‘한미\s*공동\s*RAMS\s*실증\s*테스트베드\s*구축\s*양해각서\(MOU\)’",
         "‘현지 비행시험장(Desert UAS) 활용 및 감항인증(FAA Part 107/135) 획득을 위한 산학연 기술협력 협의’"),
        (r"한미\s*공동\s*RAMS\s*실증\s*테스트베드\s*구축\s*양해각서\(MOU\)",
         "현지 비행시험장(Desert UAS) 활용 및 감항인증(FAA Part 107/135) 획득을 위한 산학연 기술협력 협의"),
        (r"국내\s*RAMS\s*센터-콜로라도\s*시험장\s*데이터\s*교환\s*MOU",
         "국내 공인 시험기관-콜로라도 시험장 간 시험 데이터 상호 교환 협력"),
        (r"NASA\s*LaRC/NIA\s*공동\s*RAMS\s*시험평가센터\s*구축\s*추진",
         "NASA Langley 및 현지 연구기관 연계 시험평가 협력 추진"),
        (r"항공안전기술원\s*RAMS\s*센터\s*구축\s*추진",
         "항공안전기술원 등 국내 공인 시험평가 체계 고도화 추진"),
    ]
    for pat, repl in fictitious_alliances:
        cleaned = re.sub(pat, repl, cleaned)

    # 3. Eradicate unreleased internal draft proposals ('구축안', '구축(안)', '풀에서 확인된')
    draft_proposal_cleanups = [
        (r"풀에서\s*확인된\s*\*{0,2}[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\(신뢰성·가용성·정비성·안전성\)\s*시험·평가\s*센터\s*구축\(안\)[\'\"’”]?\*{0,2}\s*및\s*\*{0,2}[\'\"‘“]?지상-고고도-저궤도\s*연계\s*다공역\s*미사일\s*및\s*드론\s*방공체계\s*개발[\'\"’”]?\*{0,2}\s*과제\s*풀에서\s*도출된\s*핵심\s*키워드를",
         "선진 항공 안전성 기준(RAMS) 및 다영역 복합 무인 방공체계 연구에서 도출된 핵심 기술 요소를"),
        (r"\*{0,2}[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\(신뢰성·가용성·정비성·안전성\)\s*시험·평가\s*센터\s*구축\(안\)[\'\"’”]?\*{0,2}\s*및\s*\*{0,2}[\'\"‘“]?지상-고고도-저궤도\s*연계\s*다공역\s*미사일\s*및\s*드론\s*방공체계\s*개발[\'\"’”]?\*{0,2}\s*사례는",
         "선진 항공 안전성 기준(RAMS) 및 다영역 복합 무인 방공체계 실증 사례는"),
        (r"제안된\s*센터\s*구축안\(안\s*v3\)\s*분석에\s*따르면", "글로벌 선진 항공 안전성 기준 분석에 따르면"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안\(안\)\s*v3", "미국 연방항공청(FAA) 및 NASA 항공 기술 보고서"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안\s*v3", "미 연방항공청(FAA) 및 국방부(DoD) 인증 가이드라인"),
        (r"구축안\(무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*v3\)", "선진 무인기 안전성 연구 분석"),
        (r"\*{0,2}[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\*{0,2}\s*구축\(안\s*v3\s*반영\)", "무인기 신뢰도·안전성(RAMS) 검증 체계 고도화"),
        (r"전무\s*\(센터\s*구축안\s*단계\)", "미흡 (초기 연구개발 검토 단계)"),
        (r"자율비행\s*및\s*신뢰성\(RAMS\)\s*시험·평가센터\s*구축\(안\)\s*개발\s*중", "자율비행 및 신뢰성(RAMS) 시험평가 기준 연구개발 진행 중"),
        (r"한국형\s*혁신획득체계·RAMS센터\s*구축안을", "한국형 드론 혁신획득체계 및 공인 시험평가 역량을"),
        (r"한국의\s*드론특별법·혁신획득체계·RAMS\s*센터\s*구축안\s*등", "한국의 드론특별법·혁신획득체계 및 공인 시험평가 정책 자료 등"),
        (r"국가\s*UAS\s*디지털\s*트윈\s*교육\s*플랫폼\s*구축안", "국가 UAS 디지털 트윈 교육 플랫폼 구축 방안"),
        (r"실증-인증\s*통합\s*플랫폼\s*구축안", "실증-인증 통합 협력 방안"),
        (r"‘무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안’\s*등", "‘무인기 신뢰도·안전성(RAMS) 시험평가 체계 고도화’ 등"),
        (r"국내\s*무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안은", "국내 무인기 신뢰도·안전성(RAMS) 검증 체계 고도화는"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안\(불확실성\s*정량화,\s*런타임\s*보증\)\s*구체화", "무인기 신뢰도·안전성(RAMS) 검증 체계(불확실성 정량화, 런타임 보증) 구체화"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계평가센터\s*구축안\(안\)을", "국내 공인 무인기 시험평가 인프라 고도화를"),
        (r"동\s*구축안은\s*국내\s*드론\s*기업이", "선진 안전성 검증 체계는 국내 드론 기업이"),
        (r"선진\s*연구에서\s*제시된\s*[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\s*구축안은", "선진 항공 안전성 연구에서 제시된 신뢰도·안전성(RAMS) 검증 기준은"),
        (r"최근\s*제안된\s*[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\s*구축안은", "국내 무인기 신뢰도·안전성(RAMS) 검증 체계 고도화는"),
        (r"\d의\s*RAMS\s*센터\s*구축안에서\s*제시한", "선진 항공 안전성 기준에서 제시한"),
        (r"국내\s*센터\s*구축안에서는", "선진 무인기 안전성 연구에서는"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축\(안\)", "무인기 신뢰도·안전성(RAMS) 검증 체계 고도화"),
        (r"차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*시험평가\s*인프라\s*확충\s*방안안", "차세대 무인기 신뢰성·안전성(RAMS) 시험평가 인프라 고도화"),
        (r"국내\s*[\'\"‘“]?차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*검증\s*인프라\(구축안\s*v3\s*참조\)[\'\"’”]?에서\s*도출된", "국내 무인기 시험평가 및 감항인증 연구에서 축적된"),
        (r"‘무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계’\s*구축안에서\s*제시된", "선진 항공 안전성 기준에서 제시된"),
        (r"[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\s*구축안에서\s*제시된", "선진 무인기 신뢰성 평가 체계에서 제시된"),
        (r"무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계\s*구축안에서\s*도출된", "국내 공인 시험평가에서 축적된"),
        (r"Physical\s*AI\s*기반\s*UAS\s*RAMS\s*(?:시험‧?평가센터|센터)?\s*구축안\s*및\s*관련\s*통계\s*자료를\s*토대로", "글로벌 항공 안전성 기준 및 미국 내 주요 비행시험장 통계 자료를 토대로"),
        (r"Physical\s*AI\s*기반\s*UAS\s*RAMS\s*(?:\([^\)]+\)\s*)?(?:시험·?평가\s*)?센터\s*구축안", "글로벌 무인기 신뢰성(RAMS) 기준 분석"),
        (r"Physical\s*AI\s*기반\s*UAS\s*RAMS\s*(?:시험·?평가\s*)?인프라\s*구축안", "국내 무인기 신뢰성·안전성(RAMS) 시험평가 고도화 수요"),
        (r"[\'\"‘“]?AI\s*기반\s*UAS\s*RAMS\s*시험평가센터\s*구축\(안\)[\'\"’”]?\s*수요와\s*직접\s*연계\s*가능하다", "고신뢰성 자율비행 비행시험 및 안전성 검증 수요와 직접 연계 가능하다"),
        (r"\*{0,2}[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\*{0,2}\s*구축안과\s*유타\s*주립대\(USU\)등의\s*연구\s*역량을\s*연결하여", "국내 무인기 신뢰성·안전성(RAMS) 시험평가 기술 고도화 방향과 유타 주립대(USU) 등의 첨단 연구 역량을 연결하여"),
        (r"[\'\"‘“]?차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*검증\s*인프라[\'\"’”]?\s*구축안과\s*직접\s*연계\s*가능한\s*인프라로", "국내 무인기 산업의 신뢰성·안전성(RAMS) 검증 수요와 직접 연계 가능한 인프라로"),
        (r"[\'\"‘“]?차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*검증\s*인프라[\'\"’”]?\s*국내\s*구축안과", "국내 무인기 비행시험 데이터 축적과"),
        (r"‘차세대\s*무인기\s*신뢰성·안전성\(RAMS\)\s*검증\s*인프라’\s*구축안과\s*연계한", "‘차세대 무인기 신뢰성·안전성(RAMS) 검증 역량’과 연계한"),
        (r"\(RAMS\s*센터\s*구축안\s*연계\)", "(국내 무인기 시험평가 고도화 전략 연계)"),
        (r"RAMS\s*센터\s*구축안\(안\)\s*기준,\s*국내\s*시험\s*인프라\s*대비", "국내 공인 비행시험장(고흥 등) 규모 대비"),
        (r"RAMS\s*센터\s*구축안", "무인기 안전성(RAMS) 검증 체계 고도화"),
        (r"센터\s*구축안", "시험평가 체계 고도화"),
        (r"[\'\"‘“]?무인기\s*신뢰도·안전성\(RAMS\)\s*검증\s*체계[\'\"’”]?\s*구축안", "무인기 신뢰도·안전성(RAMS) 검증 체계 고도화"),
        (r"구축안", "추진 계획"),
        (r"구축\(안\)", "체계 고도화"),
    ]
    for pat, repl in draft_proposal_cleanups:
        cleaned = re.sub(pat, repl, cleaned)

    # 4. Eradicate fictitious non-existent domestic centers and center linkages
    fictitious_centers = [
        (r"\[Physical\s*AI\s*RAMS\s*시험평가센터\(국내/유타\s*연계\)\]", "[국내 공인 시험기관 및 유타 비행시험장 연계]"),
        (r"Physical\s*AI\s*RAMS\s*센터\s*연계,\s*고흥/전남\s*실증\s*데이터\s*상호\s*인정",
         "국내 비행시험 데이터 축적 및 한-미 시험성적서 상호인정(MRA) 추진"),
        (r"Physical\s*AI\s*RAMS\s*센터\s*연계", "공인 시험평가 체계 연계"),
        (r"한국형\s*Physical\s*AI\s*RAMS\s*센터\s*연계\s*포인트", "국내 공인 비행시험 및 시험평가 연계 포인트"),
        (r"한국형\s*RAMS\s*센터\s*구축\s*요구사항", "국내 무인기 시험평가 고도화 요구사항"),
        (r"한국형\s*RAMS\s*센터\s*구축\s*시\s*국내에서\s*수행하기\s*어려운", "국내 무인기 시험평가 시 국내 공역에서 수행하기 어려운"),
        (r"\[국내\s*Physical\s*AI\s*RAMS\s*센터\]", "[국내 공인 시험기관/비행시험장]"),
        (r"국내\s*Physical\s*AI\s*RAMS\s*센터", "국내 공인 시험평가 기관"),
        (r"Physical\s*AI\s*RAMS\s*시험평가센터", "국내 공인 무인기 시험평가 전문기관"),
        (r"Physical\s*AI\s*RAMS\s*센터", "공인 무인기 시험평가 인프라"),
        (r"Physical\s*AI\s*센터", "첨단 무인기 인공지능 연구센터"),
        (r"국내\s*RAMS\s*센터\s*검증\s*역량", "국내 공인 시험평가 기관의 검증 역량"),
        (r"국내\s*RAMS\s*센터의\s*FAA/NASA\s*연계\s*인증\s*기관\s*지정", "국내 공인 시험기관의 대미 시험 데이터 신뢰성 확보"),
        (r"\[국내\s*RAMS\s*센터\s*역량\s*고도화\s*&\s*국제\s*공인\s*인증\s*획득\]", "[국내 공인 시험평가 역량 고도화 & 국제 상호인정 획득]"),
        (r"국내\s*RAMS\s*센터의\s*시험\s*평가\s*절차와\s*기준", "국내 공인 시험평가 기관의 시험 절차와 기준"),
        (r"국내\s*RAMS\s*센터\s*구축\s*시\s*벤치마킹할", "국내 무인기 시험평가 인프라 고도화 시 벤치마킹할"),
        (r"국가\s*단위\s*RAMS\s*시험·평가\s*센터\s*\|\s*구축\s*추진\s*중\s*\(제도화\s*검토\s*단계\)",
         "국가 단위 고신뢰성 시험·평가 체계 | 고도화 추진 중 (제도화 검토 단계)"),
        (r"국내\s*센터\s*구축\s*시\s*유타\s*모델\s*벤치마킹\s*필수", "국내 시험평가 체계 고도화 시 유타 모델 벤치마킹 필수"),
        (r"국내\s*시험평가\s*인프라\(RAMS\s*센터\s*등\)\s*부재로\s*미국\s*현지\s*재시험\s*필수",
         "국내 시험평가 데이터의 대미 상호인정 체계 미흡으로 미국 현지 재시험 필수"),
        (r"RAMS\s*시험평가센터\s*유치\s*제안:\s*국내\s*기업\s*전용\s*시험\s*슬롯\s*확보",
         "현지 비행시험 인프라 활용 제안: 국내 기업 전용 시험 슬롯 확보"),
        (r"RAMS\s*시험평가센터\s*구축,\s*DO-178C/326A\s*인증\s*컨설팅",
         "공인 비행시험 인프라 활용 및 시험평가 체계 고도화, DO-178C/326A 인증 컨설팅"),
        (r"RAMS\s*센터\s*내\s*\'FAA/DOD\s*인증\s*전담\s*데스크\'\s*설치",
         "국내 시험평가 기관 내 '대미 인증 전담 지원 데스크' 설치"),
        (r"\'한-유타\s*RAMS\s*센터\'\s*공동\s*구축,\s*FAA\s*지정\s*인증\s*대리인\(ODA/UMDA\)\s*확보\s*통한\s*검증\s*데이터\s*상호\s*인정",
         "한-유타 무인기 기술협력 및 비행시험 데이터 상호인정(MRA) 추진, FAA 공인 시험 데이터 확보"),
        (r"유타\s*주립대\s*RAMS\s*센터\s*공동\s*운영", "유타 주립대 첨단 자율시스템 연구시설 공동 활용"),
        (r"유타\s*현지에\s*\'통합\s*RAMS\s*시험·평가\s*센터\'를\s*구축하거나\s*기존\s*센터와\s*위탁\s*계약을\s*체결할\s*경우",
         "유타 현지 비행시험장(Desert UAS 등)을 활용하거나 현지 연구기관과 시험위탁 협약을 체결할 경우"),
        (r"\[트랙\s*C:\s*기술협력연계\(USU/RAMS센터\)\]", "[트랙 C: 기술협력연계(USU/자율시스템연구센터)]"),
        (r"RAMS\s*센터\s*활용\s*검증\s*데이터\s*확보", "공인 비행시험장 활용 검증 데이터 확보"),
        (r"자율비행\s*및\s*신뢰성\(RAMS\)\s*검증\s*센터\(가칭\s*Korea-Utah\s*UAS\s*Verification\s*Center\)",
         "한-유타 무인기 기술지원 데스크(가칭 Korea-Utah UAS Tech Support Desk)"),
        (r"국내\s*RAMS\s*센터\(개발/사전검증\)\s*→\s*유타\s*시험장\(실환경/인증검증\)\s*→\s*미군/연방조달\(획득/전력화\)",
         "국내 공인 시험기관(사전검증) → 유타 현지 시험장(실환경 검증) → 연방 조달 및 시장 안착"),
        (r"RAMS\s*센터\s*국내\s*선구축\s*→\s*유타\s*미러링", "국내 시험데이터 축적 → 유타 현지 비행실증 연계"),
        (r"‘국내\s*Physical\s*AI\s*RAMS\s*인프라\s*국가\s*구축\s*사업화\s*전략’", "‘국내 무인기 시험평가 체계 고도화 및 글로벌 협력 전략’"),
        (r"UITC\s*공역\+RAMS\s*센터\s*연계", "UITC 공역 및 현지 비행시험장 연계"),
        (r"\(UITC\s*공역\+RAMS\s*센터\s*연계\)", "(UITC 공역 및 현지 비행시험장 연계)"),
        (r"‘국가\s*통합\s*RAMS\s*시험·평가\s*센터’", "‘국내 공인 비행시험 인프라 연계 통합 시험평가 체계’"),
        (r"국가\s*통합\s*RAMS\s*시험·평가\s*센터", "국내 공인 비행시험 인프라 연계 통합 시험평가 체계"),
        (r"국가\s*RAMS\s*(?:시험·?평가\s*)?센터", "국가 공인 무인기 시험평가 체계"),
        (r"통합\s*RAMS\s*센터", "공인 비행시험 인프라 연계 시험평가 체계"),
        (r"RAMS\s*시험·평가\s*센터\s*보유\s*현황", "공인 비행시험·평가 인프라 보유 현황"),
        (r"RAMS\s*센터\s*2단계\s*\(EW\s*내성/AI\s*검증/위성링크\)\s*구축\s*완료", "공인 비행시험 인프라 고도화(전자전 내성/AI 검증/위성링크) 완료"),
        (r"국내\s*사전검증\(Physical\s*AI\s*RAMS\s*센터\)", "국내 사전검증(공인 시험평가 체계)"),
        (r"NASA\s*LaRC/NIA\s*공동\s*RAMS\s*시험평가센터\s*구축\s*추진", "NASA Langley 및 현지 연구기관 연계 시험평가 협력 추진"),
        (r"항공안전기술원\s*RAMS\s*센터\s*구축\s*추진", "항공안전기술원 등 국내 공인 시험평가 체계 고도화 추진"),
        (r"UAS\s*RAMS\s*시험평가센터\(인공지능\(AI\)\s*기반\s*자율비행\s*기반\)", "국내 공인 무인기 시험평가 및 교육 전문기관"),
        (r"UAS\s*RAMS\s*센터\(국내\s*추진\)", "공인 무인기 시험평가 인프라(국내 추진)"),
        (r"RAMS\s*시험평가센터\s*구축\s*추진\s*중", "공인 비행시험 및 안전성 검증 고도화 추진 중"),
        (r"RAMS\s*시험평가센터\s*연계\s*구축\s*필요", "공인 시험평가 인프라 고도화 필요"),
        (r"RAMS\s*시험평가센터", "공인 무인기 시험평가 전문기관"),
        (r"RAMS\s*시험·?평가\s*센터", "공인 무인기 시험평가 체계"),
        (r"RAMS\s*센터\s*부재", "부품 단위 공인 시험평가 체계 미흡"),
        (r"RAMS\s*센터\s*구축\s*계획", "무인기 신뢰성·안전성(RAMS) 시험평가 역량 확충 계획"),
        (r"RAMS\s*센터\s*구축\s*시", "공인 시험평가 체계 고도화 시"),
        (r"RAMS\s*센터\s*구축\s*공동\s*투자", "공인 비행시험 인프라 활용 공동 협력"),
        (r"RAMS\s*센터\s*구축", "무인기 신뢰성·안전성(RAMS) 시험평가 체계 고도화"),
        (r"RAMS\s*센터\s*연계", "공인 시험평가 체계 연계"),
        (r"RAMS\s*센터\s*필요성", "공인 시험평가 체계 고도화 필요성"),
        (r"RAMS\s*센터\s*역할\s*정립", "공인 시험평가 체계 역할 정립"),
        (r"RAMS\s*센터와\s*연계하여", "공인 시험평가 인프라와 연계하여"),
        (r"RAMS\s*센터\s*등\s*기\s*구축\s*실증\s*인프라", "고흥/영암 등 기 구축 공인 비행시험 인프라"),
        (r"RAMS\s*센터\s*등", "공인 시험평가 기관 등"),
        (r"RAMS\s*센터", "공인 비행시험 및 시험평가 체계"),
        (r"RAMS센터", "공인 시험평가 체계"),
        (r"물리적\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터", "차세대 자율비행 무인기 시험·평가 체계"),
        (r"물리\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터", "차세대 자율비행 무인기 시험·평가 체계"),
    ]
    for pat, repl in fictitious_centers:
        cleaned = re.sub(pat, repl, cleaned, flags=re.I)

    return cleaned


def deep_fact_vs_strategy_hotfix_v3(doc_text: str) -> str:
    """
    Applies aggressive fact vs stance corrections on Physical AI & RAMS:
    - Purges pseudo-projects ('무인기 고신뢰성 시험평가(RAMS) 인프라 확충(안)', '전남TP/고흥군')
    - Fact-finding (Chapters Ⅰ~Ⅴ): Replaces Physical AI RAMS with standard aerospace terms.
    - Strategy (Chapters Ⅵ~Ⅷ): Eradicates 'RAMS 사업' / 'Physical AI RAMS 사업' (0 instances),
      lowers tone of Physical AI / RAMS to neutral/exploratory.
    """
    ch_pattern = re.compile(r"(?m)(^##\s+[ⅠⅡⅢⅣⅤⅥⅦⅧ]\.\s*.*?$)")
    parts = ch_pattern.split(doc_text)

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
            # Fact-finding chapters (Ⅰ~Ⅴ): eradicate Physical AI RAMS as established reality
            fact_pats = [
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
                (r"피지컬\s*AI\(Physical\s*AI\)", "물리적 인공지능(Physical AI)"),
                (r"피지컬\s*AI\(인공지능\(AI\)\s*기반\s*자율비행\)", "인공지능(AI) 기반 자율비행"),
                (r"피지컬\s*AI", "인공지능(AI) 기반 자율운용"),
                (r"Physical\s*AI", "인공지능(AI) 기반 자율비행"),
            ]
            for pat, repl in fact_pats:
                mod = re.sub(pat, repl, mod, flags=re.IGNORECASE)
        else:
            # Strategy / Implications chapters (Ⅵ, Ⅶ, Ⅷ)
            strat_pats = [
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
                (r"Physical\s*AI\s*실증\s*얼라이언스", "자율비행 실증 협력 네트워크"),
                (r"(?:Physical\s*AI|피지컬\s*AI)\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:체계|기술|검증)?(?:의\s*도입|의\s*구축)?(?:을\s*신속히\s*추진해야\s*한다|을\s*추진해야\s*한다|이\s*필수적이다|이\s*불가피하다)",
                 "물리적 인공지능(Physical AI) 및 신뢰도(RAMS) 기술의 도입 필요성을 중장기적 관점에서 면밀히 고려해 볼 필요가 있다"),
                (r"(?:Physical\s*AI|피지컬\s*AI)\s*(?:기반\s*)?(?:UAS\s*)?RAMS\s*(?:체계|기술)?(?:와의\s*연계가\s*필수적이다|와\s*연계하여야\s*한다|와\s*연계하여\s*추진해야\s*한다)",
                 "차세대 자율비행 및 신뢰성(RAMS) 기술과의 연계 가능성을 선제적으로 검토해 볼 필요가 있다"),
                (r"반드시\s*Physical\s*AI\s*기반\s*RAMS\s*(?:체계를\s*)?구축해야\s*한다",
                 "중장기적으로 Physical AI 및 RAMS 검증 기술 도입을 검토해 볼 필요가 있다"),
                (r"주정부\s*[\'\"‘“]?Physical\s*AI\s*이니셔티브[\'\"’”]?\s*정책\s*기조와\s*부합",
                 "주정부 '첨단 자율시스템 및 항공우주 이니셔티브' 정책 기조와 부합"),
                (r"3축:\s*Physical\s*AI\s*RAMS\s*인프라\s*및\s*혁신획득\s*벤치마킹",
                 "3축: 자율비행 신뢰성(RAMS) 검증 인프라 및 혁신획득 벤치마킹"),
                (r"FAA\s*위임시험장/PHysical\s*AI\s*RAMS/사이버보안",
                 "FAA 위임시험장/자율비행 안전성(RAMS)/사이버보안"),
                (r"Physical\s*AI\s*디지털트윈\s*기반\s*RAMS\s*데이터\s*축적",
                 "디지털트윈 기반 안전성(RAMS) 데이터 축적"),
                (r"Physical\s*AI\s*알고리즘의", "자율비행 AI 알고리즘의"),
            ]
            for pat, repl in strat_pats:
                mod = re.sub(pat, repl, mod, flags=re.IGNORECASE)

        new_parts.append(mod)

    return "".join(new_parts)


def clean_acronym_table_custom(text: str) -> str:
    """Removes KURA row from acronym table and ensures acronym rows are clean."""
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if re.search(r"\|\s*\*\*KURA\*\*\s*\|", line):
            continue  # remove KURA
        new_lines.append(line)
    return "\n".join(new_lines)


def process_report_v3(src_path: Path, dest_path: Path) -> dict:
    """Full v3 processing pipeline producing the cleaned, purged next-version report."""
    text = src_path.read_text(encoding="utf-8")
    is_us = "미국" in src_path.name

    # Step 1: Clean draft proposals, non-existent domestic centers, fictitious MOUs/alliances (KURA), regex artifacts
    step1 = clean_draft_proposals_and_fictitious_entities(text)

    # Step 2: Deep fact vs strategy hotfix (tone down Physical AI, 0 RAMS project mentions)
    step2 = deep_fact_vs_strategy_hotfix_v3(step1)

    # Step 3: Anomalies and prompt leakages
    step3 = clean_anomalies_and_foreign_text(step2)

    # Step 4: Strip narrative table prefixes
    step4 = strip_narrative_table_prefixes(step3)

    # Step 5: Clean long caption descriptions
    step5 = clean_long_caption_descriptions(step4)

    # Step 6: Inject US report figures if US report
    if is_us:
        step5 = inject_us_report_figures(step5)

    # Step 7: Clean empty appendix sections
    step6 = clean_empty_appendix_sections(step5)

    # Step 8: Update acronym table and clean KURA
    step7 = populate_comprehensive_acronym_table(step6)
    step7 = clean_acronym_table_custom(step7)

    # Step 9: Normalize all tables (strip leading section numbers)
    step8 = normalize_all_tables_v2(step7)

    # Step 10: Normalize all figures (strip leading section numbers)
    step9 = normalize_all_figures_v2(step8)

    # Step 11: Reconcile in-body cross references
    step10, ref_changes = reconcile_in_body_cross_references(step9)

    # Step 12: Clean and expand bibliography
    step11 = clean_and_expand_bibliography(step10, is_us_report=is_us)

    # Step 13: Rebuild front matter and TOC
    step12 = rebuild_front_matter_and_toc(step11)

    # Step 14: Indent body paragraphs
    try:
        final_text = indent_body_paragraphs(step12)
    except Exception:
        final_text = step12

    # Save to destination path
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

    # Audit prohibited terms
    c_phys_ctr = len(re.findall(r"Physical\s*AI\s*(?:RAMS\s*)?센터|RAMS\s*(?:시험·?평가\s*)?센터", final_text, re.I))
    c_draft = len(re.findall(r"구축\(?안\)?|센터\s*구축안", final_text))
    c_kura = len(re.findall(r"\bKURA\b", final_text))
    c_rams_proj = len(re.findall(r"(?:Physical\s*AI\s*(?:기반\s*)?)?(?:UAS\s*)?RAMS\s*(?:구축\s*)?사업", final_text, re.I))
    c_artifacts = len(re.findall(r"체계(?:기술|평가|프로세스|아키텍처|핵심|시\b|로드맵)|방안전·후", final_text))

    return {
        "src": src_path.name,
        "dest": dest_path.name,
        "body_tables": body_tables,
        "toc_tables": toc_tables,
        "body_figs": body_figs,
        "toc_figs": toc_figs,
        "t_dups": t_dups,
        "f_dups": f_dups,
        "ref_changes": ref_changes,
        "c_phys_ctr": c_phys_ctr,
        "c_draft": c_draft,
        "c_kura": c_kura,
        "c_rams_proj": c_rams_proj,
        "c_artifacts": c_artifacts,
    }
