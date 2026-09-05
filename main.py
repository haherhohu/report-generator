"""Command-line interface entry point for the Report Generator pipeline."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import yaml

from src.graph.runner import PipelineRunner
from src.tools.preprocessor import read_text_with_fallback


def extract_front_matter(markdown_text: str) -> dict:
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
        # Fallback to poc path if not found
        poc_path = Path("poc") / path
        if poc_path.exists():
            state_path = poc_path
        else:
            raise FileNotFoundError(f"초기 상태 파일을 찾을 수 없습니다: {path}")

    raw_text = read_text_with_fallback(state_path)
    suffix = state_path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(raw_text) or {}
    elif suffix == ".md":
        loaded = extract_front_matter(raw_text)
    else:
        raise ValueError("초기 상태 파일은 .yaml/.yml 또는 .md만 지원합니다.")

    if not isinstance(loaded, dict):
        raise ValueError("초기 상태 파일은 key-value 형태여야 합니다.")

    required_fields = ("topic", "direction")
    missing = [field for field in required_fields if not loaded.get(field)]
    if missing:
        raise ValueError(f"초기 상태 파일 필수 필드 누락: {missing}")

    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Agent Long-Form Report Generator")
    parser.add_argument(
        "--thread-id",
        default="default_session",
        help="LangGraph 세션 식별자 (재개 시 동일 ID 사용)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="동일 thread-id의 마지막 중단 지점부터 재개",
    )
    parser.add_argument(
        "--state-file",
        default="config/initial_state.yaml",
        help="초기 상태 파일 경로 (.yaml 또는 front-matter 포함 .md)",
    )
    parser.add_argument(
        "--pipeline-config",
        default="config/pipeline_config.yaml",
        help="파이프라인 전역 설정 파일 경로",
    )

    args = parser.parse_args()

    print("\n=======================================================")
    print("  🚀 Report Generator: 초장문 보고서 자동 생성 파이프라인")
    print("=======================================================\n")

    initial_state = {}
    if not args.resume:
        initial_state = load_initial_state_file(args.state_file)
        print(f"[시스템] 의뢰 주제: {initial_state.get('topic')}")
        print(f"[시스템] 보고서 유형: {initial_state.get('report_type', 'market_tech_trend')}")
        print(f"[시스템] 목표 분량: {initial_state.get('target_pages', 200)}페이지 ({initial_state.get('target_chars', 250000):,}자)")
        print(f"[시스템] 세션 ID: {args.thread_id}\n")
    else:
        print(f"[시스템] 세션 '{args.thread_id}' 재개 모드 가동\n")

    runner = PipelineRunner(args.pipeline_config)

    def on_progress(node_name: str, node_state: dict):
        print(f"  [✓] 노드 완료: {node_name}")
        if node_name == "merger" and node_state.get("final_report_path"):
            print(f"\n🎉 [최종 완성] 보고서 저장 완료: {node_state['final_report_path']}")

    try:
        final_state = runner.run(
            initial_state=initial_state,
            thread_id=args.thread_id,
            resume=args.resume,
            progress_callback=on_progress,
        )
        print("\n=======================================================")
        print("  ✅ 파이프라인 전체 실행 완료")
        if final_state.get("final_report_path"):
            print(f"  📄 최종 보고서: {final_state['final_report_path']}")
        print("=======================================================\n")
    except Exception as exc:
        print(f"\n❌ [오류 발생] 파이프라인 중단: {exc}")
        print(f"👉 재개 명령어: python main.py --thread-id {args.thread_id} --resume\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

