"""Command-line interface entry point for the Report Generator pipeline."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import yaml
import certifi

if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()
if "REQUESTS_CA_BUNDLE" not in os.environ:
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

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
    parser = argparse.ArgumentParser(description="Multi-Agent Long-Form Report Generator v2")
    parser.add_argument(
        "--mode",
        choices=["generate", "verify", "translate"],
        default="generate",
        help="실행 모드 선택: generate(신규 보고서 생성) | verify(기존 문서 단독 검증) | translate(초장문 분할 번역)",
    )
    parser.add_argument(
        "--input-file",
        help="단독 검증(verify) 또는 번역(translate) 시 입력할 원본 파일 경로 (.md/.txt)",
    )
    parser.add_argument(
        "--output-file",
        help="검증 또는 번역 결과물을 저장할 출력 파일 경로 (생략 시 자동 명명)",
    )
    parser.add_argument(
        "--stance",
        default="",
        help="기관의 전략적 방향성 및 정책적 주장 (Stance DB) 텍스트",
    )
    parser.add_argument(
        "--source-lang",
        default="en",
        help="번역 원본 언어 (기본값: en)",
    )
    parser.add_argument(
        "--target-lang",
        default="ko",
        help="번역 대상 언어 (기본값: ko)",
    )
    parser.add_argument(
        "--glossary-file",
        help="번역 시 적용할 고정 전문용어 사전 파일 경로 (.yaml/.csv)",
    )
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
    parser.add_argument(
        "--mock",
        action="store_true",
        help="외부 API 호출 없이 고속 Mock 엔진으로 전 파이프라인 무토큰 테스트",
    )

    args = parser.parse_args()

    if args.mock:
        os.environ["MOCK_MODE"] = "true"
        print("[시스템] ⚡ 무토큰 Mock 테스트 모드 활성화 (API 쿼터 소모 0)")

    print("\n=======================================================")
    print(f"  🚀 Report Generator v2: 초장문 보고서 시스템 [모드: {args.mode.upper()}]")
    print("=======================================================\n")

    # 1. 단독 검증 모드 (Mode B)
    if args.mode == "verify":
        if not args.input_file:
            print("❌ 오류: --mode verify 실행 시 --input-file 경로가 필수입니다.")
            sys.exit(1)
        from src.graph.verifier_graph import StandaloneVerifier
        verifier = StandaloneVerifier({"verifier": {"mock_mode": args.mock}})
        print(f"[시스템] 단독 검증 착수: {args.input_file}")
        if args.stance:
            print(f"[시스템] 정책적 Stance 주입: {args.stance}")
        res = verifier.verify_document(
            input_path=args.input_file,
            output_path=args.output_file,
            strategic_stance=args.stance,
        )
        print("\n=======================================================")
        print(f"  ✅ 단독 문서 검증 및 정제 완료")
        print(f"  📄 최종 산출물(MD): {res['output_path']}")
        if res.get("hwpx_path"):
            print(f"  📑 공공 HWPX 산출물: {res['hwpx_path']}")
        print(f"  📊 분량 변화: {res['original_length']:,}자 ➔ {res['final_length']:,}자 (총 {res['total_chunks']}개 청크)")
        print("=======================================================\n")
        return

    # 2. 초장문 분할 번역 모드 (Mode C)
    if args.mode == "translate":
        if not args.input_file:
            print("❌ 오류: --mode translate 실행 시 --input-file 경로가 필수입니다.")
            sys.exit(1)
        from src.graph.translator_graph import StandaloneTranslator
        translator = StandaloneTranslator({"translator": {"mock_mode": args.mock}})
        print(f"[시스템] 초장문 분할 번역 착수: {args.input_file} ({args.source_lang} ➔ {args.target_lang})")
        res = translator.translate_document(
            input_path=args.input_file,
            output_path=args.output_file,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            custom_glossary_path=args.glossary_file,
        )
        print("\n=======================================================")
        print(f"  ✅ 초장문 분할 번역 완료")
        print(f"  📄 번역 산출물: {res['output_path']}")
        print(f"  📊 분량: 원문 {res['original_length']:,}자 ➔ 번역본 {res['final_length']:,}자")
        print("=======================================================\n")
        return

    # 3. 신규 보고서 생성 파이프라인 (Mode A)
    initial_state = {}
    if not args.resume:
        initial_state = load_initial_state_file(args.state_file)
        if args.stance:
            kc = initial_state.setdefault("knowledge_context", {})
            kc["strategic_stance"] = args.stance
        initial_state["mode"] = "generate"
        print(f"[시스템] 의뢰 주제: {initial_state.get('topic')}")
        print(f"[시스템] 보고서 유형: {initial_state.get('report_type', 'market_tech_trend')}")
        print(f"[시스템] 목표 분량: {initial_state.get('target_pages', 200)}페이지 ({initial_state.get('target_chars', 250000):,}자)")
        print(f"[시스템] 세션 ID: {args.thread_id}\n")
    else:
        print(f"[시스템] 세션 '{args.thread_id}' 재개 모드 가동\n")

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    from src.graph.runner import PipelineRunner
    runner = PipelineRunner(args.pipeline_config)

    node_descriptions = {
        "drafter": "초안 및 마스터 아웃라인 기획",
        "researcher": "키워드별 심층 웹·정책 자료조사",
        "expander": "섹션별 Sub-TOC 분할 및 본문 3단계 심층 확장",
        "reviewer": "공공 보고서 서식, 팩트 및 시사점 정합성 검증",
        "gatekeeper": "코어 70% 방어선 및 실증 분량 심사",
        "merger": "최종 마크다운 병합 및 HWPX 공공 규격 변환",
    }

    def on_progress(node_name: str, node_state: dict):
        desc = node_descriptions.get(node_name, "")
        print(f"\n✅ [단계 완료] {node_name.upper()} ({desc})", flush=True)
        if node_name == "gatekeeper":
            decision = node_state.get("gatekeeper_decision", "UNKNOWN")
            loop_count = node_state.get("loop_count", 0)
            chars = node_state.get("current_chars", 0)
            print(f"   ↳ 심사 판정: {decision} (현재 분량: {chars:,}자, 루프 회차: {loop_count}회)", flush=True)
        if node_name == "merger" and node_state.get("final_report_path"):
            print(f"\n🎉 [최종 완성] 보고서 저장 완료: {node_state['final_report_path']}\n", flush=True)

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
            print(f"  📄 최종 마크다운 보고서: {final_state['final_report_path']}")
        if final_state.get("final_hwpx_path"):
            print(f"  📑 최종 HWPX 보고서: {final_state['final_hwpx_path']}")
        print("=======================================================\n")
    except Exception as exc:
        print(f"\n❌ [오류 발생] 파이프라인 중단: {exc}")
        print(f"👉 재개 명령어: python main.py --thread-id {args.thread_id} --resume\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

