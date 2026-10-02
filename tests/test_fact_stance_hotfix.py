"""Unit tests for the 5 Fact vs. Stance Hotfix Rules:
1. Rule 1: Purge/realign RAMS hallucinations & unestablished project claims.
2. Rule 2: Purge aerospace code development & prompt engineering guidelines.
3. Rule 3: Purge launch vehicle advocacy & slvc_report, reground in FAA/MITRE/NIST.
4. Rule 4: Purge leaked internal reference metadata ('참고자료', '이사님 제안서', etc.).
5. Rule 5: Correct '자체 분석' / '자체 연구결과' to objective survey terms.
"""
from __future__ import annotations

import re
from src.tools.fact_stance_hotfix import (
    clean_code_and_prompt_engineering,
    clean_launch_vehicle_and_slvc,
    clean_internal_reference_meta,
    clean_rams_hallucinations,
    clean_self_research_claims,
    clean_fact_stance_all,
)


def test_rule1_rams_hallucinations():
    sample = """
국내에서 추진 중인 'Physical AI 기반 UAS RAMS 시험·평가센터' 구축안(별첨 참고자료)과 유타 주의 기존 인프라(USU CAL, NIAR 유타 분원 등)를 연계할 경우 큰 효과가 기대된다.
둘째, 'Physical AI 기반 RAMS 시험평가센터'의 국내 선구축은 선택이 아닌 생존 필수 조건이다.
새만금/Physical AI 기반 RAMS 시험·평가센터 구축(안) 사업이 진행되고 있다.
"""
    cleaned, count = clean_rams_hallucinations(sample)
    assert count >= 3
    assert "별첨 참고자료" not in cleaned
    assert "생존 필수 조건이다" not in cleaned
    assert "향후 중장기 정책 과제" in cleaned
    assert "새만금/Physical AI 기반 RAMS" not in cleaned


def test_rule2_code_and_prompt_engineering():
    sample = """
- **소프트웨어 품질:** 항공우주 코드 개발 및 품질 관리에서의 AI 활용 방안 v6.2 준수.
- **프롬프트 관리:** 코드 개발 프롬프트 개발 원칙 및 프롬프트 보안 가이드 준수.
| AI 활용 코드 개발 보안 가이드라인(REQ01~04) 준수 여부 | 통과 |
"""
    cleaned, count = clean_code_and_prompt_engineering(sample)
    assert count >= 3
    assert "항공우주 코드 개발" not in cleaned
    assert "코드 개발 프롬프트" not in cleaned
    assert "REQ01~04" not in cleaned
    assert "DO-178C" in cleaned or "비행제어 소프트웨어" in cleaned


def test_rule3_launch_vehicle_and_slvc():
    sample = """
본 사업은 발사체 기술 사업화 센터 조기 안착 방안 (참조: slvc_report_v4.1)의 원칙을 차용한다.
해당 규정은 14 CFR Part 400-460 (상업용 우주 운송) 체계를 준용하며,
디지털 트윈 시험평가는 사이버 신뢰(Cyber Trust) 기반 디지털 시험평가 체계와 동일 선상에서 이뤄진다.
"""
    cleaned, count = clean_launch_vehicle_and_slvc(sample)
    assert count >= 3
    assert "slvc_report" not in cleaned
    assert "발사체 기술 사업화 센터" not in cleaned
    assert "Part 400-460" not in cleaned
    assert "Part 135" in cleaned or "Part 89" in cleaned
    assert "NIST SP 800-171" in cleaned or "MITRE" in cleaned


def test_rule4_internal_reference_meta():
    sample = """
참조 자료(이사님 한국형 드론혁신획득체계 제안서)에서 지적되었듯, 미국 시장 진입 장벽은 높다.
20260817\\이사님 한국형 드론혁신획득체계 문건에 명시된 바와 같이 기술 보호가 요구된다.
※ 자료: 참고 데이터 [1]~[6] 실증 분석 결과 재구성
비고 (참고 데이터 연계성)
"""
    cleaned, count = clean_internal_reference_meta(sample)
    assert count >= 3
    assert "이사님" not in cleaned
    assert "20260817" not in cleaned
    assert "참고 데이터 [1]~[6]" not in cleaned
    assert "비고 (참고 데이터 연계성)" not in cleaned
    assert "공식 원천 통계" in cleaned or "국내 무인기 산업 실태" in cleaned


def test_rule5_self_research_claims():
    sample = """
※ 자료: 자체 실증분석(2024) 및 인터뷰 종합
자체 분석 결과에 따르면, 국내 기업의 대미 수출 비중은 12%에 불과하다.
본 연구팀의 자체 분석에서 도출된 세부 지표는 다음과 같다.
자체 연구결과를 토대로 제언한다.
"""
    cleaned, count = clean_self_research_claims(sample)
    assert count >= 4
    assert "자체 실증분석" not in cleaned
    assert "자체 분석 결과" not in cleaned
    assert "본 연구팀의 자체 분석" not in cleaned
    assert "자체 연구결과" not in cleaned
    assert "산업 실태 및 시장 분석 결과" in cleaned
    assert "공식 조사 분석 결과" in cleaned


def test_clean_fact_stance_all_integration():
    sample = """
# 통합 테스트 문서

참조 자료(이사님 한국형 드론혁신획득체계 제안서)에서 지적되었듯, 자체 분석 결과 유타 주 진출이 유망하다.
또한 항공우주 코드 개발 및 품질 관리에서의 AI 활용 방안과 발사체 기술 사업화 센터 조기 안착 방안 (참조: slvc_report_v4.1)을 고려할 때,
새만금/Physical AI 기반 RAMS 시험·평가센터 구축(안)과 연계해야 한다.
"""
    cleaned, stats = clean_fact_stance_all(sample)

    assert stats["code_prompt_purged"] > 0
    assert stats["launch_vehicle_purged"] > 0
    assert stats["internal_meta_purged"] > 0
    assert stats["rams_hallucinations_realigned"] > 0
    assert stats["self_research_claims_corrected"] > 0

    # Ensure none of the forbidden phrases leak through
    for forbidden in [
        "이사님",
        "항공우주 코드 개발",
        "slvc_report",
        "발사체 기술 사업화 센터",
        "새만금/Physical AI",
        "자체 분석 결과",
    ]:
        assert forbidden not in cleaned, f"Forbidden term '{forbidden}' leaked into cleaned output"


if __name__ == "__main__":
    test_rule1_rams_hallucinations()
    test_rule2_code_and_prompt_engineering()
    test_rule3_launch_vehicle_and_slvc()
    test_rule4_internal_reference_meta()
    test_rule5_self_research_claims()
    test_clean_fact_stance_all_integration()
    print("ALL 6 FACT VS. STANCE HOTFIX TESTS PASSED!")
