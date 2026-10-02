"""Unit tests verifying resolution of the 4 standalone verifier issues:
1. Stripping repetitive (계속) headings
2. Chapter restructuring (## Ⅰ. ~ Ⅷ.) and resolving duplicate implications
3. Cleaning appendix: pruning pseudo-sections, keeping regulation table, citations, acronym table
4. Acronym table validation: 100% verified English/Korean pairs, 0 placeholders
"""
from __future__ import annotations

import re
from src.utils.markdown_cleaner import (
    strip_continuation_headings,
    clean_appendix_acronym_table,
    restructure_chapters_and_appendix,
    clean_and_format_markdown,
)
from src.utils.glossary_parser import KNOWN_ACRONYMS


def test_strip_continuation_headings():
    sample = """
### 1) 글로벌 공급망 재편과 유타 주 전략적 진입의 당위성
본문 내용 1

### 1) 글로벌 공급망 재편과 유타 주 전략적 진입의 당위성 (계속)
본문 내용 2

### 1) 글로벌 공급망 재편과 유타 주 전략적 진입의 당위성 (계속) (계속)
본문 내용 3
"""
    cleaned = strip_continuation_headings(sample)
    assert "(계속)" not in cleaned
    assert "본문 내용 1" in cleaned
    assert "본문 내용 2" in cleaned
    assert "본문 내용 3" in cleaned


def test_acronym_table_known_acronyms_completeness():
    # Test specific keys that were previously missing
    assert "AFLCMC" in KNOWN_ACRONYMS
    assert "AFRL" in KNOWN_ACRONYMS
    assert "AMMI" in KNOWN_ACRONYMS
    assert "AC" in KNOWN_ACRONYMS
    assert "AIRC" in KNOWN_ACRONYMS

    # Verify no Korean characters in English full name
    korean_pat = re.compile(r"[가-힣]")
    for k, (eng, kor) in KNOWN_ACRONYMS.items():
        assert not korean_pat.search(eng), f"Korean found in English term for {k}: {eng}"
        assert kor and len(kor.strip()) >= 2
        assert "본문 수록" not in kor


def test_clean_appendix_acronym_table():
    sample_glossary = """
### 3. 주요 영문 약어(Acronym) 및 국문 정의 총괄표

| 영문 약어 (Acronym) | 영문 원어 (Full Term) | 한글 공식 명칭 및 핵심 정의 |
| :--- | :--- | :--- |
| **AC** | 감항증명 | 본문 수록 전문 용어 |
| **AFLCMC** | 힐 공군기지 | 본문 수록 전문 용어 |
| **AI** | Artificial Intelligence | 인공지능 |
"""
    cleaned = clean_appendix_acronym_table(sample_glossary)
    assert "본문 수록 전문 용어" not in cleaned
    assert "Advisory Circular" in cleaned
    assert "Air Force Life Cycle Management Center" in cleaned


def test_chapter_and_appendix_restructuring():
    # Synthetic mini-report with 8 chapters
    ch_blocks = []
    titles = [
        "개요 및 해외 진출 추진 배경",
        "글로벌 타겟 시장 환경 및 산업 트렌드 분석",
        "국내 기업 해외 진출 현황 및 구조적 애로사항",
        "주요국 시장 진출 지원 프로그램 및 제도 조사",
        "해외 시장 진출 전략 및 맞춤형 트랙 설계",
        "진출 실행 가이드라인 및 통상·인증 리스크 관리 방안",
        "기대효과 및 종합 결론",
        "부록 (현지 법령·인증 규정, 참고문헌 및 주요 약어표)",
    ]

    doc_parts = ["# 보고서 제목\n\n> 개요\n\n---\n"]
    for i, t in enumerate(titles[:7]):
        doc_parts.append(f"""## 1. {t} 개요 및 기초 분석

### 1) {t} 관련 핵심 이슈
기초 분석 내용

### 1) 소결: 본 절의 주요 시사점 및 연계 방향
소결 내용

---

## 2. {t} 세부 실증 분석 및 시사점

### 1) {t} 세부 데이터 실증 분석
실증 분석 내용

### 1) 소결: 본 절의 주요 시사점 및 연계 방향
최종 시사점 내용
""")

    # Appendix
    doc_parts.append("""## 1. 부록 (현지 법령·인증 규정, 참고문헌 및 주요 약어표) 개요 및 기초 분석

### 1. 부록 편제 방향 및 분석 체계
메타 서술 내용

### 2. 현지 법령·인증 규정 체계화 기초 분석

### 2.1. 규제 계층별 핵심 법령 및 인증 매핑 테이블

| 규제 계층 | 법적 근거 | 주요 규율 대상 | 핵심 쟁점 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **연방 (Federal)** | **14 CFR Part 107** | 드론 운용 | BVLOS 승인 | RAMS 센터 연계 |

> **【표 Ⅷ-1】 핵심 법령 매핑**

### 3. 참고문헌 및 주요 약어표 편제 기초 분석
메타 내용

### 5. 소결: 본 절의 주요 시사점
메타 시사점

## 2. 부록 (현지 법령·인증 규정, 참고문헌 및 주요 약어표) 세부 실증 분석 및 시사점

### 1. 부록 구성 방향
20260820\\이사님 지시사항.md

## Ⅷ 부록 (현지 법령·인증 규정, 참고문헌 및 주요 약어표)

### 1. 국내외 공식 참고문헌 및 데이터 출처 총괄 목록

1. FAA Official Regulations (https://www.faa.gov)

### 2. 보고서 수록 주요 영문 약어(Acronym) 및 전문용어 총괄 정의표 (Glossary)

| 영문 약어 (Acronym) | 영문 원어 (Full Term) | 한글 공식 명칭 및 핵심 정의 |
| :--- | :--- | :--- |
| **FAA** | Federal Aviation Administration | 미국 연방항공청 |
""")

    full_raw = "\n\n---\n\n".join(doc_parts)
    cleaned = restructure_chapters_and_appendix(full_raw)

    # 1. Check Roman numeral headings
    assert "## Ⅰ. 개요 및 해외 진출 추진 배경" in cleaned
    assert "## Ⅶ. 기대효과 및 종합 결론" in cleaned
    assert "## Ⅷ. 부록: 현지 법령·인증 규정, 참고문헌 및 주요 약어표" in cleaned

    # 2. Check 3-level section hierarchy
    assert "### 1. 개요 및 기초 현황 분석" in cleaned
    assert "### 2. 세부 실증 분석 및 심층 진단" in cleaned
    assert "### 3. 종합 소결 및 전략적 시사점" in cleaned

    # 3. Check appendix cleanup
    assert "부록 편제 방향" not in cleaned
    assert "이사님 지시사항" not in cleaned
    assert "### 1. 현지 법령 및 핵심 인증 규정 체계표" in cleaned
    assert "### 2. 국내외 공식 참고문헌 및 데이터 출처 총괄 목록" in cleaned
    assert "### 3. 주요 영문 약어(Acronym) 및 국문 정의 총괄표" in cleaned


def test_front_matter_and_toc_generation():
    from src.utils.markdown_cleaner import build_front_matter_and_toc, clean_and_format_markdown

    sample = """# (美)유타 주 내 국내기업 진출 가이드라인

> **【기존 메타정보】**
> - 유형: 전략보고서

---

## Ⅰ. 개요 및 해외 진출 추진 배경

### 1. 개요 및 기초 현황 분석

**[표 Ⅰ-1]** 유타 주 UAM 핵심 지표

**【그림 Ⅰ-1】** 유타 주 진입 프레임워크

### 2. 세부 실증 분석 및 심층 진단

### 3. 종합 소결 및 전략적 시사점

---

## Ⅱ. 글로벌 타겟 시장 환경 및 산업 트렌드 분석

### 1. 개요 및 기초 현황 분석

**[표 Ⅱ-1]** 글로벌 타겟 시장 지표

**【그림 Ⅱ-1】** 시장 트렌드 구조도

### 2. 세부 실증 분석 및 심층 진단

### 3. 종합 소결 및 전략적 시사점
"""
    result = build_front_matter_and_toc(sample)

    # 1. 5줄 요약문 인용 블록 검증
    assert "> **【Executive Summary: 핵심 요약】**" in result
    summary_lines = [l for l in result.splitlines() if l.startswith("> ") and "Executive Summary" not in l]
    assert len(summary_lines) >= 5, f"Expected at least 5 summary lines, got {len(summary_lines)}"

    # 2. 제목 바로 뒤 요약문 배치 검증 (제목과 요약문 사이에 --- 없음)
    title_idx = result.find("# (美)유타 주 내 국내기업 진출 가이드라인")
    summary_idx = result.find("> **【Executive Summary: 핵심 요약】**")
    between = result[title_idx + len("# (美)유타 주 내 국내기업 진출 가이드라인"):summary_idx].strip()
    assert "---" not in between, "There should not be a horizontal rule between title and executive summary"

    # 3. 목차, 표 목차, 그림 목차 생성 검증
    assert "## 목차" in result
    assert "- **Ⅰ. 개요 및 해외 진출 추진 배경**" in result
    assert "  - 1. 개요 및 기초 현황 분석" in result
    assert "- **Ⅱ. 글로벌 타겟 시장 환경 및 산업 트렌드 분석**" in result

    assert "## 표 목차" in result
    assert "- **[표 Ⅰ-1]** 유타 주 UAM 핵심 지표" in result
    assert "- **[표 Ⅱ-1]** 글로벌 타겟 시장 지표" in result

    assert "## 그림 목차" in result
    assert "- **【그림 Ⅰ-1】** 유타 주 진입 프레임워크" in result
    assert "- **【그림 Ⅱ-1】** 시장 트렌드 구조도" in result

    # 4. 멱등성 검증 (재실행 시 목차나 요약문이 중복되지 않음)
    second_pass = build_front_matter_and_toc(result)
    assert second_pass.count("## 목차") == 1
    assert second_pass.count("## 표 목차") == 1
    assert second_pass.count("## 그림 목차") == 1
    assert second_pass.count("【Executive Summary: 핵심 요약】") == 1

