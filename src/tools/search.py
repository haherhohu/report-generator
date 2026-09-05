"""Web search tools for market trends and overseas policy research."""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("report_generator.tools.search")

def perform_market_research(query: str, max_results: int = 3) -> str:
    """시장 및 트렌드 조사를 위한 일반 웹 검색."""
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        tool = DuckDuckGoSearchResults(num_results=max_results)
        return tool.invoke(query)
    except Exception as e:
        logger.warning(f"DuckDuckGo 일반 검색 실패: {e}")
        return f"[{query}] 관련 시장 동향 데이터베이스 검색 결과 확보 대기 중."


def perform_hybrid_research(query: str, max_results: int = 3) -> str:
    """일반 동향 검색과 해외 공공/정책 타겟팅(site:.gov OR ...) 검색을 병합."""
    general_res = perform_market_research(query, max_results=max_results)
    time.sleep(0.5)

    trusted_domains = "(site:.gov OR site:.mil OR site:.europa.eu OR site:.org)"
    policy_query = f"{query} {trusted_domains} filetype:pdf"

    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        tool = DuckDuckGoSearchResults(num_results=max_results)
        policy_res = tool.invoke(policy_query)
    except Exception as e:
        logger.warning(f"공공/정책 심층 검색 실패: {e}")
        policy_res = "공공 정책 문서 검색 결과 확보 대기 중."

    return (
        f"--- [일반 웹 검색 결과 (시장/산업 동향)] ---\n{general_res}\n\n"
        f"--- [해외 공공/정책 공식 문서 결과 (팩트/규정)] ---\n{policy_res}"
    )

