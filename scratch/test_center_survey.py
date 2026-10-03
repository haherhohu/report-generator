import re
from pathlib import Path

target_files = [
    "유타_주_내_국내기업_진출_가이드라인_p5_final_v5.md",
    "버지니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md",
    "콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v2.md",
    "텍사스_주_내_국내기업_진출_가이드라인_p5_final_v2.md",
    "캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v2.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v2.md",
    "변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v2.md",
]

report_dir = Path("workspace/report")

for fname in target_files:
    raw = (report_dir / fname).read_text(encoding="utf-8")
    matches = re.findall(r"[^\n]{0,40}(?:RAMS\s*(?:시험·?평가\s*)?센터|센터\s*연계|Physical\s*AI\s*(?:RAMS\s*)?센터)[^\n]{0,40}", raw, re.I)
    if matches:
        print(f"=== {fname[:20]} ({len(matches)}) ===")
        for m in matches[:5]:
            print("  ", m.strip().replace("\n", " "))
