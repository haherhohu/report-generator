try:
    import pytest
    mark_asyncio = pytest.mark.asyncio
except (ImportError, AttributeError):
    pytest = None
    mark_asyncio = lambda f: f

from src.agents.verifier import (
    _apply_deterministic_rules,
    merge_factual_updates,
    verify_and_correct_chunk,
)
from src.models.client import UnifiedModelClient


def test_apply_deterministic_rules_table_unquote():
    raw_markdown = """
> **【그림 1-1】 도식화**
> - 기능: A -> B

> | 항목 | 수치 | 비고 |
> | :--- | :--- | :--- |
> | 시장규모 | 500억 | 통계 |
"""
    cleaned = _apply_deterministic_rules(raw_markdown)
    # The table syntax must NOT be prepended with > |
    assert "> |" not in cleaned
    assert "| 항목 | 수치 | 비고 |" in cleaned
    assert "| 시장규모 | 500억 | 통계 |" in cleaned


def test_apply_deterministic_rules_cliches_and_sources():
    raw_text = """
본 기술은 미래 산업의 게임 체인저로 눈부신 도약이 되어지고 있는 상황이다.
자체 분석 결과에 따르면 향후 연평균 15% 성장이 기대된다.
<think>
내부 생각 체인: 사실 여부 확인 완료
</think>
"""
    cleaned = _apply_deterministic_rules(raw_text)
    assert "게임 체인저" not in cleaned
    assert "눈부신 도약" not in cleaned
    assert "자체 분석 결과" not in cleaned
    assert "제공 기초자료 및 공인 원천 데이터셋 재구성" in cleaned
    assert "<think>" not in cleaned
    assert "내부 생각 체인" not in cleaned


def test_merge_factual_updates_inline():
    original = """## 1. 최신 기술 동향
기술 표준화가 진행 중이다.

| 구분 | 현황 |
| :--- | :--- |
| TRL | 6단계 |

### 다. 요약: 본 절의 핵심 분석 결과
본 절의 실증 데이터를 요약함.
"""
    updates = [
        "2025년 기준 글로벌 특허 출원 건수는 전년 대비 24.5% 증가하여 3,420건 기록함.",
        "미국 FAA 규제 개정안 파트 108 제정에 따라 BVLOS 비행 승인 요건 완화됨.",
    ]
    merged = merge_factual_updates(original, updates)
    assert "【심층 실증 데이터 보강】" in merged
    assert "BVLOS 비행 승인 요건 완화됨" in merged
    # Must precede the final summary
    assert merged.index("【심층 실증 데이터 보강】") < merged.index("### 다. 요약:")


@mark_asyncio
async def test_verify_and_correct_chunk_mock():
    client = UnifiedModelClient("test", {"mock_mode": True})
    content = """
> | 지표 | 수치 |
> | --- | --- |
자체 연구분석 자료에 따르면 유타주 가상 비행단지가 신설 운영 중이다.
게임 체인저로서의 가치가 높다.
"""
    res = await verify_and_correct_chunk(
        content=content,
        metadata={"title": "기술 동향", "chapter_number": "1장", "role_type": "background_trend"},
        client=client,
        strategic_stance="",
        allow_stance=False,
    )
    assert res["passed"] is True
    corrected = res["corrected_content"]
    assert "> |" not in corrected
    assert "게임 체인저" not in corrected
    assert "자체 연구분석" not in corrected
