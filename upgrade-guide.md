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

---

# [향후 개선 방향 및 기술 부채 리팩토링 로드맵 (2026-10-03)]

### [핵심 리팩토링 배경]

12종 대규모 공공 보고서(유타, 버지니아, 콜로라도, 텍사스, 캘리포니아, NATO, 비NATO, 미국, 호주, 캐나다, 중남미, 보수교육기관)의 긴급 서식 정제 및 납품 피드백 대응 과정에서, 결과물의 무결성(목차-본문 1:1 완벽 일치, 479개소 표·그림 캡션 개행 분리, 미발표 비공개 문건 및 환각 박멸, HWPX 공공 규격 변환)을 확보하기 위해 **엔진 일부에 단기 집중형 핫픽스(Over-fitted Hotfixes)**가 적용되었습니다.

차기 세션에서는 본 시스템의 범용성(Generalization), 유지보수성, 코드 청결도를 회복하기 위해 아래 순차적 과제를 수행해야 합니다.

---

### [Step 6] Executive Summary 하드코딩 분기 제거 및 범용 요약기 일원화

> **목적**: `src/utils/markdown_cleaner.py` 내에 특정 지역명("영국", "캐나다", "호주", "중남미", "보수교육")으로 고정된 문자열 분기를 제거하고, LLM 기반 범용 요약 엔진으로 일원화합니다.

```markdown
# Task: Executive Summary 동적 생성기 추상화 및 하드코딩 제거

## 목표

`src/utils/markdown_cleaner.py`의 `generate_executive_summary` 함수에서 특정 보고서 키워드로 분기되어 하드코딩된 Executive Summary 텍스트를 전면 걷어내고, 본문 팩트와 보고서 메타데이터(`report_type`, `topic`, `direction`)를 기반으로 동적 생성하도록 리팩토링하십시오.

## 세부 구현 요구사항

1. `src/utils/markdown_cleaner.py`:
   - "영국", "캐나다", "호주", "중남미", "보수교육" 등의 조건 분기(`elif "..." in clean_title: return ...`) 완전 삭제.
   - 대체 방안:
     - (Option A) 경량 LLM(NIM / Gemini)을 호출하여 본문 도입부 및 결론부를 바탕으로 5줄 표준 요약문(`> **【Executive Summary: 핵심 요약】**...`) 동적 생성.
     - (Option B) 오프라인 환경을 위해 본문 첫 문단 및 각 장 소결(Implications)에서 완전한 한글 문장 5개를 추출하여 규격화된 요약 블록을 조립하는 범용 알고리즘 완성.
2. 테스트 검증:
   - 임의의 새로운 주제(예: "독일 드론 규제 동향", "해양 자율운항선박 기술")가 들어와도 하드코딩 없이 고품질 요약문이 추출되는지 테스트 작성.
```

---

### [Step 7] 특정 고유명사 타겟 정규식 외부화 (YAML 설정 기반 Fact Engine)

> **목적**: `src/tools/fact_stance_hotfix.py`와 `src/tools/apply_deep_purge_v3.py`에 파이썬 코드로 박혀 있는 1회성 정규식 패턴들을 선언적 설정 파일(`config/fact_rules.yaml`)로 분리합니다.

```markdown
# Task: 팩트 검증 및 환각 박멸 룰셋의 YAML 설정 기반 분리

## 목표

"유타 UTTR", "콜로라도 OEDIT", "고흥 발사체", "새만금", "Physical AI RAMS 센터", "KURA" 등 13종 보고서 작성 시 발생한 특정 환각을 잡기 위해 코어 코드에 하드코딩된 정규식을 분리하고, 설정 기반의 범용 사실검증 룰 엔진을 구축하십시오.

## 세부 구현 요구사항

1. `config/fact_rules.yaml` 신규 파일 정의:
   - `banned_phrases`: 비공개 문건 표기, 미확정 가상 센터, 가상 협력체 등 무조건 제거해야 할 패턴 목록.
   - `stance_downgrade_rules`: 당위적 서술(~해야 한다, 필수적이다)을 정책 제언형(~필요성이 제기된다, 검토해 볼 수 있다)으로 완화하는 문맥 치환 규칙.
   - `citation_sanitization_rules`: 자체 분석 사칭("자체 분석 결과", "자체 통계 DB")을 공인 데이터 종합 문구로 치환하는 규칙.
2. `src/tools/fact_stance_hotfix.py` 리팩토링:
   - 하드코딩된 튜플 리스트를 제거하고 `config/fact_rules.yaml`을 로드하여 정규식을 컴파일·적용하는 모듈형 아키텍처로 개편.
3. 단위 테스트:
   - 설정 파일 수정만으로 새로운 환각 단어나 정책 스탠스 교정 룰이 즉시 반영되는지 단위 테스트로 검증.
```

---

### [Step 8] 파편화된 전·후처리 및 정제 도구의 단일 파이프라인 통합

> **목적**: `src/tools/`, `tests/`, `scratch/`에 산재된 정제 스크립트들을 단일 표준 후처리 모듈(`src/processors/postprocessor.py`)로 일원화합니다.

```markdown
# Task: 보고서 종합 후처리 파이프라인 단일화

## 목표

대량 보고서 검증 과정에서 파편화된 스크립트(`apply_deep_purge_v3.py`, `comprehensive_report_cleaner.py`, `clean_step1.py`, `update_colorado_chapters.py` 등)의 핵심 기능을 단일 진입점으로 통합하십시오.

## 세부 구현 요구사항

1. `src/processors/postprocessor.py` 생성:
   - 다음 4단계 정제 프로세스를 단일 클래스(`ReportPostProcessor`)로 파이프라이닝:
     ① 서식 정제: `<center>` 제거, `<br>` 줄바꿈, 문단 첫머리 1칸 들여쓰기, 참고문헌 좌측 정렬.
     ② 캡션 및 목차 정합화: 본문 표/그림 앞 개행 분리, 목차-본문 넘버링/제목 1:1 강제 재색인.
     ③ 팩트 및 논조 정제: `config/fact_rules.yaml` 기반 Deep Purge 수행.
     ④ 부록 정제: 영문 약어표(Glossary) 알파벳 정렬 및 인용 출처 메타데이터 누수 차단.
2. CLI 연동:
   - 단일 파일 또는 디렉터리 단위 일괄 실행 지원:
     `python -m src.processors.postprocessor --input workspace/report/target.md --output workspace/report/target_clean.md`
3. 불필요한 일회성 스크립트(`src/tools/apply_deep_purge_v3.py`, `scratch/*`, `tests/clean_*.py`) 안전 아카이빙 또는 정리.
```

---

### [Step 9] HWPX 변환기 스타일 엔진 100% 선언적 YAML 외부화

> **목적**: `src/tools/hwpx_converter.py` 내부에 존재하는 스타일 매핑 및 레이아웃 로직을 `config/hwpx_style_mapping.yaml`로 완전 위임합니다.

```markdown
# Task: HWPX 변환 엔진 스타일 완전 외부화 및 스킨 템플릿 지원

## 목표

현재 파이썬 코드 내에 하드코딩된 HWPX 표 정렬, 셀 패딩, 폰트 크기, 개행 규칙을 `config/hwpx_style_mapping.yaml`로 100% 분리하여, 코드 수정 없이 YAML 설정과 템플릿 파일 교체만으로 다양한 관공서/기관 서식을 지원하도록 개선하십시오.

## 세부 구현 요구사항

1. `config/hwpx_style_mapping.yaml` 고도화:
   - 표(Table) 기본 정렬(중앙/좌측), 헤더 행 배경색, 테두리 두께, 내부 여백 설정 선언.
   - 콜아웃 박스(Tip, Note, Important)별 바탕색, 테두리, 아이콘 매핑 선언.
   - 참고문헌, 본문 단락, 헤딩 레벨(H1~H4)별 스타일 ID 및 문단 모양(들여쓰기, 줄간격) 정의.
2. `src/tools/hwpx_converter.py` 리팩토링:
   - 내부 스타일 로직을 YAML 설정 기반 렌더러로 변경.
   - 기관별 템플릿(예: 국책연구원용, 공공기관용, 민간용) 전환 플래그(`--template`) 지원.
```

---

### [Step 10] 오프라인 및 샌드박스 환경 Fast-Fail 및 로컬 LLM 보호 가드레일

> **목적**: 샌드박스나 폐쇄망에서 인터넷 연결 불가 시 불필요한 외부 API 재시도 루프를 방지하고 신속하게 로컬/오프라인 모드로 전환합니다.

```markdown
# Task: 네트워크 장애 Fast-Fail 및 차단 목록 보호 메커니즘

## 목표

외부 네트워크가 차단된 환경(샌드박스, 폐쇄망 등)에서 API 호출 시 `Connection error` 또는 DNS 실패가 발생할 경우, 각 모델별 불필요한 백오프 재시도를 즉각 중단(Fast-Fail)하고 안전하게 로컬 vLLM 또는 오프라인 폴백 엔진으로 진입하도록 개선하십시오.

## 세부 구현 요구사항

1. `src/models/client.py`:
   - 요청 시작 전 또는 첫 실패 시 DNS/네트워크 도달 가능성 1회 체크.
   - 네트워크 연결 자체가 없는 경우 모든 외부 모델 후보군 순회를 즉시 건너뛰고 로컬 엔드포인트(`OPENAI_BASE_URL`) 또는 오프라인 폴백 엔진으로 즉시 분기.
   - 단순 일시적 네트워크 단절 오류를 영구적 사용 불가 모델(`persist_unavailable_model`)로 오탐하여 차단 목록에 잘못 등록하는 부작용 방지.
```
