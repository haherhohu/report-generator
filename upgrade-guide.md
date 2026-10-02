# 보고서 생성기 v2 업데이트 가이드

### [핵심 아키텍처 개편 요약]

1. **지식 베이스(KB) 2원화 (Fact vs. Stance)**:
   - **Fact DB**: 공신력 있는 통계, 해외 규제(FAA/NIST 등), 수집 원천 자료.
   - **Stance DB**: 회장님의 의뢰 방향, 기관의 정책적 주장, 전략적 유치 목표(예: 새만금 센터 유치 당위성 등).
   - **제어 룰**: 사실 기술 절에는 Fact만 주입하고, '시사점/정책 제언' 절에만 Stance를 주입하여 **기정사실 왜곡을 원천 차단**합니다.
2. **3대 실행 모드 통일 (Generator / Verifier / Translator)**:
   - **Mode A (생성 파이프라인)**: 분할 기획 → Sub-TOC 생성 → 1차 검증 → 무손실 병합 → 2차 총괄 검증.
   - **Mode B (단독 검증 파이프라인)**: 기생성된 대형 문서를 청크 단위로 분해 → 팩트/논조/서식 검증 → 재병합.
   - **Mode C (초장문 번역 파이프라인)**: 200~600페이지 문서를 AST/헤딩 기준으로 청크 분할 → 용어집(Glossary) 고정 번역 → 분량 보존 검증 → 재조립.
3. **결정론적 후처리 & HWPX 스타일 엔진**:
   - LLM의 비결정적 오류(`> |` 표 깨짐, CoT 누출, 넘버링 파편화)는 Python 정규식 및 HWPX 템플릿 주입기로 100% 기계적 처리합니다.

# [순차적 프로그램 업데이트 프롬프트 가이드 (Copilot / Antigravity 전용)]

아래 Step 1부터 Step 5까지의 작업 지시 블록을 복사하여 Copilot이나 Antigravity에 순서대로 프롬프트로 전달하시면 됩니다.

### [Step 1] 상태 스키마 확장 및 설정 고도화

> **목적**: 파이프라인 상태(`ReportState`)에 단독 검증, 초장문 번역, Fact/Stance 분리 파라미터를 추가하고 설정을 확장합니다.

Markdown

```
# Task: ReportState 스키마 확장 및 멀티 모드(Generate, Verify, Translate) 지원

## 목표
`src/core/state.py`와 `config/pipeline_config.yaml`을 수정하여 기존 보고서 생성기 외에 '단독 문서 검증(standalone_verify)' 및 '초장문 분할 번역(chunk_translate)' 워크플로우를 수용할 수 있도록 데이터 구조를 확장하십시오.

## 세부 구현 요구사항
1. `src/core/state.py`의 `ReportState` TypedDict 수정:
   - `mode`: Literal["generate", "verify", "translate"] 추가 (기본값: "generate")
   - `knowledge_context`: Dict[str, Any] 추가
     - `fact_sources`: List[str] (객관적 사실 및 외부 수집 레퍼런스 경로)
     - `strategic_stance`: str (사용자 설정 및 기관의 정책적 방향성/주장 텍스트)
   - `source_doc_path`: Optional[str] (단독 검증 또는 번역 시 입력할 원본 md/txt 경로)
   - `translation_meta`: Optional[Dict[str, Any]] (출발어, 도착어, 고정 전문용어 사전 매핑)
   - `verification_report`: List[Dict[str, Any]] (각 절/청크별 검증 통과 여부 및 교정 로그)

2. `config/pipeline_config.yaml` 설정 추가:
   - `verification_level`: "strict" | "standard"
   - `translation_chunk_size`: 3000 (토큰 또는 글자 수 기준 분할 단위)
   - `chunk_overlap`: 200 (맥락 단절 방지용 오버랩)
   - `stance_injection_targets`: ["implications", "policy_proposals", "action_plans"] (주장 반영 허용 챕터 명시)

기존 파이프라인과의 하위 호환성을 유지하면서 위 코드를 작성하십시오.
```

### [Step 2] Fact vs. Stance 분리형 RAG 라우터 및 프롬프트 고도화

> **목적**: 주장을 사실로 둔갑시키는 환각을 막고, 시사점에만 전략적 방향성을 주입하는 프롬프트 엔진을 구축합니다.

Markdown

```
# Task: Fact-Stance 라우팅 엔진 및 NIM 검증 프롬프트 구축

## 목표
본문 작성 에이전트(`src/agents/expander.py`)와 검증 에이전트(`src/agents/verifier.py` 신규 생성)에서 객관적 사실과 기관의 정책적 주장을 엄격히 구분하여 주입하도록 로직을 재설계하십시오.

## 세부 구현 요구사항
1. `prompts/expander_prompt.md` 업데이트:
   - 일반 동향/현황 섹션: 제공된 `fact_sources`에 기반하여 개조식(~함, ~로 분석됨)으로 객관적 서술 유지.
   - 시사점/제언 섹션: `strategic_stance`를 반영하되, 기정사실화(예: '기구축된 새만금 센터')를 절대 금지하고 반드시 "글로벌 규제 대응을 위한 선제적 구축 필요성 도출"과 같은 '정책 제언형' 논조로 서술하도록 지침 강화.

2. `src/agents/verifier.py` (신규 모듈 생성):
   - NIM LLM을 호출하여 생성된 청크를 3대 기준으로 전수 검증:
     ① 팩트 왜곡/환각 여부 (존재하지 않는 해외 인프라 날조 검출)
     ② 정책 논조 준수 여부 (미확정 국내 사업의 기정사실화 여부)
     ③ 문체 준수 여부 (번역투, '게임 체인저' 등 상투어구, 불필요한 접속사 제거)
   - 검증 탈락 시 수정한 본문과 수정 사유(changelog)를 반환하는 루프 작성.
3. 단위 테스트 작성:
   - `tests/test_verifier_logic.py`를 작성하여 환각이 포함된 텍스트가 정상 교정되는지 검증하십시오.
```

### [Step 3] 단독 검증기(Standalone Verifier) 파이프라인 구축

> **목적**: 기존에 이미 생성된 200페이지 규모의 보고서를 청크 단위로 나누어 검증·교정하는 독립 워크플로우를 만듭니다.

Markdown

```
# Task: 대용량 마크다운 문서 단독 검증 파이프라인 개발

## 목표
이미 완성된 대규모 마크다운 보고서(100~200p+)를 입력받아 문서 전체 맥락과 분량을 보존하면서 단계별로 검증·교정하는 파이프라인을 구축하십시오.

## 세부 구현 요구사항
1. `src/tools/doc_chunker.py` 모듈 생성:
   - 마크다운 문서를 헤딩 레벨(H1, H2, H3) 기준으로 의미 단위 파싱.
   - 각 청크의 메타데이터(헤딩 뎁스, 원본 순서, 캡션 번호)를 유지하는 `DocumentChunk` 클래스 구현.

2. `src/graph/verifier_graph.py` 워크플로우 생성:
   - 문서 파싱 ➔ 청크 순회 검증(NIM 기반 Verifier Node) ➔ 무손실 재조립 ➔ 전체 목차 및 캡션 넘버링 연속성 재검토 단계 구축.
   - 각 청크 검증 시 이전 청크의 마지막 문단 500자를 컨텍스트로 제공하여 문맥 단절 방지.
   - 검증 과정에서 전체 텍스트 분량이 10% 이상 축소(요약)되는 현상을 방지하는 게이트키퍼 로직 포함.

3. `main.py`에 단독 검증 CLI 옵션 추가:
   - `python main.py --mode verify --input-file workspace/report/target.md --stance "새만금 실증단지 유치 당위성 강조"`
```

### [Step 4] 초장문(200~600p) 분할 번역 파이프라인 구축

> **목적**: 컨텍스트 제한을 극복하고, 고정 용어집을 바탕으로 번역 퀄리티와 분량을 보존하는 번역 파이프라인을 구축합니다.

Markdown

```
# Task: 초장문 분할 번역 및 역번역 검증 엔진 구축

## 목표
200~600페이지의 전문 영문/한글 보고서를 문단/절 단위로 쪼개어 용어 일관성을 유지하며 고속 번역하고 무손실 병합하는 파이프라인을 구현하십시오.

## 세부 구현 요구사항
1. `src/tools/glossary_manager.py` 모듈 구현:
   - 원문 전체를 사전 스캔하여 핵심 고유명사 및 약어 목록을 추출하고 번역 사전(Glossary) 생성.
   - 번역 시 해당 전문 용어가 일관되게 치환되도록 강제하는 지침 주입기 구현.

2. `src/agents/translator.py` 및 `src/graph/translator_graph.py`:
   - 입력된 대형 텍스트를 청크 분할 ➔ 용어집 바인딩 번역(NIM) ➔ 번역 품질 및 누락 검수(Verifier) ➔ 조립 순으로 동작.
   - 번역 검수 조건: 원문의 문단 구조, 표(Table), 수식, 리스트 넘버링을 100% 동일한 구조로 보존해야 함.

3. `main.py`에 번역 실행 옵션 연결:
   - `python main.py --mode translate --input-file workspace/source/target_600p.pdf --target-lang ko`
```

### [Step 5] 결정론적 Python 포맷터 및 HWPX 템플릿 익스포터 구축

> **목적**: LLM이 해결하기 어려운 마크다운 문법 파탄을 100% 파이썬 룰 기반으로 수정하고, 한글 서식 템플릿을 적용하여 저장합니다.

Markdown

```
# Task: 결정론적 마크다운 클리너 및 HWPX 템플릿 변환기 구현

## 목표
LLM의 비결정적 출력 오류(표 깨짐, CoT 누출, 태그 미처리)를 정규식으로 완벽히 정돈하고, 최종 결과물을 관공서/국책 표준 HWPX 서식으로 자동 매핑하여 출력하는 엔진을 완성하십시오.

## 세부 구현 요구사항
1. `src/utils/markdown_cleaner.py` 모듈 강화:
   - `> |` 인용구 내 표 구조를 일반 마크다운 표(`|`)로 복구.
   - `Here's a thinking process:`, `<think>...</think>`, 시스템 지침 잔여 텍스트 강제 삭제.
   - 캡션 번호(`[표 Ⅰ-1-1]`, `[그림 Ⅰ-1-1]`) 및 계층 번호(`Ⅰ.` ➔ `1.` ➔ `1)` ➔ `가.`) 순차적 재색인 및 강제 매핑.
   - 약어표는 본문에서 추출된 JSON 데이터를 파이썬이 알파벳 순 표로 렌더링하고, 불필요한 시사점 문구 자동 절삭.

2. `src/tools/hwpx_exporter.py` 모듈 구축:
   - 정돈된 순수 마크다운을 파싱하여 사전 정의된 관공서 HWPX 템플릿의 스타일(본문_개조식, 표_본문, 제목_1단계 등)에 1:1 매핑하여 파일 생성.
   - 깨진 태그(`<br>`, 불완전한 볼드)를 HWPX 규격 문단 구분자로 치환.

3. 엔드투엔드 파이프라인 통합:
   - 생성/검증/번역 파이프라인의 최종 단계에 `markdown_cleaner.py`와 `hwpx_exporter.py`가 반드시 실행되도록 파이프라인 러너를 업데이트하십시오.
```
