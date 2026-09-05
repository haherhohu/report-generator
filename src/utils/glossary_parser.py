"""Extraction tools for acronyms, terms, and citations from generated markdown texts."""
from __future__ import annotations

import re

# 자주 등장하는 표준 기술/정책 약어 사전
KNOWN_ACRONYMS: dict[str, tuple[str, str]] = {
    "UAV": ("Unmanned Aerial Vehicle", "무인항공기"),
    "UAS": ("Unmanned Aircraft System", "무인항공시스템"),
    "C2": ("Command and Control", "지휘통제 및 원격제어 통신"),
    "TRL": ("Technology Readiness Level", "기술성숙도 (1~9단계)"),
    "CAGR": ("Compound Annual Growth Rate", "연평균 복합 성장률"),
    "FAA": ("Federal Aviation Administration", "미국 연방항공청"),
    "BVLOS": ("Beyond Visual Line of Sight", "가시권 밖 비행"),
    "GCS": ("Ground Control Station", "지상통제소"),
    "AI": ("Artificial Intelligence", "인공지능"),
    "ML": ("Machine Learning", "머신러닝/기계학습"),
    "R&D": ("Research and Development", "연구개발"),
    "OEM": ("Original Equipment Manufacturer", "주문자 상표 부착 생산"),
    "IP": ("Intellectual Property", "지식재산권/원천특허"),
    "K-UAS": ("Korea Unmanned Aircraft System", "한국형 무인항공시스템"),
    "ICAO": ("International Civil Aviation Organization", "국제민간항공기구"),
    "EASA": ("European Union Aviation Safety Agency", "유럽 항공안전청"),
    "M&A": ("Mergers and Acquisitions", "기업 인수합병"),
    "WBS": ("Work Breakdown Structure", "작업 분류 체계"),
    "API": ("Application Programming Interface", "애플리케이션 프로그래밍 인터페이스"),
    "NTN": ("Non-Terrestrial Network", "비지상 통신 네트워크 (위성통신 연계)"),
    "GEO": ("Geostationary Earth Orbit", "정지궤도 위성"),
    "LEO": ("Low Earth Orbit", "저궤도 위성"),
}


def extract_acronyms_from_markdown(text: str) -> list[dict[str, str]]:
    """본문에서 2글자 이상의 영문 약어(Acronym)를 감지하고 정의 목록을 구성."""
    if not text:
        return []

    # 1. 괄호 병기 패턴 감지 (예: 인공지능(AI), Unmanned Aerial Vehicle (UAV), 지휘통제(C2))
    paren_pattern = re.compile(r"([가-힣A-Za-z\s]+)\(([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\)")
    detected_defs: dict[str, str] = {}
    for m in paren_pattern.finditer(text):
        full_term = m.group(1).strip()
        acronym = m.group(2).strip()
        if len(full_term) < 40 and acronym not in detected_defs:
            detected_defs[acronym] = full_term

    # 2. 대문자 시작 약어 단어 탐색 (예: UAV, C2, TRL, CAGR)
    token_pattern = re.compile(r"\b([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\b")
    found_acronyms = set(token_pattern.findall(text))

    results: list[dict[str, str]] = []
    for acr in sorted(found_acronyms):
        # 무시할 일반 단어 필터링
        if acr in {"THE", "AND", "FOR", "WITH", "FROM", "PAGE", "NOTE", "STEP", "CASE", "PART"}:
            continue

        if acr in KNOWN_ACRONYMS:
            full_eng, def_kor = KNOWN_ACRONYMS[acr]
            results.append({
                "acronym": acr,
                "full_term": full_eng,
                "definition": def_kor,
            })
        elif acr in detected_defs:
            results.append({
                "acronym": acr,
                "full_term": detected_defs[acr],
                "definition": "본문 수록 전문 용어",
            })

    return results


def extract_in_text_citations(text: str) -> list[str]:
    """본문에서 [1], [2] 인용 부호 및 '※ 자료: ...' 출처 표기를 수집."""
    if not text:
        return []

    citations = []
    # 1. ※ 자료: ... 패턴
    source_pattern = re.compile(r"※\s*자료\s*:\s*(.+?)(?:\n|$)", re.MULTILINE)
    for m in source_pattern.finditer(text):
        src = m.group(1).strip()
        if src and src not in citations:
            citations.append(src)

    # 2. 학술 인용 부호 [1], [2] 뒤에 붙은 각주 패턴
    footnote_pattern = re.compile(r"\[\^?(\d+)\]\s*(.+?)(?:\n|$)", re.MULTILINE)
    for m in footnote_pattern.finditer(text):
        fn = f"[{m.group(1)}] {m.group(2).strip()}"
        if fn not in citations:
            citations.append(fn)

    return citations
