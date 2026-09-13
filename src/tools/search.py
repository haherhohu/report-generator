"""Web search tools for market trends and overseas policy research with SSL resilience."""
from __future__ import annotations

import logging
import os
import time
from typing import Any
import certifi

# macOS Python SSL 인증서 번들 경로 강제 적용 (SSL: CERTIFICATE_VERIFY_FAILED 해결)
if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()
if "REQUESTS_CA_BUNDLE" not in os.environ:
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

logger = logging.getLogger("report_generator.tools.search")


def _execute_ddgs_query(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """SSL 오류 및 차단에 견고한 다단계 DuckDuckGo 검색."""
    # 1순위: certifi 명시적 CA 인증서 검증
    try:
        from ddgs import DDGS
        with DDGS(verify=certifi.where(), timeout=8) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if results:
                return results
    except Exception as e:
        logger.debug(f"DDGS certifi search failed ({e}), trying unverified...")

    # 2순위: SSL 검증 우회 (자체 서명 프록시, 로컬 백신/방화벽 SSL 인터셉션, 루트 인증서 누락 대응)
    try:
        from ddgs import DDGS
        with DDGS(verify=False, timeout=8) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if results:
                return results
    except Exception as e:
        logger.debug(f"DDGS unverified search failed ({e}), trying langchain wrapper...")

    # 3순위: LangChain Community 검색 툴 폴백
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        tool = DuckDuckGoSearchResults(num_results=max_results)
        raw = tool.invoke(query)
        if raw and "No good DuckDuckGo" not in raw:
            return [{"title": f"[{query}] 동향 검색", "href": "", "body": raw}]
    except Exception as e:
        logger.debug(f"Langchain DDG search failed ({e})")

    return []


def perform_hybrid_research_structured(query: str, max_results: int = 3) -> dict[str, Any]:
    """일반 동향 검색과 공공/정책 타겟팅 검색을 병합하여 구조화된 원본 레코드 및 텍스트 반환."""
    records: list[dict[str, Any]] = []

    # 1. 일반 시장/산업 동향 검색
    general_items = _execute_ddgs_query(query, max_results=max_results)
    for it in general_items:
        records.append({
            "title": it.get("title") or f"{query} 동향",
            "href": it.get("href") or "",
            "snippet": it.get("body") or it.get("snippet") or "",
            "source_type": "market_web",
        })

    time.sleep(0.3)

    # 2. 해외 공공/정책 타겟팅 검색
    trusted_domains = "(site:.gov OR site:.mil OR site:.europa.eu OR site:.org)"
    policy_query = f"{query} {trusted_domains} filetype:pdf"
    policy_items = _execute_ddgs_query(policy_query, max_results=max_results)
    for it in policy_items:
        records.append({
            "title": it.get("title") or f"{query} 공공 규정/정책",
            "href": it.get("href") or "",
            "snippet": it.get("body") or it.get("snippet") or "",
            "source_type": "policy_pdf",
        })

    # 중복 제거 (URL 기준 또는 제목 기준)
    seen_urls = set()
    unique_records = []
    for r in records:
        key = r.get("href") or r.get("title")
        if key and key not in seen_urls:
            seen_urls.add(key)
            unique_records.append(r)

    if not unique_records:
        logger.warning(f"[Search] '{query}' 실제 검색 결과 0건 (네트워크 차단, API 제한 또는 일치 데이터 부재).")
        return {
            "has_results": False,
            "records": [],
            "context_text": "",
        }

    # 포맷팅된 컨텍스트 텍스트 생성
    formatted_parts = []
    for i, r in enumerate(unique_records, 1):
        t = r["title"]
        h = r["href"]
        s = r["snippet"]
        link = f" ({h})" if h else ""
        formatted_parts.append(f"[{i}] **{t}**{link}\n{s}")

    context_text = "\n\n".join(formatted_parts)
    return {
        "has_results": True,
        "records": unique_records,
        "context_text": context_text,
    }


def perform_market_research(query: str, max_results: int = 3) -> str:
    """하위 호환성을 위한 일반 시장 검색."""
    results = _execute_ddgs_query(query, max_results=max_results)
    if results:
        formatted_list = []
        for i, r in enumerate(results, 1):
            title = r.get("title", f"출처 {i}")
            href = r.get("href", "")
            body = r.get("body") or r.get("snippet") or ""
            link_str = f" ({href})" if href else ""
            formatted_list.append(f"- **{title}**{link_str}\n  {body}")
        return "\n\n".join(formatted_list)
    return ""


def perform_hybrid_research(query: str, max_results: int = 3) -> str:
    """하위 호환성을 위한 문자열 기반 하이브리드 검색."""
    res = perform_hybrid_research_structured(query, max_results=max_results)
    if res["has_results"]:
        return res["context_text"]
    return ""



