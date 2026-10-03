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
all_passed = True

print(f"{'File':<30} | {'T_B/TOC':<9} | {'F_B/TOC':<9} | {'T_Dup':<5} | {'F_Dup':<5} | {'Draft':<5} | {'Ctr':<5} | {'KURA':<5} | {'Proj':<5} | {'Art':<5} | {'SecNum':<6}")
print("-" * 105)

for fname in target_files:
    fpath = report_dir / fname
    if not fpath.exists():
        print(f"NOT FOUND: {fname}")
        all_passed = False
        continue
    text = fpath.read_text(encoding="utf-8")
    lines = text.splitlines()

    body_t = len(re.findall(r"(?m)^\s*\*{0,2}\[표\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)\]", text))
    toc_t = len([l for l in lines[:500] if re.match(r"^\s*-\s*\*\*\[표", l)])
    body_f = len(re.findall(r"(?m)^\s*\*{0,2}【그림\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)】", text))
    toc_f = len([l for l in lines[:500] if re.match(r"^\s*-\s*\*\*【그림", l)])

    t_titles = [re.sub(r"^\s*\*{0,2}\[표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+\]\*{0,2}\s*", "", l).strip() for l in lines if re.match(r"^\s*\*{0,2}\[표\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+\]", l)]
    t_dup = len(t_titles) - len(set(t_titles))
    f_titles = [re.sub(r"^\s*\*{0,2}【그림\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+】\*{0,2}\s*", "", l).strip() for l in lines if re.match(r"^\s*\*{0,2}【그림\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+】", l)]
    f_dup = len(f_titles) - len(set(f_titles))

    c_draft = len(re.findall(r"구축\(?안\)?|센터\s*구축안", text))
    c_ctr = len(re.findall(r"RAMS\s*(?:시험·?평가\s*)?센터|Physical\s*AI\s*(?:RAMS\s*)?센터", text, re.I))
    c_kura = len(re.findall(r"\bKURA\b", text))
    c_proj = len(re.findall(r"(?:Physical\s*AI\s*(?:기반\s*)?)?(?:UAS\s*)?RAMS\s*(?:구축\s*)?사업", text, re.I))
    c_art = len(re.findall(r"체계(?:기술|평가|프로세스|아키텍처|핵심|시\b|로드맵)|방안전·후", text))

    toc_lines = [l for l in lines[:500] if re.match(r"^\s*-\s*\*\*(\[표|【그림)", l)]
    c_secnum = 0
    for l in toc_lines:
        if re.search(r"^\s*-\s*\*\*(?:\[표|【그림)\s*[^\]】]+(?:\s*\]|\s*】)\*\*\s*(?:<[^>]+>\s*)?((?:제\s*\d+\s*[장절편]|제\s*[ⅠⅡⅢⅣⅤⅥⅦⅧ]+\s*[장절편]|\d+(?:[\.\-]\d+)+[\.\-]?|\d+\.(?!\d)|[ⅠⅡⅢⅣⅤⅥⅦⅧ]+(?:[\.\-]\d+)*[\.\-]?)\s+)", l):
            c_secnum += 1

    t_str = f"{body_t}/{toc_t}"
    f_str = f"{body_f}/{toc_f}"
    print(f"{fname[:30]:<30} | {t_str:<9} | {f_str:<9} | {t_dup:<5} | {f_dup:<5} | {c_draft:<5} | {c_ctr:<5} | {c_kura:<5} | {c_proj:<5} | {c_art:<5} | {c_secnum:<6}")

    if body_t != toc_t or body_f != toc_f or t_dup != 0 or f_dup != 0 or c_draft != 0 or c_ctr != 0 or c_kura != 0 or c_proj != 0 or c_art != 0 or c_secnum != 0:
        all_passed = False

print("-" * 105)
print("AUDIT RESULT:", "ALL 100% PERFECT!" if all_passed else "SOME FAILED")
