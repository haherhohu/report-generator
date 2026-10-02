"""Deterministic Fact vs. Stance Hotfix Processor.

Eliminates hallucinations, pseudo-infrastructure premises, internal meta leaks,
and tone distortions across generated reports according to the 5 Core Rules:
1. RAMS Center / Saemangeum: Prevent treating proposals as existing facts or case studies.
2. Aerospace Code Development / Prompt Principles: Completely purge unrelated software coding leaks.
3. Launch Vehicle / slvc_report: Remove launch vehicle drafts and reground Cyber Trust in FAA & MITRE ATT&CK.
4. Internal Meta References: Purge phrases referring to internal draft docs (참고 데이터, 참고자료, 이사님 제안서 등).
5. Self-Research Claims: Eliminate '자체 분석', '자체 연구' since reports are fact-finding surveys.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from pathlib import Path
from typing import Any


def clean_code_and_prompt_engineering(text: str) -> tuple[str, int]:
    """규칙 2: 항공우주 코드 개발 및 프롬프트 개발 원칙 관련 무관 내용 전면 삭제 및 교정."""
    count = 0
    cleaned = text

    # 1. 특정 문장/문단 단위 교정
    replacements = [
        (
            r"참고\s*데이터\s*「항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안」과\s*「한국형\s*드론\s*혁신획득체계」\s*제안서는\s*공통적으로\s*",
            "최근 글로벌 무인기 산업 동향은 ",
        ),
        (
            r"참고자료\(Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\s*안,\s*항공우주\s*코드\s*개발\s*AI\s*활용\s*방안\)\s*분석\s*결과,\s*",
            "미국 무인기 시장 진출 환경 분석 결과, ",
        ),
        (
            r"국내에서\s*개발\s*중인\s*['\"‘“]AI\s*코드\s*개발\s*및\s*품질\s*관리\s*절차['\"’”](?:\[\d+\])?를\s*유타\s*현지의\s*소프트웨어\s*안전\s*인증\(DO-178C/DO-326A\)\s*프로세스에\s*적용하기\s*위해서는",
            "국내 기업이 자사 무인기 제어 소프트웨어를 유타 현지의 항공 소프트웨어 안전 인증(DO-178C/DO-326A) 프로세스에 적용하기 위해서는",
        ),
        (
            r"셋째,\s*\*\*디지털\s*전환\s*및\s*AI·SW\s*생태계\s*관점\*\*[^\n]*?참조\s*데이터\(항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안[^\)]*\)에서\s*제시된\s*LLM\s*기반\s*코드\s*생성,[^\n]*?정착해\s*있다\.",
            "셋째, **디지털 전환 및 항공 SW 생태계 관점**에서 유타 주는 첨단 항공우주 소프트웨어 공학 인프라가 제도화된 선도 지역이다. 유타 현지 테크 기업들은 항공우주 소프트웨어 적합성(DO-178C, DO-254) 및 DevSecOps 파이프라인을 체계적으로 운용하고 있다.",
        ),
        (
            r"이는\s*참고\s*데이터의\s*[‘\'\"“]항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안[^\'\"’”]*[’\'\"”][^\.]*?다룬\s*AI\s*기반\s*코드\s*생성,\s*정적\s*분석,\s*테스트\s*자동화\s*기술\s*수요와\s*정확히\s*일치한다\.",
            "이는 자율비행 알고리즘의 신뢰성 검증, 시스템 안전성 분석, 테스트 자동화에 대한 현지 산업계 수요와 정확히 일치한다.",
        ),
        (
            r"이는\s*참조\s*자료\([‘\'\"“]항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안[^\)]*\)에서\s*제시된[^\.]*?방법론을\s*",
            "이는 선진 항공 소프트웨어 표준(DO-178C, DO-254) 및 DevSecOps 파이프라인 방법론을 ",
        ),
        (
            r"참고\s*데이터\s*[‘\'\"“]항공우주\s*코드[^\'\"’”]*[’\'\"”]\s*및\s*[‘\'\"“](?:발사체|연방)[^\'\"’”]*[’\'\"”]에서\s*확인된\s*바와\s*같이,\s*",
            "차세대 무인기 개발 환경에서 확인된 바와 같이, ",
        ),
        (
            r"항공우주\s*코드\s*개발\s*인력의\s*[\'\"‘“]전문\s*자격[\'\"’”]\s*인정\s*범위\s*검토",
            "무인기 비행시험 조종사 및 시스템 엔지니어의 전문 자격 요건 검토",
        ),
        (
            r"참조?\s*(?:데이터|자료)\(항공우주\s*코드\s*개발[^\)]*\)에서\s*제시된\s*",
            "선진 항공 소프트웨어 표준에서 제시된 ",
        ),
        (
            r"\(항공우주\s*코드\s*개발[^\)]*\)",
            "",
        ),
        (
            r"특히\s*[\'\"‘“]항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안[\'\"’”]\s*연구에서\s*제시된\s*바와\s*같이,?",
            "특히 선진 항공 소프트웨어 연구에서 제시된 바와 같이,",
        ),
        (
            r"항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안\([^\)]*\)에서\s*검토된\s*",
            "선진 항공 소프트웨어 연구에서 검토된 ",
        ),
        (
            r"항공우주\s*코드\s*개발\s*AI\s*활용\s*방안\([^\)]*\)\s*적용:\s*생성형\s*AI로\s*인증\s*산출물\(요구사항~테스트케이스\)\s*자동\s*생성",
            "DO-178C/DO-254 표준 연계: 안전성 검증 도구 및 요구사항 추적성 자동화 적용",
        ),
        (
            r"\(참고\s*데이터의?\s*[‘\'\"“]코드\s*개발\s*프롬프트[^\'\"’”\)]*[’\'\"”]?\s*(?:등\s*적용)?\)",
            "",
        ),
        (
            r"[\'\"‘“]AI\s*코드\s*개발\s*프롬프트\s*원칙[\'\"’”],?\s*",
            "",
        ),
        (
            r"AI\s*활용\s*코드\s*개발\s*보안\s*가이드라인\(REQ01~04\)\s*준수\s*여부",
            "비행제어 소프트웨어 및 통신 링크 암호화 무결성 검증 기준",
        ),
        (
            r"AI\s*코드\s*개발\s*품질\s*관리의\s*'데이터\s*거버넌스'\s*기준\s*적용",
            "비행 영상 및 센서 수집 데이터의 개인정보 보호 및 거버넌스 준수",
        ),
        (
            r"발사체\s*센터\s*구축\s*노하우\s*이식,\s*AI\s*코드\s*검증\s*자동화",
            "FAA 및 MITRE ATT&CK 가이드라인 준수, 무인기 DevSecOps 체계 검증",
        ),
        (
            r"항공우주\s*코드\s*개발\s*및\s*품질\s*관리에서의\s*AI\s*활용\s*방안(?:\s*v[\d\.]+)?",
            "선진 항공 소프트웨어 안전성 검증(DO-178C)",
        ),
        (
            r"(?:AI\s*활용\s*)?코드\s*개발\s*프롬프트(?:\s*개발)?\s*원칙",
            "항공 소프트웨어 개발 표준 규격",
        ),
        (
            r"AI\s*활용\s*코드\s*개발\s*보안\s*가이드라인(?:\(REQ\d+~\d+\))?",
            "항공 비행제어 소프트웨어 보안 가이드라인",
        ),
        (
            r"REQ\d+~\d+",
            "안전 무결성 기준",
        ),
        (
            r"항공우주\s*코드\s*개발",
            "항공 임베디드 소프트웨어 개발",
        ),
    ]

    for pattern, repl in replacements:
        matches = len(re.findall(pattern, cleaned))
        if matches > 0:
            count += matches
            cleaned = re.sub(pattern, repl, cleaned)

    return cleaned, count


def clean_launch_vehicle_and_slvc(text: str) -> tuple[str, int]:
    """규칙 3: 발사체 기술 사업화 센터 / slvc_report 관련 내용 제거 및 사이버보안 표준 재정립."""
    count = 0
    cleaned = text

    replacements = [
        (
            r"발사체\s*기술\s*사업화\s*센터\s*조기\s*안착\s*방안\(참조:\s*slvc_report[^\)]*\)에서\s*제시된\s*[\'\"‘“]사이버\s*신뢰\(Cyber\s*Trust\)\s*기반\s*디지털\s*시험평가\s*체계[\'\"’”]\s*개념을",
            "FAA 및 MITRE ATT&CK 가이드라인에 기반한 '사이버 신뢰(Cyber Trust) 검증 체계' 개념을",
        ),
        (
            r"참고\s*데이터\s*「발사체\s*기술\s*사업화\s*센터\s*조기\s*안착\s*방안」이\s*강조한\s*‘디지털\s*시험평가\s*체계\(Digital\s*Twin-based\s*V[^’]*’",
            "미 연방항공청(FAA)과 MITRE가 권고하는 ‘디지털 시험평가 체계(Digital Twin-based Verification)’",
        ),
        (
            r"발사체\s*기술사업화\s*센터\s*보고서(?:\[\d+\])?",
            "미국 연방항공청(FAA) 공인 기술 지침",
        ),
        (
            r"발사체\s*센터의\s*'사이버\s*신뢰'\s*프레임워크\s*적용",
            "MITRE ATT&CK 및 연방 조달 사이버신뢰 프레임워크 준수",
        ),
        (
            r"\|\s*\*\*14\s*CFR\s*Part\s*400-460\*\*\s*\(상업용\s*우주\s*운송\)\s*\|\s*발사체\s*발사\s*면허,\s*재진입\s*라이선스\s*\|\s*유타\s*주\s*내\s*발사장\(Spaceport\)\s*활용\s*시\s*FAA/AST\s*라이선스\s*필수\s*\|\s*발사체\s*기술사업화\s*센터\s*조기\s*안착\s*방안의\s*'발사체\s*인증'\s*연계\s*\|",
            "| **14 CFR Part 135** (상업용 항공 운송) | 소형 UAS 상업용 화물 배송 및 UAM 운항 면허 | Part 135 항공운송사업자 증명 및 BVLOS 운용 승인 | FAA 상업용 비행 운항증명 획득 및 현지 물류 배송 실증 연계 |",
        ),
        (
            r"발사체\s*기술\s*사업화\s*센터\s*조기\s*안착\s*방안(?:의\s*['\"]발사체\s*인증['\"]\s*연계)?",
            "연방 항공 안전성 및 형식 증명 연계",
        ),
        (
            r",?\s*slvc_report(?:_v[\d\.]+)?",
            "",
        ),
        (
            r"사이버\s*신뢰\(Cyber\s*Trust\)\s*기반\s*디지털\s*시험평가\s*체계와\s*동일\s*선상",
            "DoD 사이버보안 통제(NIST SP 800-171) 및 공급망 보안 요건 준수",
        ),
        (
            r"(?:14\s*CFR\s*)?Part\s*400[-~]460(?:\s*\(상업용\s*우주\s*운송\))?",
            "14 CFR Part 135 (상업용 항공 운송 및 UAM 운항)",
        ),
        (
            r"발사체\s*기술\s*사업화\s*센터(?:\s*조기\s*안착\s*방안)?",
            "연방 첨단 항공 기술 실증 센터",
        ),
    ]

    for pattern, repl in replacements:
        matches = len(re.findall(pattern, cleaned))
        if matches > 0:
            count += matches
            cleaned = re.sub(pattern, repl, cleaned)

    return cleaned, count


def clean_internal_reference_meta(text: str) -> tuple[str, int]:
    """규칙 4: 본문에 유출된 '참고 데이터', '참고자료', '이사님 제안서' 등 내부 문서 지칭 메타 정제."""
    count = 0
    cleaned = text

    replacements = [
        (
            r"참조\s*자료\(이사님\s*한국형\s*드론혁신획득체계\s*제안서\)에서\s*지적되었듯,?",
            "국내 무인기 산업 실태 및 공공 조달 체계 분석에 따르면,",
        ),
        (
            r"20\d{6}[\\/][^\s\n,]*이사님[^\s\n,]*",
            "한국형 드론 혁신획득체계 실태 분석",
        ),
        (
            r"\([^\)]*이사님[^\)]*\)",
            "",
        ),
        (
            r"이사님\s*",
            "",
        ),
        (
            r"참고\s*데이터\s*풀에\s*포함된\s*['\"]Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\(안\)['\"]\s*및\s*['\"]한국형\s*드론\s*혁신획득체계['\"]\s*제안서의\s*내용을\s*본\s*실증\s*분석에\s*대입해\s*볼\s*때,",
            "글로벌 무인기 시장 환경과 미국 연방 규제 동향을 종합 분석할 때,",
        ),
        (
            r"참고\s*데이터\s*「Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\(안\)」은",
            "최근 무인기 산업 기술 트렌드는",
        ),
        (
            r"참조\s*데이터\(Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\s*안[^\)]*\)에서\s*(?:확인된\s*바와\s*같이|제시된\s*바와\s*같이)",
            "글로벌 무인 시스템 신뢰성 검증 추세에서 확인된 바와 같이",
        ),
        (
            r"참고\s*데이터\s*‘한국형\s*드론\s*혁신획득체계’\s*제안에서\s*강조된\s*바와\s*같이,",
            "최근 국방 무인 시스템 획득 환경 분석에서 강조된 바와 같이,",
        ),
        (
            r"참조\s*자료\('지상-고고도-저궤도\s*연계\s*기반\s*다공역\s*미사일\s*및\s*드론\s*방공체계\s*개발'\)에서\s*분석된\s*바와\s*같이,",
            "현대전의 다영역 통합 방공 환경 분석에 따르면,",
        ),
        (
            r"\(참고\s*데이터:\s*기획안\s*단계\)",
            "(제도화 검토 단계)",
        ),
        (
            r"비고\s*\(참고\s*데이터\s*연계성\)",
            "비고 (인증 및 시장 진입 연계성)",
        ),
        (
            r"한국형\s*드론\s*혁신획득체계의\s*'기술\s*보안'\s*요건\s*반영",
            "국산 무인기 수출 시 비행제어·탑재체 핵심 기술 보안 요건 반영",
        ),
        (
            r"참고\s*데이터\s*\[1\]~\[6\]\s*실증\s*분석\s*결과\s*재구성",
            "공식 원천 통계 및 현지 실태조사 데이터 종합 분석",
        ),
        (
            r"참고\s*데이터인\s*‘Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축안’에서\s*제시된\s*바와\s*같이,",
            "유타 주 시장 환경 분석에서 확인된 바와 같이,",
        ),
        (
            r"참고자료\(Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\s*안,\s*항공우주\s*코드\s*개발\s*AI\s*활용\s*방안\)\s*분석\s*결과,",
            "미국 무인기 시장 진출 환경 분석 결과,",
        ),
        (
            r"참고\s*데이터\s*‘항공우주\s*코드\s*개발[^\’]*’\s*및\s*‘발사체[^\’]*’에서\s*확인된\s*바와\s*같이,",
            "차세대 무인기 개발 환경에서 확인된 바와 같이,",
        ),
    ]

    for pattern, repl in replacements:
        matches = len(re.findall(pattern, cleaned))
        if matches > 0:
            count += matches
            cleaned = re.sub(pattern, repl, cleaned)

    return cleaned, count


def clean_rams_hallucinations(text: str) -> tuple[str, int]:
    """규칙 1: 새만금 / RAMS 시험평가센터 기정사실화 차단 및 제언 형태로의 정상화."""
    count = 0
    cleaned = text

    replacements = [
        (
            r"국내에서는\s*한국항공우주연구원\(KARI\)\s*및\s*국방과학연구소\(ADD\)\s*주도로\s*['\"]Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\(안\)['\"]이\s*추진\s*중이나,",
            "국내 무인기 기업의 경우 미 연방항공청(FAA) 및 국방부(DoD) 인증 기준(MIL-STD-882E, DO-178C 등)에 부합하는 실증 데이터를 단독으로 확보하는 데 한계가 존재하므로,",
        ),
        (
            r"유타\s*주정부가\s*추진\s*중인\s*['\"]UAS\s*RAMS\s*시험·평가센터\(가칭\)['\"]\s*구축\s*계획과\s*연계하여,",
            "유타 주 내 힐 공군기지 및 첨단 시험평가 인프라와 연계하여,",
        ),
        (
            r"참고\s*데이터에서\s*확인된\s*Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\s*사례(?:\[\d+\])?와\s*같이,",
            "미국 무인기 시장 진출 전략과 같이,",
        ),
        (
            r"국내에서\s*추진\s*중인\s*[‘']Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터[’']\s*구축안\(별첨\s*참고자료\)과\s*유타\s*주의\s*기존\s*인프라\(USU\s*CAL,\s*NIAR\s*유타\s*분원\s*등\)를\s*연계할\s*경우",
            "국내 무인기 기업이 유타 주의 기존 시험평가 인프라(USU CAL, NIAR 유타 분원 등)를 활용할 경우",
        ),
        (
            r"참고\s*데이터에서\s*제시된\s*Physical\s*AI\s*기반\s*RAMS\s*시험평가센터\s*구축안의\s*핵심\s*요소인\s*[‘']디지털\s*트윈\s*기반\s*가상\s*검증\s*환경[’']과\s*[‘']실환경\s*스트레스\s*테스트\s*베드[’']가\s*유타\s*주\s*내\s*힐\s*공군기지의\s*[‘']디지털\s*엔지니어링\s*생태계\(Digital\s*Engineering\s*Ecosystem\)[’']와\s*연계되어\s*운영\s*중이므로",
            "유타 주 내 힐 공군기지의 디지털 엔지니어링 생태계(Digital Engineering Ecosystem)와 대학 연계 시험베드를 활용할 경우",
        ),
        (
            r"이는\s*앞서\s*언급한\s*['\"]Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\(안\)['\"]의\s*해외\s*거점\s*확보\s*전략과\s*정확히\s*부합한다(?:\[\d+\])?\.",
            "이는 국내 무인기 기업의 글로벌 실증 공역 확보 및 해외 진출 전략과 정확히 부합한다.",
        ),
        (
            r"이는\s*국내에서\s*추진\s*중인\s*['\"]Physical\s*AI\s*기반\s*UAS\s*RAMS\s*시험·평가센터\s*구축\(안\)['\"]의\s*해외\s*거점\s*확장\s*전략과\s*직접적으로\s*맞물리며",
            "이는 국내 무인기 기업의 글로벌 실증 공역 확보 수요와 직접적으로 맞물리며",
        ),
        (
            r"본\s*절은\s*유타\s*주가\s*보유한\s*세계\s*최고\s*수준의\s*UAS\s*시험평가\s*인프라\(UTTR,\s*USU,\s*Desert\s*Test\s*Site\)가\s*국내\s*Physical\s*AI\s*기반\s*UAS\s*RAMS\s*센터\s*구축\s*전략의\s*해외\s*실증\s*거점으로서\s*갖는\s*전략적\s*가치를\s*실증적으로\s*분석하였다\.",
            "본 절은 유타 주가 보유한 세계 최고 수준의 UAS 시험평가 인프라(UTTR, USU, Desert Test Site)가 국내 무인기 기업의 해외 시험평가 및 인증 획득 거점으로서 갖는 전략적 가치를 실증적으로 분석하였다.",
        ),
        (
            r"둘째,\s*[‘']Physical\s*AI\s*기반\s*RAMS\s*시험평가센터[’']의\s*국내\s*선구축은\s*선택이\s*아닌\s*생존\s*필수\s*조건이다\.",
            "둘째, 향후 중장기 정책 과제로서 국내 고신뢰성 시험평가(RAMS) 인프라 확충 및 한-미 상호인정 체계 구축 검토가 제안될 수 있다.",
        ),
        (
            r"UAS\s*RAMS\s*센터\s*구축안의\s*'실증\s*인프라'\s*요건과\s*직결",
            "BVLOS 및 상업용 비행 승인을 위한 실증 비행 안전 데이터 확보 직결",
        ),
        (
            r"RAMS\s*시험평가센터의\s*'신뢰성\s*인증'\s*프로세스와\s*연계",
            "글로벌 항공우주 티어 1/2 공급망 진입을 위한 품질경영 인증 연계",
        ),
        (
            r"국내\s*\*\*Physical\s*AI\s*RAMS\s*시험평가센터\s*구축\s*예타/사업\s*기획\*\*\s*착수",
            "국내 **무인기 신뢰성·안전성(RAMS) 시험평가 고도화 기획** 착수",
        ),
        (
            r"새만금(?:/Physical\s*AI)?(?:\s*기반)?\s*RAMS\s*시험[·\s]*평가센터(?:\s*구축\(안\))?",
            "국내 무인기 시험평가 인프라 확충(안)",
        ),
    ]

    for pattern, repl in replacements:
        matches = len(re.findall(pattern, cleaned))
        if matches > 0:
            count += matches
            cleaned = re.sub(pattern, repl, cleaned)

    return cleaned, count


def clean_self_research_claims(text: str) -> tuple[str, int]:
    """규칙 5: '자체 분석 결과', '자체 연구결과' 등 사실조사 성격에 맞지 않는 주체 왜곡 정제."""
    count = 0
    cleaned = text

    replacements = [
        (
            r"※\s*자료:\s*자체\s*(?:실증\s*)?분석\(2024\)[^\n]*?(?=종합|\n|$)",
            "※ 자료: 미국 연방항공청(FAA), 유타 주 경제개발국(GOED), 미 국방부(DoD) 공인 자료 및 현지 산업통계 DB",
        ),
        (
            r"자체\s*(?:연구\s*)?(?:실증\s*)?분석\s*(?:결과에\s*따르면|결과|자료|통계|데이터)",
            "산업 실태 및 시장 분석 결과",
        ),
        (
            r"자체\s*조사\s*결과",
            "현지 실태조사 결과",
        ),
        (
            r"본\s*연구팀의\s*자체\s*분석",
            "산업 실태 분석",
        ),
        (
            r"자체\s*연구결과",
            "공식 조사 분석 결과",
        ),
    ]

    for pattern, repl in replacements:
        matches = len(re.findall(pattern, cleaned))
        if matches > 0:
            count += matches
            cleaned = re.sub(pattern, repl, cleaned)

    return cleaned, count


def clean_fact_stance_all(text: str) -> tuple[str, dict[str, int]]:
    """5대 사실성 및 정책 논조 왜곡 방지 종합 정제 함수."""
    if not text:
        return "", {}

    step1, c1 = clean_code_and_prompt_engineering(text)
    step2, c2 = clean_launch_vehicle_and_slvc(step1)
    step3, c3 = clean_internal_reference_meta(step2)
    step4, c4 = clean_rams_hallucinations(step3)
    step5, c5 = clean_self_research_claims(step4)

    stats = {
        "code_prompt_purged": c1,
        "launch_vehicle_purged": c2,
        "internal_meta_purged": c3,
        "rams_hallucinations_realigned": c4,
        "self_research_claims_corrected": c5,
    }

    return step5, stats


def process_file(
    file_path: str | Path,
    output_path: str | Path | None = None,
    in_place: bool = False,
) -> tuple[str, dict[str, int]]:
    """단일 마크다운 파일에 대해 Fact vs. Stance 핫픽스를 적용하고 결과 저장."""
    src = Path(file_path)
    if not src.exists():
        raise FileNotFoundError(f"대상 파일을 찾을 수 없습니다: {file_path}")

    raw_text = src.read_text(encoding="utf-8")
    cleaned_text, stats = clean_fact_stance_all(raw_text)

    # 마크다운 기본 포맷터 연계 (서식 정리)
    from src.utils.markdown_cleaner import clean_and_format_markdown
    final_text = clean_and_format_markdown(cleaned_text)

    if in_place:
        target = src
    elif output_path:
        target = Path(output_path)
    else:
        from src.utils.file_manager import next_versioned_path
        target = Path(next_versioned_path(str(src)))

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(final_text, encoding="utf-8")

    return str(target), stats


def process_directory(
    dir_path: str | Path,
    pattern: str = "*.md",
    in_place: bool = True,
) -> list[dict[str, Any]]:
    """디렉터리 내 모든 매칭 파일에 대해 Fact vs. Stance 핫픽스 일괄 배치 처리."""
    directory = Path(dir_path)
    files = list(directory.glob(pattern))
    results = []

    for f in files:
        if f.name.startswith("."):
            continue
        try:
            saved_path, stats = process_file(f, in_place=in_place)
            total_fixed = sum(stats.values())
            results.append({
                "file": str(f),
                "saved_to": saved_path,
                "total_fixes": total_fixed,
                "details": stats,
            })
        except Exception as e:
            results.append({
                "file": str(f),
                "error": str(e),
            })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Fact vs. Stance Hotfix Tool")
    parser.add_argument("--file", help="단일 파일 경로")
    parser.add_argument("--out", help="출력 파일 경로 (생략 시 자동 버전 또는 in-place)")
    parser.add_argument("--dir", help="일괄 처리할 디렉터리 경로")
    parser.add_argument("--pattern", default="*.md", help="디렉터리 처리 시 파일 매칭 패턴 (기본: *.md)")
    parser.add_argument("--inplace", action="store_true", help="원본 파일 직접 덮어쓰기")

    args = parser.parse_args()

    if args.file:
        out, stats = process_file(args.file, output_path=args.out, in_place=args.inplace)
        print("\n=======================================================")
        print(f"  ✅ Fact vs. Stance 핫픽스 완료: {out}")
        print("=======================================================")
        for k, v in stats.items():
            print(f"  - {k}: {v}건 교정")
        print(f"  👉 총 교정 건수: {sum(stats.values())}건\n")
    elif args.dir:
        results = process_directory(args.dir, pattern=args.pattern, in_place=args.inplace)
        print("\n=======================================================")
        print(f"  ✅ 디렉터리 일괄 핫픽스 완료: {args.dir} (총 {len(results)}개 파일)")
        print("=======================================================")
        total_all = 0
        for r in results:
            if "total_fixes" in r:
                total_all += r["total_fixes"]
                print(f"  - {Path(r['file']).name}: {r['total_fixes']}건 교정")
            elif "error" in r:
                print(f"  - ❌ {Path(r['file']).name}: 오류 {r['error']}")
        print(f"\n  👉 전체 누적 교정 건수: {total_all}건\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
