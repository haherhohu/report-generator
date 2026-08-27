import os
import yaml
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from src.utils.model_client import build_llm
from src.utils.parser import extract_text_smartly
from dotenv import load_dotenv

load_dotenv()

def summarize_heavy_references():
    print("--- [Pre-processing] 타 기관 보고서 요약 파이프라인 가동 ---")
    
    raw_dir = "workspace/raw_refs"
    summary_dir = "workspace/source/summary"
    os.makedirs(summary_dir, exist_ok=True)
    
    # 모델 세팅 (저렴하고 빠른 모델 권장)
    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    llm = build_llm(agent_name="researcher", agent_config=config.get("researcher", {}))
    
    # 긴 PDF를 소화하기 위한 청크 분할기 설정
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=15000, chunk_overlap=1000)
    
    for filename in os.listdir(raw_dir):
        if not filename.endswith(".pdf"):
            continue
            
        file_path = os.path.join(raw_dir, filename)
        print(f"  -> [진행 중] {filename} 분석 시작...")
        
        try:
            # 1. PDF 로드 및 텍스트 분할
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            full_text = "\n".join([doc.page_content for doc in docs])
            chunks = text_splitter.split_text(full_text)
            
            # 2. 청크별 핵심 팩트 추출 프롬프트
            prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 전문 리서처입니다. 제공된 방대한 보고서 원문을 읽고 다음 원칙에 따라 핵심만 발췌하십시오.
                1. 서론, 인사말, 불필요한 배경 설명은 모두 버리십시오.
                2. 규정, 수치, 예산, 기관명, 기술 사양(예: 통신 주파수, 레이더 스펙) 등 '팩트'만 남기십시오.
                3. 마크다운 개조식 및 표(Table) 형태로 압축하여 출력하십시오."""),
                ("human", "문서 내용의 일부입니다:\n\n{text}")
            ])
            
            summaries = []
            for i, chunk in enumerate(chunks):
                print(f"      - Chunk {i+1}/{len(chunks)} 요약 중...")
                response = (prompt | llm).invoke({"text": chunk})
                clean_text = extract_text_smartly(response.content)
                summaries.append(clean_text)
                
            # 3. 요약본 파일 저장
            final_summary = f"# {filename} 핵심 요약본\n\n" + "\n\n---\n\n".join(summaries)
            save_name = filename.replace(".pdf", "_summary.md")
            save_path = os.path.join(summary_dir, save_name)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(final_summary)
                
            print(f"  -> [완료] {save_name} 저장 완료 (용량 대폭 감소)\n")
            
        except Exception as e:
            print(f"  -> [에러] {filename} 처리 실패: {e}\n")

if __name__ == '__main__':
    summarize_heavy_references()