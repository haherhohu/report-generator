import os


def _reference_to_text(reference):
    if isinstance(reference, dict):
        return str(reference.get("content", ""))
    if isinstance(reference, str):
        if os.path.exists(reference):
            with open(reference, "r", encoding="utf-8") as f:
                return f.read()
        return reference
    return str(reference)


def map_references_to_sections(sections, references, global_direction):
    """
    챕터별 성격(목적)에 맞춰 참조 자료와 프롬프트 지침을 다르게 매핑합니다.
    """
    routed_sections = []
    
    # 레퍼런스 전체 요약본 생성 (4~7장 지원용 / 실제 환경에서는 LLM 요약 모듈 활용)
    # 여기서는 단순 병합으로 가정
    normalized_refs = [_reference_to_text(ref) for ref in references if ref]
    summarized_refs = "\n".join([f"- {ref[:200]}..." for ref in normalized_refs]) 
    full_refs = "\n".join(normalized_refs)
    
    for section in sections:
        chapter_num = section.get('section_index', 0)
        
        # 1. 빌드업 및 데이터 팽창 챕터 (2장, 3장, 8장, 9장)
        if chapter_num in [2, 3, 9]:
            section['context_data'] = full_refs  # 원시 데이터 전체 주입
            section['specific_instruction'] = (
                "제공된 데이터를 빠짐없이 활용하여 구체적인 사례와 통계를 서술하시오. "
                "절대 내용을 축약하지 말고, 하위 목차를 추가하여 분량을 논리적으로 팽창시키시오."
            )

        # 8장: 통계 및 법령 부록 (엄격한 데이터 발췌)
        elif chapter_num == 8:
            section['context_data'] = full_refs  # 수집된 원시 데이터 전체 주입
            section['specific_instruction'] = (
                "제공된 참고 자료에서 '통계 수치', '예산 데이터', 'FAA 및 국내 관련 법령/규정'만을 엄격하게 발췌하시오. "
                "서술형 문장 작성을 최소화하고, 반드시 마크다운 표(Table)와 인용구(Blockquote)를 사용하여 데이터시트 형태로 정리하시오. "
                "자료에 없는 수치나 법령은 절대 지어내지 마시오."
            )            
        # 2. 코어 전략 및 실행 챕터 (4장, 5장, 6장, 7장)
        elif chapter_num in [4, 5, 6, 7]:
            section['context_data'] = summarized_refs  # 요약된 데이터만 주입
            section['specific_instruction'] = (
                f"보고서의 핵심 방향성('{global_direction}')을 최우선으로 반영하시오. "
                "제공된 요약 데이터를 뒷받침 근거로만 짧게 인용하고, "
                "실현 가능한 전략과 구체적인 세부 과제 도출에 집중하시오."
            )
            
        # 3. 서론 및 기타 (1장)
        else:
            section['context_data'] = summarized_refs
            section['specific_instruction'] = "보고서의 전체 목적과 배경을 설득력 있게 서술하시오."
            
        routed_sections.append(section)
        
    return routed_sections