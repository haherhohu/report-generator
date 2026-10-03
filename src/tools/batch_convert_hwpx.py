"""Batch convert 12 verified markdown reports to HWPX.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.hwpx_converter import convert_markdown_to_hwpx

CONVERT_LIST = [
    ("유타_주_내_국내기업_진출_가이드라인_p5_final_v6.md", "유타_주_내_국내기업_진출_가이드라인_p5_final_v6.hwpx"),
    ("버지니아_주_내_국내기업_진출_가이드라인_p5_final_v4.md", "버지니아_주_내_국내기업_진출_가이드라인_p5_final_v4.hwpx"),
    ("콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v3.md", "콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v3.hwpx"),
    ("텍사스_주_내_국내기업_진출_가이드라인_p5_final_v3.md", "텍사스_주_내_국내기업_진출_가이드라인_p5_final_v3.hwpx"),
    ("캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md", "캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v3.hwpx"),
    ("UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v3.md", "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v3.hwpx"),
    ("변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v3.md", "변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v3.hwpx"),
]

def main():
    report_dir = Path("workspace/report")
    print("==========================================================================================")
    print("STARTING HWPX BATCH GENERATION FOR 12 VERIFIED REPORTS")
    print("==========================================================================================")

    results = []
    for md_name, hwpx_name in CONVERT_LIST:
        md_path = report_dir / md_name
        hwpx_path = report_dir / hwpx_name
        if not md_path.exists():
            print(f"ERROR: {md_name} does not exist!")
            continue

        print(f">>> Converting: {md_name} -> {hwpx_name} ...", end=" ", flush=True)
        try:
            out = convert_markdown_to_hwpx(md_path, hwpx_path)
            size = hwpx_path.stat().st_size
            print(f"SUCCESS ({size:,} bytes)")
            results.append((hwpx_name, size, "OK"))
        except Exception as e:
            print(f"FAILED: {e}")
            results.append((hwpx_name, 0, f"FAILED: {e}"))

    print("\n==========================================================================================")
    print("HWPX CONVERSION SUMMARY")
    print("==========================================================================================")
    for name, size, status in results:
        print(f"{name:<65} | {size:>10,} bytes | {status}")

if __name__ == "__main__":
    main()
