import os
import argparse
from pathlib import Path
import yaml
from src.graph.workflow import app
from langchain_community.document_loaders import PyPDFLoader
from pypdf import PdfReader

from src.utils.preprocessor import run_preprocessing

DEFAULT_PIPELINE_SETTINGS = {
    "max_loops": 2,
    "max_concurrency": 5,
    "target_6_min_length": 3000,
    "target_total_min_length": 50000,
}


def _read_text_with_fallback(file_path: Path) -> str:
    """UTF-8 우선, 실패 시 일반적인 한글 인코딩을 순차 시도합니다."""
    candidate_encodings = ("utf-8", "utf-8-sig", "cp949", "euc-kr")
    last_error = None

    for encoding in candidate_encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(
        f"{file_path} 파일을 디코딩할 수 없습니다. 시도한 인코딩: {candidate_encodings}. 마지막 오류: {last_error}"
    ) from last_error

def load_source_materials(source_dir):
    """지정된 디렉터리에서 기초 자료(.md, .txt, .pdf)를 읽어옵니다."""
    materials = []
    if os.path.exists(source_dir):
        for filename in os.listdir(source_dir):
            file_path = os.path.join(source_dir, filename)
            
            # 마크다운 및 텍스트 파일 처리
            if filename.endswith(".md") or filename.endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    materials.append({"filename": filename, "content": f.read()})

            # PDF 파일 처리 로직 수정안
            # PDF 파일 처리 로직 (스킵 방어 로직 추가)
            elif filename.endswith(".pdf"):
                try:
                    # 1차 방어: 전체 페이지 수 확인
                    # 1. 파일 전체 파싱 전, 메타데이터로 페이지 수만 0.1초 만에 확인
                    reader = PdfReader(file_path)
                    total_pages = len(reader.pages)
                    
                    # 2. 50페이지(원하시는 기준치) 초과 시 무조건 스킵
                    MAX_ALLOWED_PAGES = 50
                    if total_pages > MAX_ALLOWED_PAGES:
                        print(f"    [Skip] {filename} (PDF): 총 {total_pages}페이지. 대형 문서({MAX_ALLOWED_PAGES}p 초과)는 파이프라인 지연 방지를 위해 제외합니다.")
                        continue
                        
                    # 3. 기준치 이하의 정상 문서만 무거운 PyPDFLoader로 텍스트 추출
                    loader = PyPDFLoader(file_path)
                    pages = loader.load()
                    pdf_text = "\n".join([page.page_content for page in pages])
                    
                    # --- [PATCH] PDF 강제 다이어트 로직 ---
                    # 2차 방어: 지정된 텍스트 길이를 초과하면 강제 절삭
                    # (만약을 대비한 2차 글자 수 방어선 유지)
                    max_chars_limit = 15000  # 약 1만 토큰 제한 방어선
                    if len(pdf_text) > max_chars_limit:
                        pdf_text = pdf_text[:max_chars_limit] + "\n\n... [시스템 개입: 문서 분량 초과로 이하 생략됨] ..."

                    # 페이지별 텍스트를 하나로 병합                    
                    materials.append({"filename": filename, "content": pdf_text})
                    print(f"    [System] {filename} (PDF) 로드 성공. (총 {len(pages)}페이지)")
                    # ------------------------------------
                except Exception as e:
                    print(f"    [Error] {filename} PDF 읽기/스킵 실패: {e}")
                    
    return materials

def _extract_front_matter(markdown_text: str) -> dict:
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("MD 상태 파일은 YAML front matter(--- ... ---)를 포함해야 합니다.")

    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    if end_index is None:
        raise ValueError("MD 상태 파일의 YAML front matter 종료 구분자(---)를 찾지 못했습니다.")

    front_matter_text = "\n".join(lines[1:end_index])
    data = yaml.safe_load(front_matter_text) or {}
    if not isinstance(data, dict):
        raise ValueError("MD front matter는 key-value 형태의 YAML이어야 합니다.")
    return data


def load_initial_state_file(path: str) -> dict:
    state_path = Path(path)
    if not state_path.exists():
        raise FileNotFoundError(f"초기 상태 파일을 찾을 수 없습니다: {state_path}")

    raw_text = _read_text_with_fallback(state_path)
    suffix = state_path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(raw_text) or {}
    elif suffix == ".md":
        loaded = _extract_front_matter(raw_text)
    else:
        raise ValueError("초기 상태 파일은 .yaml/.yml 또는 .md만 지원합니다.")

    if not isinstance(loaded, dict):
        raise ValueError("초기 상태 파일은 key-value 형태여야 합니다.")

    required_fields = ("topic", "direction", "target_perspective")
    missing = [field for field in required_fields if not loaded.get(field)]
    if missing:
        raise ValueError(f"초기 상태 파일 필수 필드 누락: {missing}")

    return loaded


def load_pipeline_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_PIPELINE_SETTINGS.copy()

    loaded = yaml.safe_load(_read_text_with_fallback(config_path)) or {}
    if not isinstance(loaded, dict):
        raise ValueError("pipeline_config 파일은 key-value 형태의 YAML이어야 합니다.")

    merged = DEFAULT_PIPELINE_SETTINGS.copy()
    merged.update(loaded)
    return merged


def main():
    parser = argparse.ArgumentParser(description="Report Generator Pipeline Runner")
    parser.add_argument(
        "--thread-id",
        default="default-session",
        help="LangGraph 체크포인트 식별자. 같은 ID로 재실행 시 이어서 재개 가능",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="같은 thread-id의 마지막 실패/중단 지점부터 재개",
    )
    parser.add_argument(
        "--state-file",
        default="config/initial_state.yaml",
        help="초기 상태 파일 경로 (.yaml/.yml 또는 YAML front matter 포함 .md)",
    )
    parser.add_argument(
        "--pipeline-config",
        default="config/pipeline_config.yaml",
        help="파이프라인 전역 설정 파일 경로 (.yaml/.yml)",
    )
    args = parser.parse_args()

    print('--- Report Generator Pipeline 가동 ---')

    # 0. 메인 파이프라인 시작 전, 무거운 원문(PDF/HTML) 자동 요약 처리
    run_preprocessing(raw_dir="workspace/raw_refs", summary_dir="workspace/source/summary")

    # 1. 파일 스캔 및 모드 판별
    # 1.1. 코어 방향성 파일만 주입 (Drafter 용)
    core_materials = load_source_materials("workspace/source/core")
    
    # 1.2. 요약된 레퍼런스 주입 (Expander/Researcher 용)
    summary_materials = load_source_materials("workspace/source/summary")
    is_blank_slate = (len(core_materials) == 0)

    # 2. 초기 상태(State) 로드 및 관점 설정
    if args.resume:
        initial_state = {}
    else:
        pipeline_config = load_pipeline_config(args.pipeline_config)
        initial_state = load_initial_state_file(args.state_file)
        # Drafter가 분석할 핵심 초안
        initial_state["source_materials"] = core_materials
        # 후속 에이전트들이 참고할 가벼운 팩트 시트 모음
        initial_state["reference_summaries"] = summary_materials
        initial_state["is_blank_slate"] = is_blank_slate
        initial_state.setdefault("keywords", [])
        initial_state.setdefault("loop_count", 0)
        initial_state.setdefault("max_loops", pipeline_config["max_loops"])
        initial_state.setdefault("max_concurrency", pipeline_config["max_concurrency"])
        initial_state.setdefault("target_6_min_length", pipeline_config["target_6_min_length"])
        initial_state.setdefault("target_total_min_length", pipeline_config["target_total_min_length"])

        # --- [PATCH] 워커 강제 확장(Expansion) 행동 강령 주입 ---
        initial_state["global_directive"] = (
            "당신에게 제공되는 자료는 완성본이 아닌 '초안(Bullet points)'입니다. "
            "단순 요약이나 병합을 엄격히 금지합니다. 이 핵심 요약을 바탕으로 관련된 배경지식과 "
            "논리적 인과관계를 스스로 추론하여 최소 3문단 이상의 구체적인 '서술형(Descriptive) 세부 보고서'로 "
            "반드시 확장(Expand)하여 작성하십시오. 마크다운 리스트만 나열하는 것을 금지합니다."
        )
        
        print(f"[시스템] 상태 파일: {args.state_file}")
        print(f"[시스템] 상태 파일: {args.state_file}")
        print(f"[시스템] 파이프라인 설정 파일: {args.pipeline_config}")
        print(f"[시스템] 백지 모드: {is_blank_slate} / 로드된 기초 자료: {len(core_materials)}건")
        print(f"[시스템] 타겟 관점: {initial_state['target_perspective']}\n")
            
    # 3. 파이프라인 실행
    if not args.resume:
        print(f"주제: {initial_state['topic']}\n")

    run_config = {"configurable": {"thread_id": args.thread_id}}
    run_input = None if args.resume else initial_state
    
    # 스트리밍 방식으로 각 노드(에이전트)가 끝날 때마다 상태 출력
    try:
        for output in app.stream(run_input, config=run_config):
            for key, value in output.items():
                print(f"현재 완료된 노드: {key}")
    except Exception as exc:
        snapshot = app.get_state(run_config)
        pending_nodes = list(snapshot.next or [])
        print(f"\n[오류] 파이프라인이 중단됨: {exc}")
        print(f"[안내] 재개 명령: python main.py --thread-id {args.thread_id} --resume")
        if pending_nodes:
            print(f"[안내] 재개 예정 노드: {pending_nodes}")
        raise
            
    print('\n--- 파이프라인 실행 완료 ---')

if __name__ == '__main__':
    main()