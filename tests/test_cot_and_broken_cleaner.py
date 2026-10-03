"""Tests for enhanced CoT and broken character stripping in markdown_cleaner."""
import re
from src.utils.markdown_cleaner import strip_cot_and_system_residue


def test_strip_california_cot_monologues():
    sample = """## Ⅰ. 개요 및 해외 진출 추진 배경

### 1. 개요 및 기초 현황 분석

We need to produce a deep analysis for the section: "개요 및 해외 진출 추진 배경 관련 핵심 이슈 심층 분석". Must follow rules: tone: government research style: ending with ~함, ~임.
We need to write in Korean, with government research tone: ending with ~함, ~임.
Let's draft paragraphs, ensuring each sentence ends with ~함 or ~임.
Ok I'm going to assume that "있음" is acceptable as a noun ending with "음" but the rule might be flexible.
Sentence 1: "최근 전 세계 무인기 시장은 급속한 성장을 보이며, 특히 캘리포니아 주는 혁신 생태계와 규제 친환경으로 주목받고 있음."
Thus we can make sentences where the predicate is a noun ending with 함/임, not a verb.
Maybe we can say: "캘리포니아 주의 혁신 생태계와 규제 친환경은 주목받고 있음." Not good.

#### 1. 주요 현황 및 팩트 분석 심층 분석

본 절에서는 캘리포니아 주의 드론 산업 생태계 현황을 심층 분석함.
"""
    cleaned = strip_cot_and_system_residue(sample)
    assert "We need to produce" not in cleaned
    assert "Let's draft paragraphs" not in cleaned
    assert "Ok I'm going to" not in cleaned
    assert "Sentence 1:" not in cleaned
    assert "Thus we can make" not in cleaned
    assert "본 절에서는 캘리포니아 주의 드론 산업 생태계 현황을 심층 분석함." in cleaned
    assert "#### 1. 주요 현황 및 팩트 분석 심층 분석" in cleaned


def test_strip_australia_prompt_and_degeneration():
    sample = """### 1. 개요 및 기초 현황 분석

Here are the key things to work with: ...}
Let's list the relevant parts from the prompt:
YY Y the and and Y the and y Y Y Y expanding.
확장사 (, Exp비 July, (,,- bu=-YYY\ufffd y.Y.Y
., yy th y Y1 Y Yyy1. y . ymeans y Th YYy Y1 1 . ysthth th. y y th Y
1.  **Analyze User Input:**
- Role: Chief Researcher at a top Korean state research institute (KDI, STEPI, ETRI, KIET, KISTEP).
- Rules: 4 major principles (single report cohesion, no individual refs/abbreviations).
- Overall Topic: UAV Industry Activation for Global Certification Standards & Tech Trends (Australia focus)
- Must start with `### 1) UAS 산업·기술 정의 체계화 및 핵심 지표 현황 분석`
2.  **Deconstruct the Task:**
- I need to output a section of a report.

#### 1. 호주 중심 글로벌 인증 표준 선도 사례

호주 민간항공안전국(CASA)은 무인기 운용 규제 프레임워크를 선제적으로 구축하였다.
"""
    cleaned = strip_cot_and_system_residue(sample)
    assert "Here are the key things" not in cleaned
    assert "Analyze User Input" not in cleaned
    assert "Role: Chief Researcher" not in cleaned
    assert "Rules: 4 major" not in cleaned
    assert "Deconstruct the Task" not in cleaned
    assert "YY Y the" not in cleaned
    assert "확장사" not in cleaned
    assert "\ufffd" not in cleaned
    assert "#### 1. 호주 중심 글로벌 인증 표준 선도 사례" in cleaned
    assert "호주 민간항공안전국(CASA)은" in cleaned


def test_fix_broken_words_and_headings():
    sample = """#### 1. \ufffd글로벌 UAV 인증 체계 전환과 국가적 대응 당위성 분석

1. **버지니아 주 맞\ufffd형 시장진입 패키지 구축**
- 세부적인 맞\ufffd형 전략을 수립하여 제공함.
"""
    cleaned = strip_cot_and_system_residue(sample)
    assert "#### 1. 글로벌 UAV 인증 체계" in cleaned
    assert "\ufffd" not in cleaned
    assert "맞춤형 시장진입 패키지 구축" in cleaned
    assert "맞춤형 전략을 수립하여" in cleaned
