"""Batch verification and HWPX export runner for all works/ documents."""
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

from src.graph.verifier_graph import StandaloneVerifier
from src.utils.file_manager import resolve_existing_path


def main():
    works_dir = Path("works")
    if not works_dir.exists():
        print("❌ works 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)

    files = sorted(works_dir.glob("*.md"))
    print(f"=======================================================")
    print(f"🚀 works 디렉터리 보고서 일괄 검증 및 HWPX 변환 (총 {len(files)}개)")
    print(f"=======================================================\n")

    verifier = StandaloneVerifier({"verifier": {"mock_mode": True}})
    results = []
    total_start = time.time()

    for idx, f in enumerate(files, 1):
        nfc_name = unicodedata.normalize("NFC", f.name)
        stem = unicodedata.normalize("NFC", f.stem)
        clean_topic = re.sub(r"_(?:p\d+|v\d+|final|verified|최종본)+.*$", "", stem)

        # Check existing final files
        report_dir = Path("workspace/report")
        existing_mds = sorted(report_dir.glob(f"{clean_topic}_p5_final_v*.md"))
        existing_hwpxs = sorted(report_dir.glob(f"{clean_topic}_p5_final_v*.hwpx"))

        # If already verified (e.g. Utah v4, Texas v1, UK v1, NATO v1), check if we can reuse or need to run
        # If both MD and HWPX exist and were recently created with latest pipeline, we can keep or re-verify
        # Let's re-run only if not already having both valid MD and HWPX
        should_run = True
        if existing_mds and existing_hwpxs:
            latest_md = existing_mds[-1]
            latest_hwpx = existing_hwpxs[-1]
            # Check if matching version
            if latest_md.stem == latest_hwpx.stem:
                # Valid pair exists!
                should_run = False
                print(f"[{idx}/{len(files)}] ⏩ 이미 검증 및 HWPX 변환 완료: {clean_topic} ({latest_hwpx.name})")
                results.append({
                    "file": nfc_name,
                    "topic": clean_topic,
                    "status": "ALREADY_DONE",
                    "output_md": str(latest_md),
                    "output_hwpx": str(latest_hwpx),
                    "orig_chars": f.stat().st_size,
                    "final_chars": latest_md.stat().st_size,
                    "elapsed": 0.0,
                })

        if should_run:
            print(f"[{idx}/{len(files)}] ⏳ 검증 착수: {nfc_name} ({f.stat().st_size / 1024:.1f} KB)...")
            t0 = time.time()
            try:
                res = verifier.verify_document(input_path=str(f))
                elapsed = time.time() - t0
                out_md = res["output_path"]
                out_hwpx = res.get("hwpx_path")
                print(f"    ✅ 성공 ({elapsed:.1f}초): {Path(out_md).name} / {Path(out_hwpx).name if out_hwpx else 'None'}")
                results.append({
                    "file": nfc_name,
                    "topic": clean_topic,
                    "status": "SUCCESS",
                    "output_md": out_md,
                    "output_hwpx": out_hwpx,
                    "orig_chars": res["original_length"],
                    "final_chars": res["final_length"],
                    "chunks": res["total_chunks"],
                    "elapsed": elapsed,
                })
            except Exception as e:
                print(f"    ❌ 실패: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "file": nfc_name,
                    "topic": clean_topic,
                    "status": "FAIL",
                    "error": str(e),
                })

    total_elapsed = time.time() - total_start
    print(f"\n=======================================================")
    print(f"🎉 일괄 검증 및 HWPX 변환 완료 (총 소요시간: {total_elapsed:.1f}초)")
    print(f"=======================================================\n")

    header = f"{'번호':^4} | {'주제':^35} | {'상태':^8} | {'MD 파일':^40} | {'HWPX 파일':^40}"
    print(header)
    print("-" * len(header))
    for i, r in enumerate(results, 1):
        status_sym = "✅" if r["status"] in ("SUCCESS", "ALREADY_DONE") else "❌"
        md_name = Path(r["output_md"]).name if r.get("output_md") else "-"
        hwpx_name = Path(r["output_hwpx"]).name if r.get("output_hwpx") else "-"
        print(f"{i:^4} | {r['topic'][:35]:<35} | {status_sym} {r['status']:<6} | {md_name:<40} | {hwpx_name:<40}")


if __name__ == "__main__":
    main()
