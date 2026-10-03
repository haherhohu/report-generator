import re
from pathlib import Path

target_files = [
    "유타_주_내_국내기업_진출_가이드라인_p5_final_v6.md",
    "버지니아_주_내_국내기업_진출_가이드라인_p5_final_v4.md",
    "콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v3.md",
    "텍사스_주_내_국내기업_진출_가이드라인_p5_final_v3.md",
    "캘리포니아_주_내_국내기업_진출_가이드라인_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_비NATO_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_미국_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v3.md",
    "UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v3.md",
    "변화하는_시대_흐름에_맞춰_글로벌_UAV_관련_보수교육_기관_동향_조사_p5_final_v3.md",
]

report_dir = Path("workspace/report")

for fname in target_files:
    fpath = report_dir / fname
    text = fpath.read_text(encoding="utf-8")
    lines = text.splitlines()

    body_start = 0
    for idx, l in enumerate(lines):
        if l.startswith("## Ⅰ.") or l.startswith("# Ⅰ."):
            body_start = idx
            break

    new_lines = []
    inserted = 0
    for i in range(len(lines)):
        if i >= body_start:
            line = lines[i]
            if re.match(r"^\s*\*{0,2}(?:\[표|【그림)", line):
                if new_lines and new_lines[-1].strip() != "":
                    new_lines.append("")
                    inserted += 1
        new_lines.append(lines[i])

    updated_text = "\n".join(new_lines) + "\n"
    fpath.write_text(updated_text, encoding="utf-8")
    print(f"{fname[:30]}: inserted {inserted} blank lines before body captions.")
