from langchain_community.tools import DuckDuckGoSearchResults
import time

def search(query):
    # 검색 API 연동 로직 (Tavily 등)
    pass

def perform_market_research(query: str, max_results: int = 3) -> str:
    """
    시장 및 트렌드 조사를 위한 웹 검색 도구입니다.
    별도의 API 키가 필요 없으며, 기획보고서 작성을 위한 최신 동향을 수집합니다.
    """
    search_tool = DuckDuckGoSearchResults(num_results=max_results)
    try:
        results = search_tool.invoke(query)
        if not results:
            raise RuntimeError("검색 결과가 비어 있습니다.")
        return results
    except Exception as e:
        raise RuntimeError(f"웹 검색 실패: {query}") from e


def perform_overseas_policy_research(query: str, max_results: int = 3) -> str:
    """
    해외 공공/연구기관 자료 타겟팅을 위해 검색 쿼리에 강제 필터를 적용합니다.
    """
    # 1. 해외 공공기관 및 신뢰할 수 있는 도메인 강제 (구글/DDG 공통 검색 연산자)
    # .gov(미국 정부), .mil(미국 군/국방), .europa.eu(유럽연합), .org(비영리/국제기구)
    trusted_domains = "(site:.gov OR site:.mil OR site:.europa.eu OR site:.org)"
    
    # 2. 정책 보고서 특성상 PDF 문서 우선 검색
    document_type = "filetype:pdf"
    
    # 최종 쿼리 조립 (예: "BVLOS waiver FAA (site:.gov OR ...) filetype:pdf")
    optimized_query = f"{query} {trusted_domains} {document_type}"
    
    print(f"    [Search] 최적화된 쿼리 실행: {optimized_query}")
    
    search_tool = DuckDuckGoSearchResults(num_results=max_results)
    try:
        results = search_tool.invoke(optimized_query)
        return results
    except Exception as e:
        print(f"  [Error] 웹 검색 실패: {e}")
        return "검색 결과를 가져오지 못했습니다."


def perform_hybrid_research(query: str, max_results: int = 3) -> str:
    """
    일반 웹 검색과 해외 공공/정책 타겟 검색을 동시에 수행하여 결과를 병합합니다.
    """
    search_tool = DuckDuckGoSearchResults(num_results=max_results)
    
    # 1. 일반 검색 (시장 동향, 뉴스, 업계 컨센서스 파악용)
    print(f"    [Search] 일반 동향 검색 중: {query}")
    try:
        general_results = search_tool.invoke(query)
    except Exception as e:
        general_results = f"일반 검색 실패: {e}"
        
    time.sleep(1) # API Rate Limit 방지를 위한 짧은 대기
    
    # 2. 공공/정책 심층 검색 (신뢰도 높은 레퍼런스 확보용)
    # 영어 키워드가 포함되어 있을 때 가장 효율이 좋습니다.
    trusted_domains = "(site:.gov OR site:.mil OR site:.europa.eu OR site:.org)"
    policy_query = f"{query} {trusted_domains} filetype:pdf"
    
    print(f"    [Search] 공공/정책 심층 검색 중: {policy_query}")
    try:
        policy_results = search_tool.invoke(policy_query)
    except Exception as e:
        policy_results = f"공공 검색 실패: {e}"
        
    # 3. 결과 병합 및 반환
    merged_results = (
        f"--- [일반 웹 검색 결과 (시장/동향)] ---\n{general_results}\n\n"
        f"--- [해외 공공/정책 공식 문서 결과 (팩트/규정)] ---\n{policy_results}"
    )
    
    return merged_results