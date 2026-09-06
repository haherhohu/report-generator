# Multi-Agent Long-Form Report Generator

> **AI 기반 국책·공공 연구기관 및 산업 동향 분석용 초장문(30p~200p+) 보고서 자동 생성 파이프라인**

본 프로젝트는 공공기관, 국가연구개발기관, 민간 연구소 및 해외 진출 지원 기관에 제출·활용되는 대규모(**30페이지/약 4만 자 ~ 200페이지 이상/약 25만 자**) 보고서를 전자동으로 생성하기 위한 **LangGraph 기반 Multi-Agent 파이프라인**입니다.

기존 검증된 장애 대응/체크포인트 메커니즘과 고품질 국책 표준 서식 체계를 융합하여, **모듈 간 결합도가 낮고 견고한 순수 Markdown 텍스트 엔진**으로 구축되었습니다.

---

## 🌟 핵심 특징 및 개선 성과

1. **순수 Markdown 텍스트 엔진**:
   - 불필요한 웹 뷰 및 HTML 컴포넌트 종속성을 일체 배제하고 순수 Python + Markdown 표준 규격으로 정제.
2. **비즈니스 로직과 UI/CLI 인터페이스 완전 분리**:
   - 핵심 파이프라인(`src/`)은 독립 모듈로 캡슐화되어 CLI(`main.py`), Streamlit 웹 대시보드, FastAPI 등 어디서든 `PipelineRunner`를 통해 동일하게 구동 가능.
3. **3대 표준 보고서 유형 동적 지원**:
   - **정부제출용 연구기관 보고서 (`research_policy`)**: 9대 장 구조, 국책 표준 서술 어조(`~함`, `~임`), 정책 당위성, R&D 세부수행과제(Action Plans), 재정 투자 및 로드맵 중심.
   - **민간기관용 연구/동향조사 원고 (`market_tech_trend`)**: 8대 장 구조, 부드러운 서술 어조(`~한다`, `~이다`), 시장/기술/산업 생태계 동향 및 다각적 시사점(Implications) 중심 (억지 사업과제 배제).
   - **해외시장진출 전략보고서 (`global_market_expansion`)**: 8대 장 구조, 실무 제안 어조(`~한다`, `~이다`), 해외 진출 환경, 주요국 지원제도 조사 및 맞춤형 진출 가이드라인 중심.
4. **본문(1~N-1장) vs 부록(부록 장) 명확한 역할 분리 및 일체감 유지**:
   - 본문 챕터 내에서 독립적으로 전체 결론을 내리거나 개별 참고문헌/약어표를 중복 작성하는 현상을 차단하고, 오직 `[소결: 본 절의 주요 시사점 및 연계 방향]` 형태로 절 내부 논리만 매듭지음.
   - 마지막 부록 장에서 본문 전체 인용구와 수집 자료를 취합하여 **통합 참고문헌 목록**과 **총괄 영문 약어 정의표(Glossary)**를 일괄 합성.
5. **Sub-TOC 분할 정복 팽창**:
   - 각 절(Section) 작성 시 기획된 핵심 토픽(`key_topics`)과 필수 표(`planned_tables`), 실증 사례(`planned_case_studies`)를 기반으로 3~4개의 세부 소주제(Sub-TOC)를 선행 기획하여 밀도 높은 본문 작성.
   - 본문 내 **【그림 X-X】 도식화 블록(ASCII 구조도 + AI 생성 프롬프트 + 조판 규격)** 및 정밀 데이터 마크다운 표(Table) 의무 수록.
6. **단조 증가(Monotonic Growth) 게이트키퍼**:
   - 분량 미달 시 기존에 작성된 절을 덮어쓰거나 축소하지 않고, 배경 및 실증 사례 챕터에 **신규 세부 목차(Section)를 증설**하여 이전 작성분을 100% 보존하면서 목표 분량까지 점진적으로 팽창 (최대 2회 루프 제한).
7. **엔터프라이즈 안정성 가드레일 (Safety Nets)**:
   - 429/503/504 지수 백오프(2s~30s) 재시도 및 다중 모델 티어링/Fallback (Gemini ➔ NVIDIA NIM/OpenAI ➔ 오프라인 결정론적 폴백 엔진).
   - Gemini와 OpenAI/NIM 간 응답 객체 차이를 완벽히 흡수하는 단일 텍스트 변환 엔진 내장.
   - 동일 자료/섹션 5회 이상 작성 시 `_final` 고정 및 재사용(5-Duplicate Guard).
   - LangGraph `SqliteSaver` 기반 세션 체크포인트를 통한 임의 중단 후 무손실 재개(`--resume`) 지원.

---

## 🔄 10-Step 수행 프로세스

```text
[Step 0] 사전 전처리: 무거운 대형 PDF/HTML 파일을 가벼운 마크다운 팩트 시트로 분할 요약
[Step 1] 방향성에 맞춘 보고서 타입별 최초 뼈대(v1) 작성 (/report/[주제]_v1.md)
[Step 2] 사용자 제공 자료(/source)를 융합한 업데이트 초안(v2) 작성 (/report/[주제]_v2.md)
[Step 3] v2 초안과 제공 자료로부터 심층 조사 키워드 매트릭스 5~8건 도출
[Step 4] 키워드별 하이브리드 웹 검색 및 팩트 수집 (/reference/[keyword].md)
[Step 5] 자료 아카이빙 및 중복 방지 (5회 이상 중복 시 Final 요약본 고정 및 재사용)
[Step 6] 팩트를 기반으로 키워드별 조사보고서 작성 (/report/research_[keyword].md)
[Step 7] 챕터 성격별 동적 라우팅 및 세부 절(Sub-TOC) 분할 정복 팽창 (/report/[주제]_v3_ch[n]_sec[m].md)
[Step 8] 마크다운 헤딩 뎁스 통일, 문체 교열, 중간 장 결론 소결화 검토 (Reviewer)
[Step 9] 게이트키퍼 분량 심사: 코어 70% 방어 확인 및 신규 목차 증설 루프 통제 (최대 2회)
[Step 10] 전체 본문 무손실 병합, 통합 참고문헌 및 총괄 영문 약어표 합성 (/report/[주제]_v3_final.md)
```

---

## 📁 디렉터리 구조

```text
report-generator/
├── config/                          # 파이프라인 및 모델 설정
│   ├── pipeline_config.yaml         # 전역 설정 (루프 한도, 동시성, 목표 분량)
│   ├── agents_config.yaml           # 에이전트별 모델(Gemini / NIM), 파라미터, fallback 목록
│   ├── initial_state.yaml           # 초기 보고서 의뢰 템플릿
│   └── templates/                   # 보고서 유형별 장/절 템플릿
│       ├── research_policy.yaml     # 정부제출용 연구보고서 (9대 장)
│       ├── market_tech_trend.yaml   # 민간 동향조사원고 (8대 장)
│       └── global_market_expansion.yaml # 해외시장진출 전략보고서 (8대 장)
├── prompts/                         # 에이전트별 특화 시스템 프롬프트 (Markdown)
│   ├── drafter_prompt.md            # 초안 기획 프롬프트
│   ├── researcher_prompt.md         # 팩트 조사 프롬프트
│   ├── expander_prompt.md           # Sub-TOC 본문 팽창 프롬프트
│   ├── reviewer_prompt.md           # 교열 및 헤딩 표준화 프롬프트
│   └── merger_prompt.md             # 최종 병합 프롬프트
├── src/                             # 순수 파이프라인 비즈니스 로직
│   ├── core/                        # 상태 스키마 및 템플릿 로더
│   │   ├── state.py                 # ReportState, ChapterItem, SectionItem TypedDict
│   │   ├── report_types.py          # 보고서 유형 정규화 및 동적 챕터 빌더
│   │   └── exceptions.py            # 파이프라인 커스텀 예외
│   ├── models/                      # AI 모델 클라이언트 및 폴백 엔진
│   │   ├── client.py                # Gemini & NIM/OpenAI 통합 클라이언트 (재시도/티어링)
│   │   └── fallback_engine.py       # API 전면 마비 대응 결정론적 마크다운 생성기
│   ├── tools/                       # 외부 I/O 및 검색 도구
│   │   ├── search.py                # DuckDuckGo 하이브리드 검색 (정책/공공/PDF 타겟)
│   │   └── preprocessor.py          # 대형 PDF/HTML 자료 사전 요약기
│   ├── utils/                       # 유틸리티 및 안전 가드레일
│   │   ├── file_manager.py          # Append-Only 무덮어쓰기 버전 파일 관리
│   │   ├── final_guard.py           # 5회 중복 방지 및 Final 자동 재사용 실드
│   │   ├── markdown_tools.py        # 마크다운 헤딩 뎁스 정규화 및 중간 결론 정제
│   │   ├── router.py                # 챕터 역할(동향, 전략, 시사점, 부록) 동적 지침 라우터
│   │   └── glossary_parser.py       # 본문 영문 약어(Acronym) 및 인용 출처 자동 추출
│   ├── agents/                      # 6대 특화 에이전트 노드
│   │   ├── drafter.py               # Step 1~3: 마스터 아웃라인 기획 및 v1/v2 초안
│   │   ├── researcher.py            # Step 4~6: 키워드 검색, 팩트 수집 및 아카이빙
│   │   ├── expander.py              # Step 7: Sub-TOC 분할 팽창, 도식화/표 삽입
│   │   ├── reviewer.py              # Step 8: 마크다운 뎁스 표준화, 문체 교열, 소결화
│   │   ├── gatekeeper.py            # Step 9: 분량 심사 및 신규 목차 증설 루프 통제
│   │   └── merger.py                # Step 10: 무손실 병합, 통합 참고문헌/약어표 생성
│   └── graph/                       # LangGraph 워크플로우 제어부
│       ├── workflow.py              # StateGraph 컴파일 및 SqliteSaver 체크포인터
│       └── runner.py                # CLI/Streamlit 공용 PipelineRunner 실행기
├── tests/                           # 단위 및 통합 테스트 스위트 (pytest 17종)
│   ├── test_report_types.py         # 보고서 유형 로딩 및 챕터 역할 검증
│   ├── test_markdown_tools.py       # 헤딩 정규화 및 소결 치환 검증
│   ├── test_glossary_parser.py      # 약어 및 인용구 추출 검증
│   ├── test_final_guard.py          # 5회 중복 방지 및 Final 재사용 검증
│   ├── test_router.py               # 챕터 역할별 프롬프트 라우팅 검증
│   ├── test_gatekeeper_expansion.py # 신규 세부 목차 증설 단조 증가 검증
│   ├── test_runner_and_checkpoint.py# 세션 체크포인트 및 재개 검증
│   └── test_workflow_execution.py   # 엔드투엔드 6단계 파이프라인 상태 전이 검증
├── workspace/                       # 런타임 입출력 격리 디렉터리 (.gitignore)
│   ├── source/                      # 사용자 제공 원시 파일
│   ├── reference/                   # 수집된 원시 자료 및 조사보고서
│   ├── report/                      # 버전별 산출물 및 최종 보고서 (*_v3_final.md)
│   └── checkpoints/                 # SqliteSaver 세션 체크포인트 DB
├── main.py                          # CLI 실행 엔트리포인트
├── guideline.md                     # 통합 아키텍처 및 세부 작성 가이드라인
├── requirements.txt                 # 의존 라이브러리 목록
└── readme.md                        # 프로젝트 설명서 (본 문서)
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 구성 및 의존성 설치

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

# 필수 라이브러리 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (`.env`)

프로젝트 루트에 `.env` 파일을 생성하고 사용할 모델의 API 키를 설정합니다:

```env
# Google Gemini API 키 (1차 기본 권장 모델)
GEMINI_API_KEY=your_gemini_api_key_here

# NVIDIA NIM API 키 (대체 Fallback 모델)
NIM_API_KEY=your_nim_api_key_here

# 또는 OpenAI 호환 API를 사용할 경우
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 파이프라인 CLI 실행

```bash
# 기본 실행 (config/initial_state.yaml 의뢰 건 작성)
python3 main.py --state-file config/initial_state.yaml

# 특정 세션 식별자를 지정하여 실행
python3 main.py --thread-id session_uav_01 --state-file config/initial_state.yaml

# 오류나 일시 장애로 중단된 경우 동일 세션의 직전 성공 노드부터 즉시 재개
python3 main.py --thread-id session_uav_01 --resume
```

---

## 💻 프로그래밍 방식 실행 (`PipelineRunner`)

Streamlit 대시보드, FastAPI 서버 또는 커스텀 Python 스크립트에서 파이프라인을 직접 호출할 수 있습니다:

```python
from src.graph.runner import PipelineRunner

runner = PipelineRunner("config/pipeline_config.yaml")

initial_state = {
    "topic": "AI 기반 자율비행 드론 기술 및 시장 동향",
    "direction": "글로벌 시장 동향 분석 및 국내 산업계 시사점 도출",
    "target_perspective": "국책 연구기관 관점",
    "report_type": "market_tech_trend",
    "target_pages": 30,
    "target_chars": 40000,
    "is_blank_slate": True,
}

def on_step_finished(node_name: str, state: dict):
    print(f"노드 완료: {node_name}")

final_state = runner.run(
    initial_state=initial_state,
    thread_id="my_custom_run",
    progress_callback=on_step_finished,
)

print("최종 보고서 저장 경로:", final_state["final_report_path"])
```

---

## 🧪 테스트 실행

전체 17개 단위 및 통합 테스트를 실행하여 모든 모듈의 정상 동작을 검증합니다:

```bash
python3 -m pytest tests
```

---

## 📄 라이선스 및 유의사항

- 본 파이프라인은 국책·공공 보고서 표준 서식 체계 및 AI 안전장치 가이드라인을 준수합니다.
- 대규모 텍스트 생성 시 과도한 API 호출을 방지하기 위해 `max_loops`와 `max_concurrency` 설정값이 `config/pipeline_config.yaml`에 사전 정의되어 있습니다.
