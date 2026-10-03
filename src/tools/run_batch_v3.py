"""Batch runner for v3 deep purge across all 12 reports.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.apply_deep_purge_v3 import process_report_v3

REPORT_PAIRS = [
    ("유타_주_내_국내기업_진출_가이드라인_p5_final_v5.md", "유타_주_내_국내기업_진출_가이드라인_p5_final_v6.md"),
    ("버지니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md", "버지니아_주_내_국내기업_진출_가이드라인_p5_final_v4.md"),
    ("콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v2.md", "콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v3.md"),
    ("텍사스_주_내_국내기업_진출_가이드라인_p5_final_v2.md", "텍사스_주_내_국내기업_진출_가이드라인_p5_final_v3.md"),
    ("캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v2.md", "캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v3.md"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v2.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v3.md"),
    ("변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v2.md", "변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v3.md"),
]

def main():
    report_dir = Path("workspace/report")
    results = []

    print("==========================================================================================")
    print("STARTING V3 COMPREHENSIVE DEEP PURGE BATCH EXECUTION")
    print("==========================================================================================")

    for src_name, dest_name in REPORT_PAIRS:
        src_path = report_dir / src_name
        dest_path = report_dir / dest_name
        print(f"\n>>> Processing: {src_name} -> {dest_name}")
        if not src_path.exists():
            print(f"ERROR: Source file {src_name} not found!")
            continue

        res = process_report_v3(src_path, dest_path)
        results.append(res)
        print(f"    Tables: Body={res['body_tables']} / TOC={res['toc_tables']} (Dups={res['t_dups']})")
        print(f"    Figures: Body={res['body_figs']} / TOC={res['toc_figs']} (Dups={res['f_dups']})")
        print(f"    Cross-refs reconciled: {res['ref_changes']}")
        print(f"    Prohibited counts: PhysCtr={res['c_phys_ctr']}, Draft={res['c_draft']}, KURA={res['c_kura']}, RAMSProj={res['c_rams_proj']}, Artifacts={res['c_artifacts']}")

    print("\n==========================================================================================")
    print("FINAL AUDIT SUMMARY TABLE (V3)")
    print("==========================================================================================")
    print(f"{'Report Name':<35} | {'Tables':<9} | {'Figs':<9} | {'Draft':<5} | {'Ctr':<5} | {'KURA':<5} | {'Proj':<5} | {'RegexArt':<8}")
    print("-" * 95)
    for r in results:
        short_name = r['dest'][:34]
        tbl_match = f"{r['body_tables']}/{r['toc_tables']}"
        fig_match = f"{r['body_figs']}/{r['toc_figs']}"
        print(f"{short_name:<35} | {tbl_match:<9} | {fig_match:<9} | {r['c_draft']:<5} | {r['c_phys_ctr']:<5} | {r['c_kura']:<5} | {r['c_rams_proj']:<5} | {r['c_artifacts']:<8}")

if __name__ == "__main__":
    main()
