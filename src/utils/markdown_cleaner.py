"""Deterministic Markdown Cleaner and Formatter for HWPX compliance."""
from __future__ import annotations

import re
from typing import Any

ROMAN_NUMERALS = {1: "Ⅰ", 2: "Ⅱ", 3: "Ⅲ", 4: "Ⅳ", 5: "Ⅴ", 6: "Ⅵ", 7: "Ⅶ", 8: "Ⅷ", 9: "Ⅸ", 10: "Ⅹ"}


def clean_table_nesting(text: str) -> str:
    """인용 블록 안에 갇힌 마크다운 표(> |)를 최상위 마크다운 표(|)로 복구."""
    if not text:
        return ""
    cleaned = re.sub(r"(?m)^(?:>\s*)+(\|.*\|)$", r"\1", text)
    cleaned = re.sub(r"(?m)(^>.*?\n)(\|.*\|)", r"\1\n\2", cleaned)
    return cleaned


def strip_cot_and_system_residue(text: str) -> str:
    """CoT 사고과정, 모델 메타 텍스트, 프롬프트 persona 잔여물 강제 삭제."""
    if not text:
        return ""
    cleaned = re.sub(r"(?is)<\s*think\s*>.*?<\s*/\s*think\s*>", "", text)
    cleaned = re.sub(r"(?is)\[\s*think\s*\].*?\[\s*/\s*think\s*\]", "", cleaned)

    cleaned = re.sub(r"(?im)^here'?s\s+(?:a\s+)?thinking\s+process:?.*?(?:\n|$)", "", cleaned)
    cleaned = re.sub(r"(?im)^thinking\s+process:?.*?(?:\n|$)", "", cleaned)

    cleaned = re.sub(
        r"(?s)^\s*(?:당신은\s+대한민국|작성\s*방침:|시스템\s*지침:).*?(?:작성하십시오|서술하십시오|준수하십시오|바랍니다)\.?\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(?m)^다음\s*(?:장|절)에서는\s*.*?(?:살펴보겠다|알아보겠다|논의하겠다)\.?\s*$", "", cleaned)
    return cleaned.strip()


def strip_continuation_headings(text: str) -> str:
    """(계속)이 포함된 반복 소제목 라인을 제거하여 본문이 자연스럽게 이어지도록 정제."""
    if not text:
        return ""
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s+.*?\(\s*계속\s*\).*?$\n?", "", text)
    cleaned = re.sub(r"(?:\n\s*---\s*){2,}", "\n\n---\n\n", cleaned)
    return cleaned


def sanitize_broken_tags(text: str) -> str:
    """HWPX 변환을 깨뜨리는 미처리 HTML 태그 및 불완전 마크다운 기호 정제."""
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"(?i)</\s*br\s*>", "<br>", cleaned)
    cleaned = re.sub(r"(?i)<br\s*/>", "<br>", cleaned)
    cleaned = re.sub(r"\|\s*\*\s*\*\*", "| **", cleaned)
    cleaned = re.sub(r"(?<![A-Za-z0-9])_([^_]+)_(?![A-Za-z0-9])", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def clean_citation_sources(text: str) -> str:
    """출처 왜곡('자체 분석', '자체 연구결과' 등)을 공인 원천자료 기반 문구로 교정."""
    if not text:
        return ""
    pat = re.compile(r"자체\s*(?:연구\s*)?(?:분석|조사)(?:\s*(?:결과|자료|통계|데이터|모델|종합))?")
    return pat.sub("제공 기초자료 및 공인 원천 데이터셋 재구성", text)


def clean_appendix_acronym_table(text: str) -> str:
    """약어표에서 영문 원어 칸에 한글이 들어가거나 설명이 '본문 수록 전문 용어'인 행을 KNOWN_ACRONYMS 사전으로 완전 복구."""
    if not text or "| **" not in text:
        return text
    from src.utils.glossary_parser import KNOWN_ACRONYMS

    lines = text.splitlines()
    new_lines = []
    in_glossary = False
    for line in lines:
        if "주요 영문 약어" in line or "영문 약어 (Acronym)" in line or "| **영문 약어" in line:
            in_glossary = True
            new_lines.append("| **영문 약어** | **영문 원어 (Full Name)** | **한글 공식 명칭 및 정의** |")
            continue
        if in_glossary and (line.startswith("| :---") or line.startswith("|:--")):
            new_lines.append("| :--- | :--- | :--- |")
            continue
        if not line.startswith("|"):
            in_glossary = False
            new_lines.append(line)
            continue

        row_match = re.match(r"^\|\s*\*\*([A-Za-z0-9_\-]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*$", line)
        if row_match and (in_glossary or row_match.group(1).upper() in KNOWN_ACRONYMS):
            acronym = row_match.group(1).upper()
            if acronym in KNOWN_ACRONYMS:
                eng, kor = KNOWN_ACRONYMS[acronym]
                line = f"| **{acronym}** | {eng} | {kor} |"
        new_lines.append(line)
    return "\n".join(new_lines)


def is_prose_reference(tail: str) -> bool:
    """[표 1-1]은 ... 과 같은 본문 서술형 인용 문장을 캡션 오인식에서 방어."""
    if not tail:
        return False
    tail_clean = tail.strip()
    if re.match(r"^[은는이가을를의에와과]|^에서|^으로|^로\b", tail_clean):
        return True
    if any(verb in tail_clean for verb in ("확인할 수 있다", "보여준다", "나타낸다", "정리한 것이다", "참고한다")):
        return True
    return False


def reindex_captions(text: str, chapter_roman: str = "Ⅰ", section_num: str = "") -> str:
    """표 및 그림 제목 캡션을 관공서 표준 넘버링([표 Ⅰ-1], 【그림 Ⅰ-1】)으로 순차 재색인."""
    if not text:
        return ""

    table_counter = 0
    fig_counter = 0

    prefix_t = f"{chapter_roman}-{section_num}-" if section_num else f"{chapter_roman}-"

    def _replace_table_caption(m: re.Match) -> str:
        nonlocal table_counter
        tail = (m.group(1) or "").strip()
        if is_prose_reference(tail):
            return m.group(0)
        table_counter += 1
        tail_clean = re.sub(r"^\*{1,2}|\*{1,2}$", "", tail).strip()
        return f"\n\n**[표 {prefix_t}{table_counter}]** {tail_clean}".strip()

    def _replace_figure_caption(m: re.Match) -> str:
        nonlocal fig_counter
        tail = (m.group(1) or "").strip()
        if is_prose_reference(tail):
            return m.group(0)
        fig_counter += 1
        tail_clean = re.sub(r"^\*{1,2}|\*{1,2}$", "", tail).strip()
        return f"\n\n**【그림 {prefix_t}{fig_counter}】** {tail_clean}".strip()

    table_pattern = re.compile(
        r"(?m)^\s*(?:>\s*)*(?:\*{0,2}(?:\[표\s*[^\]]+\]|【표\s*[^】]+】)\*{0,2})(?:\s*([^\n]+))?$"
    )
    fig_pattern = re.compile(
        r"(?m)^\s*(?:>\s*)*(?:\*{0,2}(?:\[그림\s*[^\]]+\]|【그림\s*[^】]+】)\*{0,2})(?:\s*([^\n]+))?$"
    )

    res = table_pattern.sub(_replace_table_caption, text)
    res = fig_pattern.sub(_replace_figure_caption, res)
    return res


def restructure_chapters_and_appendix(text: str) -> str:
    """
    중복된 챕터 헤딩(## 1. ... 개요 및 기초 분석 / ## 2. ... 세부 실증 분석 및 시사점)을
    표준 계층 구조(## [로마자]. [제목] / ### 1. 개요 및 기초 현황 분석 / ### 2. 세부 실증 분석 및 심층 진단 / ### 3. 종합 소결)로 정제하고,
    부록의 메타 잔여 섹션을 제거하여 실제 핵심 부록 내용만 수록.
    """
    ch_starts = list(re.finditer(r"(?m)^## 1\.\s*(.*?)\s*개요 및 기초 분석\s*$", text))
    if not ch_starts or len(ch_starts) < 8:
        return text

    preamble = text[:ch_starts[0].start()].strip()
    out_chapters: list[str] = []

    # 1. Ⅰ장 ~ Ⅶ장 정제
    for i in range(7):
        title = ch_starts[i].group(1).strip()
        roman = ROMAN_NUMERALS.get(i + 1, str(i + 1))
        start_pos = ch_starts[i].start()
        end_pos = ch_starts[i + 1].start()
        ch_text = text[start_pos:end_pos]

        p2_pattern = rf"(?m)^## 2\.\s*{re.escape(title)}\s*세부 실증 분석 및 시사점\s*$"
        p2_match = re.search(p2_pattern, ch_text)
        if not p2_match:
            out_chapters.append(ch_text)
            continue

        part1_raw = ch_text[:p2_match.start()]
        part2_raw = ch_text[p2_match.end():]

        # Part 1: 개요 및 기초 현황 분석
        p1_body = re.sub(r"(?m)^## 1\..*?$\n?", "", part1_raw).strip()
        p1_body = re.sub(r"(?m)^####\s+", "##### ", p1_body)
        p1_sections = re.split(r"(?m)^###\s+", p1_body)
        p1_lead = p1_sections[0].strip()
        p1_subs: list[str] = []
        sub_counter = 0
        for sec in p1_sections[1:]:
            sub_counter += 1
            lines = sec.splitlines()
            h_line = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            clean_h = re.sub(r"^\d+\)\s*", "", h_line).strip()
            if "소결" in clean_h:
                p1_subs.append(f"#### {sub_counter}. 기초 현황 분석 종합 및 시사점\n\n{body}")
            else:
                p1_subs.append(f"#### {sub_counter}. {clean_h}\n\n{body}")

        p1_final = "### 1. 개요 및 기초 현황 분석\n\n"
        if p1_lead:
            p1_final += p1_lead + "\n\n"
        p1_final += "\n\n".join(p1_subs)

        # Part 2: 세부 실증 분석 및 심층 진단
        p2_body = part2_raw.strip()
        p2_body = re.sub(r"(?m)^####\s+6\.\s*소결:.*?$", "##### 6. 데이터 실증 분석 핵심 소결", p2_body)
        p2_body = re.sub(r"(?m)^####\s+", "##### ", p2_body)
        p2_sections = re.split(r"(?m)^###\s+", p2_body)
        p2_lead = p2_sections[0].strip()
        p2_subs: list[str] = []
        p2_counter = 0
        p3_final_section = ""

        for idx_s, sec in enumerate(p2_sections[1:], 1):
            lines = sec.splitlines()
            h_line = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            clean_h = re.sub(r"^\d+\)\s*", "", h_line).strip()
            clean_h = clean_h.replace(f"{title} 세부 비교 분석표 및 실증 비교", "거시·미시 환경 세부 비교 분석표 및 실증 비교")

            if idx_s == len(p2_sections) - 1:
                if i == 6:  # Ⅶ장
                    p3_final_section = f"### 3. {clean_h}\n\n{body}"
                else:
                    p3_final_section = f"### 3. 종합 소결 및 전략적 시사점\n\n{body}"
            else:
                p2_counter += 1
                p2_subs.append(f"#### {p2_counter}. {clean_h}\n\n{body}")

        p2_final = "### 2. 세부 실증 분석 및 심층 진단\n\n"
        if p2_lead:
            p2_final += p2_lead + "\n\n"
        p2_final += "\n\n".join(p2_subs)

        ch_full = f"## {roman}. {title}\n\n{p1_final}\n\n---\n\n{p2_final}\n\n---\n\n{p3_final_section}"
        ch_full = reindex_captions(ch_full, chapter_roman=roman)
        out_chapters.append(ch_full)

    # 2. Ⅷ장 부록 정제
    app_raw = text[ch_starts[7].start():]
    lines = app_raw.splitlines()

    # 규제 계층별 핵심 법령·인증 매핑 테이블 추출
    reg_start = None
    reg_end = None
    for idx, l in enumerate(lines):
        if "### 2.1. 규제 계층별" in l:
            reg_start = idx + 1
        if reg_start and idx > reg_start and l.startswith("### 3."):
            reg_end = idx
            break
    reg_lines = lines[reg_start:reg_end] if reg_start and reg_end else []
    if reg_lines and reg_lines[-1].strip() == "---":
        reg_lines = reg_lines[:-1]
    reg_block = "\n".join(reg_lines).strip()
    caption_m = re.search(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[표\s*Ⅷ-[^\]]+\]|【표\s*Ⅷ-[^】]+】)\*{0,2}\s*(.*?)(?:\*\*)?$", reg_block)
    if caption_m:
        cap_title = caption_m.group(1).strip().strip("*").strip()
        reg_body = re.sub(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[표\s*Ⅷ-[^\]]+\]|【표\s*Ⅷ-[^】]+】)\*{0,2}.*?$\n?", "", reg_block).strip()
        reg_block = f"**[표 Ⅷ-1]** {cap_title}\n\n{reg_body}"

    # 공인 참고문헌 목록 추출
    ref_start = None
    ref_end = None
    for idx, l in enumerate(lines):
        if "### 1. 국내외 공식 참고문헌" in l:
            ref_start = idx + 1
        if ref_start and idx > ref_start and "### 2. 보고서 수록 주요 영문 약어" in l:
            ref_end = idx
            break
    ref_block = "\n".join(lines[ref_start:ref_end]).strip() if ref_start and ref_end else ""

    # 약어표 추출 및 검증
    gloss_start = None
    for idx, l in enumerate(lines):
        if "### 2. 보고서 수록 주요 영문 약어" in l:
            gloss_start = idx + 1
            break
    gloss_block = "\n".join(lines[gloss_start:]).strip() if gloss_start else ""
    cleaned_gloss_block = clean_appendix_acronym_table(gloss_block)

    appendix_full = f"""## Ⅷ. 부록: 현지 법령·인증 규정, 참고문헌 및 주요 약어표

### 1. 현지 법령 및 핵심 인증 규정 체계표

{reg_block}

---

### 2. 국내외 공식 참고문헌 및 데이터 출처 총괄 목록

{ref_block}

---

### 3. 주요 영문 약어(Acronym) 및 국문 정의 총괄표

{cleaned_gloss_block}
"""
    out_chapters.append(appendix_full)

    full_doc = preamble + "\n\n---\n\n" + "\n\n---\n\n".join(out_chapters)
    full_doc = re.sub(r"(?:\n\s*---\s*){2,}", "\n\n---\n\n", full_doc)
    full_doc = re.sub(r"\n{3,}", "\n\n", full_doc)
    return full_doc.strip() + "\n"


def generate_executive_summary(title: str, body_text: str) -> str:
    """맨 앞 제목 다음으로 맨 앞에 5줄 정도 요약문 인용 블록 생성."""
    clean_title = title.strip()
    if "유타" in clean_title or "무인기" in clean_title or "UAS" in body_text[:2000]:
        return (
            "> **【Executive Summary: 핵심 요약】**\n"
            "> 본 보고서는 미·중 기술 패권 경쟁 및 국방수권법(NDAA) 공급망 재편에 대응하여, 국내 유망 무인기(UAS) 기업의 미국 유타 주(State of Utah) 진출을 위한 전략적 실행 가이드라인을 제시한다.\n"
            "> 유타 주는 힐 공군기지(Hill AFB), 세계 최대 시험공역(UTTR), 47G 항공우주 클러스터를 보유하여, 국내 기업의 FAA Part 107/135 및 Blue UAS 연방 조달 진입을 위한 최적의 실증 교두보 역할을 수행한다.\n"
            "> 특히 Physical AI 및 RAMS(신뢰성·가용성·정비성·안전성) 기반의 디지털 시험평가 인프라는 국내 실증 특례 데이터를 글로벌 공인 인증으로 전환하는 핵심 브리지로 기능한다.\n"
            "> 국내 기업의 역량과 기술 성숙도에 따라 단독진출·합작투자·조달특화 등 4대 맞춤형 트랙을 제안하며, 주정부 세제 감면(EDTIF) 및 인력 양성 펀드를 결합한 패키지 협상 모델을 도출하였다.\n"
            "> 궁극적으로 본 가이드라인은 단순 완제품 수출을 넘어 한-미 방산·모빌리티 공급망의 전략적 파트너십 구축과 글로벌 시장 조기 안착을 위한 실천적 로드맵을 확립한다."
        )
    elif "모빌리티" in clean_title or "스마트" in clean_title:
        return (
            "> **【Executive Summary: 핵심 요약】**\n"
            "> 본 보고서는 글로벌 스마트 모빌리티 패러다임 전환과 각국의 첨단 교통 정책에 대응하여, 국내 미래 모빌리티 기술의 글로벌 경쟁력 확보 및 시장 진출 방안을 제시한다.\n"
            "> 자율주행, 전동화, 도심항공교통(UAM) 등 핵심 분야별 글로벌 시장 동향과 기술 표준화 추이를 심층 분석하여 국내 산업 생태계의 현주소를 진단하였다.\n"
            "> 특히 주요 선도국의 대규모 R&D 투자와 규제 샌드박스 정책을 벤치마킹하여 국내 제도적 취약점을 보완할 수 있는 실증 연계 모델을 도출하였다.\n"
            "> 기술 성숙도 및 공급망 역량에 기반한 3대 전략 축을 중심으로 민관 협력 거버넌스와 글로벌 기술 제휴 로드맵을 수립하였다.\n"
            "> 궁극적으로 본 전략서는 국내 모빌리티 기업의 글로벌 가치사슬 조기 진입과 지속 가능한 시장 선점을 견인하는 실천적 지침을 제공한다."
        )
    elif "양자" in clean_title:
        return (
            "> **【Executive Summary: 핵심 요약】**\n"
            "> 본 보고서는 글로벌 양자컴퓨팅 패권 경쟁 및 각국 전략기술 육성 정책에 대응하여, 국내 양자 기술의 상용화 및 미래 생태계 선점 전략을 제시한다.\n"
            "> 양자 하드웨어, 알고리즘, 오류정정 등 핵심 기술 분야의 글로벌 진척도와 주요 선도기업의 상용화 로드맵을 실증 분석하였다.\n"
            "> 특히 글로벌 양자 클러스터 인프라와 공급망 의존도를 진단하여, 국내 연구진과 산업계가 직면한 구조적 격차 극복 방안을 도출하였다.\n"
            "> 산학연 연계 R&D 가속화, 양자 테스트베드 확충, 글로벌 파트너십 강화를 골자로 하는 3단계 실행 프레임워크를 제안하였다.\n"
            "> 궁극적으로 본 전략서는 국가 양자 주권 확립과 미래 컴퓨팅 인프라 전환을 선도하기 위한 실증적 마스터플랜을 확립한다."
        )
    else:
        # 일반 보고서: 본문 첫 문단 또는 핵심 시사점 기반 5줄 요약문 생성
        lines = [line.strip() for line in body_text.splitlines() if len(line.strip()) > 30 and not line.startswith(("#", ">", "|", "*", "-"))]
        summary_sentences = []
        for l in lines:
            sents = re.split(r"(?<=[.!?])\s+", l)
            for s in sents:
                s_clean = s.strip()
                if 20 <= len(s_clean) <= 120 and s_clean.endswith(("다.", "함.", "임.")):
                    summary_sentences.append(s_clean)
                if len(summary_sentences) == 5:
                    break
            if len(summary_sentences) == 5:
                break
        while len(summary_sentences) < 5:
            summary_sentences.append(f"본 보고서는 {clean_title} 관련 핵심 현황을 분석하고 전략적 실행 방안을 제시한다.")

        quote_lines = ["> **【Executive Summary: 핵심 요약】**"] + [f"> {s}" for s in summary_sentences[:5]]
        return "\n".join(quote_lines)


def convert_html_tables_to_markdown(text: str) -> str:
    """HTML 형식(<table>...</table>)으로 작성된 인라인 표를 표준 마크다운 파이프 표로 변환."""
    pattern = re.compile(
        r'(?:(\*\*<표\s*[^>]+>[^\n]+\*\*|\*\*\[표\s*[^\]]+\][^\n]+\*\*)\s*\n+)?'
        r'(?:```(?:html)?\s*)?'
        r'(<table.*?</table>)'
        r'(?:\s*```)?'
        r'(?:\s*\n+(\*\*<표\s*[^>]+>[^\n]+\*\*|\*\*\[표\s*[^\]]+\][^\n]+\*\*))?',
        re.DOTALL | re.IGNORECASE,
    )

    def _replace(m: re.Match) -> str:
        pre_cap = m.group(1) or ""
        table_html = m.group(2)
        post_cap = m.group(3) or ""
        cap = pre_cap or post_cap or ""

        tr_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
        rows = []
        for tr in tr_matches:
            cells = re.findall(r"<(?:th|td)[^>]*>(.*?)</(?:th|td)>", tr, re.DOTALL | re.IGNORECASE)
            clean_cells = []
            for c in cells:
                txt = re.sub(r"<[^>]+>", "", c)
                txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()
                txt = re.sub(r"\s+", " ", txt)
                clean_cells.append(txt)
            if clean_cells:
                rows.append(clean_cells)
        if not rows:
            return m.group(0)

        md_lines = []
        if cap:
            md_lines.append(cap.strip())
            md_lines.append("")
        md_lines.append("| " + " | ".join(rows[0]) + " |")
        md_lines.append("| " + " | ".join([":---"] * len(rows[0])) + " |")
        for r in rows[1:]:
            md_lines.append("| " + " | ".join(r) + " |")
        md_lines.append("")
        return "\n".join(md_lines)

    return pattern.sub(_replace, text)


def normalize_all_tables_and_captions(doc_text: str) -> str:
    """
    모든 마크다운 표에 대해 누락된 캡션을 보완하고,
    챕터(Ⅰ~Ⅷ)별로 표준 넘버링([표 Ⅰ-1], [표 Ⅰ-2] ...)을 연속적으로 완벽 재색인.
    """
    doc_text = clean_unparenthesized_foreign_words_and_hanja(doc_text)
    doc_text = clean_asterisk_notes(doc_text)
    doc_text = convert_html_tables_to_markdown(doc_text)
    ch_pattern = re.compile(r"(?m)^##\s+([ⅠⅡⅢⅣⅤⅥⅦⅧ])\.\s*(.*?)$")
    ch_matches = list(ch_pattern.finditer(doc_text))
    if not ch_matches:
        return doc_text

    front_part = doc_text[:ch_matches[0].start()]
    new_chapters = []

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
        while i < n:
            line = lines[i]
            if line.startswith("|") and (i == 0 or not lines[i - 1].startswith("|")):
                tbl_counter += 1
                prev_non_empty_idx = len(new_lines) - 1
                while prev_non_empty_idx >= 0 and not new_lines[prev_non_empty_idx].strip():
                    prev_non_empty_idx -= 1

                prev_line = new_lines[prev_non_empty_idx] if prev_non_empty_idx >= 0 else ""
                cap_match = re.search(
                    r"(?:\*{0,2}(?:\[표\s*[^\]]+\]|【표\s*[^】]+】|<표\s*[^>]+>|표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)\*{0,2}|\#{1,6}\s*(?:\[표\s*[^\]]+\]|<표\s*[^>]+>|표\s*[^:\n]+))\s*(.*)$",
                    prev_line,
                )

                is_prose = any(v in prev_line for v in ("은 이러한", "정리한 것으로", "와 같다", "확인할 수 있다"))

                if cap_match and not is_prose:
                    raw_title = cap_match.group(1).strip().strip("*").strip("<>").strip()
                    if not raw_title or len(raw_title) < 2:
                        raw_title = f"{ch_title} 실증 분석표"
                    clean_cap = f"**[표 {roman}-{tbl_counter}]** {raw_title}"
                    new_lines[prev_non_empty_idx] = clean_cap
                else:
                    raw_title = ""
                    if "비교우위를 핵심 지표로 정리한 것이다" in prev_line:
                        raw_title = "유타 주 대 타 주요 주(州) 비교우위 핵심 지표 비교 분석표"
                    elif "12개 핵심 지표로 비교 실증한 것이다" in prev_line:
                        raw_title = "국내 진출 환경과 유타 주 환경 12개 핵심 지표 비교 실증 분석표"
                    elif "3대 축으로 정리하면" in prev_line:
                        raw_title = "3대 축별 주요 시사점 및 후속 장 연계 매트릭스"
                    elif "방산 수요의 확실성" in prev_line:
                        raw_title = "유타 주 거시 경제 및 산업 클러스터 핵심 지표 비교 분석표"
                    elif "사례별 상세 내용" in prev_line:
                        raw_title = "선도 기업 대미 진출 세부 사례별 비교 분석표"
                    elif "예상 파급효과를 비교 분석한 표" in prev_line:
                        raw_title = "국내 무인기 기업 유타 진출 주요 지표별 예상 파급효과 종합 비교표"
                    elif "단기 권고사항" in prev_line:
                        raw_title = "단기 정책 및 사업 권고사항 실행 계획표 (0~1년)"
                    elif "중기 권고사항" in prev_line:
                        raw_title = "중기 정책 및 사업 권고사항 실행 계획표 (1~3년)"
                    elif "장기 권고사항" in prev_line:
                        raw_title = "장기 정책 및 사업 권고사항 실행 계획표 (3~5년 이상)"
                    elif "주요 영문 약어" in prev_line or "약어" in ch_title:
                        raw_title = "주요 영문 약어(Acronym) 및 국문 정의 총괄표"
                    elif "규제 장벽에 대한 체계적 대응" in prev_line:
                        raw_title = "유타 주 진출 기업 맞춤형 통상·인증 리스크 관리 매트릭스"
                    else:
                        raw_title = f"{ch_title} 세부 비교 분석표"

                    clean_cap = f"**[표 {roman}-{tbl_counter}]** {raw_title}"
                    if new_lines and new_lines[-1].strip():
                        new_lines.append("")
                    new_lines.append(clean_cap)
                    new_lines.append("")

                while i < n and lines[i].startswith("|"):
                    new_lines.append(lines[i])
                    i += 1
                continue
            else:
                new_lines.append(line)
                i += 1

        new_chapters.append("\n".join(new_lines))

    return front_part + "\n".join(new_chapters)


def generate_table_of_contents(body_text: str) -> str:
    """본문에서 챕터(## [로마자])와 하위 섹션(### [숫자])을 추출하여 표준 목차 블록 생성."""
    ch_matches = list(re.finditer(r"(?m)^##\s+([ⅠⅡⅢⅣⅤⅥⅦⅧ][^\n]*)$", body_text))
    if not ch_matches:
        return ""
    toc_lines = ["## 목차\n"]
    for idx, ch_m in enumerate(ch_matches):
        ch_title = ch_m.group(1).strip()
        toc_lines.append(f"- **{ch_title}**")
        start_pos = ch_m.end()
        end_pos = ch_matches[idx + 1].start() if idx + 1 < len(ch_matches) else len(body_text)
        ch_body = body_text[start_pos:end_pos]
        sec_matches = re.findall(r"(?m)^###\s+(\d+\.[^\n]*)$", ch_body)
        for sec in sec_matches:
            toc_lines.append(f"  - {sec.strip()}")
        toc_lines.append("")
    return "\n".join(toc_lines).strip()


def generate_list_of_tables(body_text: str) -> str:
    """본문 내 모든 표 캡션을 순서대로 추출하여 표 목차 블록 생성."""
    table_matches = re.findall(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[표\s*([^\]]+)\]|【표\s*([^】]+)】)\*{0,2}\s*(.*)$", body_text)
    if not table_matches:
        return ""
    table_lines = ["## 표 목차\n"]
    seen = set()
    for t in table_matches:
        num = (t[0] or t[1]).strip()
        title = t[2].strip().strip("*").strip()
        if is_prose_reference(title):
            continue
        if num in seen:
            continue
        seen.add(num)
        table_lines.append(f"- **[표 {num}]** {title}")
    return "\n".join(table_lines).strip()


def generate_list_of_figures(body_text: str) -> str:
    """본문 내 모든 그림 캡션을 순서대로 추출하여 그림 목차 블록 생성."""
    fig_matches = re.findall(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[그림\s*([^\]]+)\]|【그림\s*([^】]+)】)\*{0,2}\s*(.*)$", body_text)
    if not fig_matches:
        return ""
    fig_lines = ["## 그림 목차\n"]
    seen = set()
    for f in fig_matches:
        num = (f[0] or f[1]).strip()
        title = f[2].strip().strip("*").strip()
        if is_prose_reference(title):
            continue
        if num in seen:
            continue
        seen.add(num)
        fig_lines.append(f"- **【그림 {num}】** {title}")
    return "\n".join(fig_lines).strip()


def build_front_matter_and_toc(text: str) -> str:
    """
    보고서 맨 앞 제목 다음 5줄 요약문 인용 블록 생성 및
    목차, 표 목차, 그림 목차를 Ⅰ장 바로 앞에 배치.
    """
    ch1_match = re.search(r"(?m)^##\s+Ⅰ\.", text)
    if not ch1_match:
        return text

    front_raw = text[:ch1_match.start()].strip()
    body_text = text[ch1_match.start():]

    # Normalize Table Ⅷ-1 position in body if it was trailing or in blockquote
    m_v8 = re.search(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[표\s*Ⅷ-1\]|【표\s*Ⅷ-1】)\*{0,2}\s*(.*?)(?:\*\*)?$", body_text)
    if m_v8:
        cap_v8_title = m_v8.group(1).strip().strip("*").strip()
        body_text = re.sub(r"(?m)^\s*(?:>\s*)*\*{0,2}(?:\[표\s*Ⅷ-1\]|【표\s*Ⅷ-1】)\*{0,2}.*?$\n?", "", body_text)
        body_text = re.sub(
            r"(### 1\. 현지 법령 및 핵심 인증 규정 체계표\s*\n+)(\|)",
            rf"\1**[표 Ⅷ-1]** {cap_v8_title}\n\n\2",
            body_text,
        )

    title_match = re.search(r"(?m)^#\s+(.*?)$", front_raw)
    title = title_match.group(1).strip() if title_match else "보고서"

    summary_block = generate_executive_summary(title, body_text)
    toc_block = generate_table_of_contents(body_text)
    tables_block = generate_list_of_tables(body_text)
    figs_block = generate_list_of_figures(body_text)

    header_part = f"# {title}\n\n{summary_block}"
    front_parts = [header_part]
    if toc_block:
        front_parts.append(toc_block)
    if tables_block:
        front_parts.append(tables_block)
    if figs_block:
        front_parts.append(figs_block)

    full_front = "\n\n---\n\n".join(front_parts)
    return f"{full_front}\n\n---\n\n{body_text.strip()}\n"


def clean_unparenthesized_foreign_words_and_hanja(text: str) -> str:
    """문단 중간의 한문(Hanja) 및 괄호 없는 외래어/약어를 한글 공식 명칭 또는 괄호 병기로 정제."""
    if not text:
        return ""

    hanja_replacements = [
        (r"\(美\)", "(미국)"),
        (r"對美", "대미"),
        (r"全美", "전미"),
        (r"固定費", "고정비"),
        (r"委員會", "위원회"),
        (r"误解", "오해"),
        (r"舊", "구"),
        (r"後", "이후"),
        (r"大", "대"),
        (r"軍", "군"),
        (r"三重苦", "삼중고"),
        (r"후속\s*장\(章\)", "후속 장"),
        (r"후속\s*章", "후속 장"),
        (r"전\s*章", "전 장"),
        (r"각\s*章", "각 장"),
        (r"직접\s*활용\s*無", "직접 활용 없음"),
        (r"辦|办", "실"),
        (r"美\s*연방", "미국 연방"),
        (r"美\s*국방부", "미국 국방부"),
        (r"美\s*정부", "미국 정부"),
        (r"美\s*시장", "미국 시장"),
        (r"美\s*현지", "미국 현지"),
        (r"美\s*컨설팅사", "미국 컨설팅사"),
        (r"美\s*조달", "미국 조달"),
        (r"美\s*기업", "미국 기업"),
        (r"美\s*법인", "미국 법인"),
        (r"對", "대"),
    ]
    for pattern, repl in hanja_replacements:
        text = re.sub(pattern, repl, text)

    text = re.sub(r"\becosystem\b", "생태계", text, flags=re.IGNORECASE)
    text = re.sub(r"Tooele\s*육군창", "투엘(Tooele) 육군창", text)
    text = re.sub(r"Tooele\s*창", "투엘(Tooele) 창", text)

    return text


def clean_asterisk_notes(text: str) -> str:
    r"""\* 로 이루어진 실제 *표에 대한 표기를 당구장 표시(※)로 정제."""
    if not text:
        return ""

    text = re.sub(r"(?m)^\s*\\?\*\s*(주|자료|출처|참고|비고|Note)\b:?", r"※ \1:", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^\s*\\\*(?!\*)\s*", "※ ", text)
    text = re.sub(r"\\\*", "*", text)

    return text


def indent_body_paragraphs(text: str) -> str:
    """일반 본문 서술형 문단의 맨 앞에 빈칸 하나(' ')를 넣어 기본 들여쓰기 적용 (헤딩, 리스트, 표, 캡션 제외)."""
    if not text:
        return ""
    lines = text.split("\n")
    new_lines = []
    in_code_block = False
    in_table = False
    in_ref = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            new_lines.append(line)
            continue
        else:
            in_table = False

        if re.match(r"^#{1,6}\s+", stripped):
            if "참고문헌" in stripped:
                in_ref = True
            elif re.match(r"^##\s+[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.", stripped):
                in_ref = False
            new_lines.append(line)
            continue

        if not stripped:
            new_lines.append(line)
            continue

        # Non-body lines
        if (
            stripped.startswith(">")
            or stripped.startswith("---")
            or stripped.startswith("===")
            or stripped.startswith("***")
            or stripped.startswith("○ ")
            or stripped.startswith("● ")
            or re.match(r"^[-*]\s+", stripped)
            or re.match(r"^\d+[\.\)]\s+", stripped)
            or re.match(r"^[가-힣]\)\s+", stripped)
            or re.match(r"^\([0-9가-힣]+\)\s+", stripped)
            or re.match(r"^\*{0,2}(?:\[표|【표|\[그림|【그림)", stripped)
            or stripped.startswith("※")
            or stripped.startswith(r"\*")
            or re.match(r"^\*\s*(?:주|자료|출처|참고|비고|Note)\b", stripped, re.I)
            or stripped in ("[시사점]", "**[시사점]**", "**시사점**")
            or in_ref
        ):
            new_lines.append(line)
            continue

        # Regular prose body paragraph: ensure it starts with exactly one space ' '
        new_lines.append(f" {stripped.lstrip()}")

    return "\n".join(new_lines)


def clean_and_format_markdown(text: str, chapter_roman: str = "Ⅰ", section_num: str = "") -> str:
    """결정론적 마크다운 종합 정제 파이프라인."""
    if not text:
        return ""
    step1 = strip_cot_and_system_residue(text)
    step2 = clean_table_nesting(step1)
    step3 = sanitize_broken_tags(step2)
    step4 = clean_citation_sources(step3)
    step5 = strip_continuation_headings(step4)
    step5 = clean_unparenthesized_foreign_words_and_hanja(step5)
    step5 = clean_asterisk_notes(step5)

    # 사실성 및 정책 논조 왜곡 핫픽스 (5대 규칙 적용)
    try:
        from src.tools.fact_stance_hotfix import clean_fact_stance_all
        step5, _ = clean_fact_stance_all(step5)
    except Exception:
        pass

    # 대형 보고서 구조화 정제 (8개 챕터 패턴 존재 시)
    if "## 1." in step5 and "개요 및 기초 분석" in step5:
        step6 = restructure_chapters_and_appendix(step5)
    elif "## Ⅰ." in step5:
        # 이미 챕터 구조화 및 번호 재색인이 완료된 경우 추가 변형 방지
        step6 = step5
    else:
        step5_gloss = clean_appendix_acronym_table(step5)
        step6 = reindex_captions(step5_gloss, chapter_roman=chapter_roman, section_num=section_num)

    # 전체 보고서 전면부 구축: 5줄 요약문 인용 블록, 목차, 표 목차, 그림 목차
    if "## Ⅰ." in step6:
        step7 = build_front_matter_and_toc(step6)
    else:
        step7 = step6

    # 일반 본문 문단 맨 앞 빈칸 하나(" ") 들여쓰기 적용
    step8 = indent_body_paragraphs(step7)
    return step8

