import re
from pathlib import Path

PROMPT_BLOCK_STARTERS = [
    r'^\s*(?:\d+\.\s*)?\*\*(?:analyze|identify|drafting|writing|deconstruct|plan|outline|core topics|constraints|instructions?)[^\n]*\*\*',
    r'^\s*[-*]\s*\*\*(?:4 rules|4 major rules|rules|instruction details|constraints|core direction|context summary|additional constraints|key constraints|key directives)[^\n]*\*\*',
    r'^\s*check rules again:',
    r'^\s*\[작성\s*강령\]',
    r'^\s*지시사항:',
    r'^\s*(?:\d+\.\s*)?i need to analyze\b',
    r'^\s*the user has provided a detailed\b',
    r'^\s*looking at the (?:provided text|request)\b',
    r'^\s*tone/ending:\b',
    r'^\s*tone/unification:\b',
    r'^\s*ending consistency:\b',
    r'^\s*[-*]\s*어미 규칙:\b',
    r'^\s*[-*]\s*actually,\s*re-reading:\b',
    r'^\s*[-*]\s*user wants me to act as a\b',
    r'^\s*[-*]\s*maintain single report unity\b',
    r'^\s*[-*]\s*no individual reference lists\b',
    r'^\s*[-*]\s*there\'s a conflict\b'
]
COMPILED_STARTERS = [re.compile(p, re.IGNORECASE) for p in PROMPT_BLOCK_STARTERS]

def clean_multiline_prompt_residue(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    in_prompt_block = False
    
    for i, line in enumerate(lines):
        s = line.strip()
        
        # Check if line initiates prompt block
        if not in_prompt_block:
            if any(cp.search(s) for cp in COMPILED_STARTERS):
                in_prompt_block = True
                continue
        
        if in_prompt_block:
            # Exit conditions
            if s.startswith('#'):
                in_prompt_block = False
                cleaned_lines.append(line)
                continue
            if s == '---':
                next_is_heading = False
                for j in range(i+1, min(i+6, len(lines))):
                    if lines[j].strip().startswith('#'):
                        next_is_heading = True
                        break
                    elif lines[j].strip():
                        break
                if next_is_heading:
                    in_prompt_block = False
                    cleaned_lines.append(line)
                    continue
            
            kor_chars = len(re.findall(r'[가-힣]', s))
            eng_words = len(re.findall(r'\b[A-Za-z]{2,}\b', s))
            if kor_chars >= 20 and eng_words < 5 and s.endswith(('다.', '임.', '함.', '됨.', '음.')):
                in_prompt_block = False
                cleaned_lines.append(line)
                continue
            
            # Skip line within prompt block
            continue
            
        # Clean standalone code fence wrappers that wrap markdown
        if s in ('```', '```markdown', '```text'):
            continue
            
        cleaned_lines.append(line)
        
    res = '\n'.join(cleaned_lines)
    res = re.sub(r'\n{3,}', '\n\n', res)
    return res

if __name__ == '__main__':
    targets = [
        'workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_NATO_p5_final_v1.md',
        'workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v1.md',
        'workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_캐나다_p5_final_v1.md',
        'workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_호주_p5_final_v1.md',
    ]
    for t in targets:
        p = Path(t)
        if not p.exists(): continue
        raw = p.read_text(encoding='utf-8')
        cleaned = clean_multiline_prompt_residue(raw)
        p.write_text(cleaned, encoding='utf-8')
        print(f'{p.name}: {len(raw):,} -> {len(cleaned):,} chars (reduced {len(raw)-len(cleaned):,} chars)')
