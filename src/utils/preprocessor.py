import os
import yaml
from langchain_community.document_loaders import PyPDFLoader, BSHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from src.utils.model_client import build_llm
from src.utils.parser import extract_text_smartly
from src.utils.prompting import trim_prompt_context, estimate_context_budget

def run_preprocessing(raw_dir="workspace/raw_refs", summary_dir="workspace/source/summary"):
    """
    파이프라인 가동 전, 무거운 PDF와 HTML 파일을 가벼운 마크다운 팩트 시트로 요약합니다.
    """
    if not os.path.exists(raw_dir):
        return # 원본 폴더가 없으면 조용히 패스

    os.makedirs(summary_dir, exist_ok=True)
    files_to_process = [f for f in os.listdir(raw_dir) if f.lower().endswith((".pdf", ".html", ".htm"))]

    if not files_to_process:
        return

    print("  [System] 타 기관 보고서(PDF/HTML) 인라인 자동 요약 가동...")
    
    with open("config/agents_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    # 요약 작업은 속도가 중요하므로 meta/llama-3.1-8b-instruct 등 경량 모델 사용
    researcher_config = config.get("researcher", {})
    llm = build_llm(agent_name="researcher", 
                    agent_config=researcher_config,
                    default_model=researcher_config.get("model", "meta/llama-3.1-8b-instruct"), # config에서 가져오거나 기본값 지정
                    temperature=0.0 # 요약 작업이므로 환각 방지를 위해 온도를 0으로 고정
    )
    max_input_tokens = int(researcher_config.get("max_input_tokens", 12000))
    chunk_size = max(4000, min(16000, estimate_context_budget(max_input_tokens, default=12000) // 2))
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=max(250, chunk_size // 12))

    for filename in files_to_process:
        file_path = os.path.join(raw_dir, filename)
        save_name = filename.rsplit('.', 1)[0] + "_summary.md"
        save_path = os.path.join(summary_dir, save_name)

        # 이미 요약된 파일이 있으면 비용 절감을 위해 건너뜀
        if os.path.exists(save_path):
            print(f"    -> [패스] {save_name} (이미 요약됨)")
            continue

        print(f"    -> [진행 중] {filename} 분석 및 팩트 추출 시작...")
        try:
            # 확장자에 따른 로더 분기 처리
            if filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            else:
                loader = BSHTMLLoader(file_path) # HTML 태그를 벗겨내고 순수 텍스트만 추출
                
            docs = loader.load()
            full_text = "\n".join([doc.page_content for doc in docs])
            chunks = text_splitter.split_text(full_text)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "당신은 전문 리서처입니다. 서론/인사말을 제외하고 규정, 수치, 예산, 기관명, 기술 사양 등 팩트만 발췌하여 마크다운 개조식으로 요약하시오. 절대 내용을 지어내지 마시오."),
                ("human", "문서 내용:\n\n{text}")
            ])
            
            summaries = []
            for i, chunk in enumerate(chunks):
                safe_chunk = trim_prompt_context(
                    chunk,
                    max_chars=max(3000, chunk_size * 2),
                    required_fragments=[
                        "규정",
                        "예산",
                        "기관명",
                        "수치",
                        "기술 사양",
                    ],
                )
                response = (prompt | llm).invoke({"text": safe_chunk})
                clean_text = extract_text_smartly(response.content)
                summaries.append(clean_text)
                
            final_summary = f"# {filename} 핵심 요약본\n\n" + "\n\n---\n\n".join(summaries)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(final_summary)
                
            print(f"    -> [완료] {save_name} 저장 완료")
            
        except Exception as e:
            print(f"    -> [에러] {filename} 처리 실패: {e}")