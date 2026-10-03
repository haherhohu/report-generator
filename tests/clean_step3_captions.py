"""Step 3 Caption and Fragment Normalization for Latin America and Virginia."""
from pathlib import Path
import re

LATIN_AMERICA_PATH = Path("workspace/report/UAV_산업_활성화를_위한_글로벌_인증_표준_및_기술_동향_중남미_p5_final_v1.md")
VIRGINIA_PATH = Path("workspace/report/버지니아_주_내_국내기업_진출_가이드라인_p5_final_v1.md")

# ==========================================
# 1. LATIN AMERICA REPLACEMENTS
# ==========================================

CH1_AUTHENTIC_SYNTHESIS = """### 3. 종합 소결 및 전략적 시사점

본 장에서는 국내 무인기(UAV) 산업 활성화를 위한 글로벌 인증 표준 및 기술 동향의 기초 현황과 세부 실증 분석을 수행하였다. 글로벌 주요국은 부품 단위의 신뢰성 검증(RAMS)부터 소프트웨어 안전성(DO-178C), 데이터 링크 보안, 시스템 통합 및 UTM 공역 연계에 이르는 전 체계(System of Systems) 인증 체계로 급격히 전환하고 있다. 반면 국내 인증 환경은 완제품 감항성 중심의 평가에 머물러 있어, 핵심 부품의 국산화 및 해외 시장 진출 시 인증 호환성 확보에 구조적 한계를 안고 있다.

따라서 국내 산업계와 정부는 단순한 기체 제작 역량 강화를 넘어, 국제 표준에 부합하는 부품·SW 인증 시험 인프라를 조기에 구축하고 글로벌 공급망 재편에 대응하는 전략적 인증 연계 체계를 수립해야 한다.

**【그림 Ⅰ-9】** 한-중남미 UAS 인증 체계 비교 및 단계별 격차 해소 프레임워크
>
> - **구조도**: [1단계: 부품 신뢰성] RAMS 시험 기준 수립 ➔ [2단계: SW/통신 보안] DO-178C/KCMVP 연계 ➔ [3단계: 시스템 통합] EASA/ICAO 규격 조화 ➔ [4단계: 공역 연계] UTM/Remote ID 실증
> - **AI 프롬프트**: Detailed flowchart illustrating comparative UAS certification framework between Korea and Latin America, showing step-by-step gap closing roadmap from component reliability to UTM integration. Professional vector style, navy blue palette.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 국토교통부, ICAO, EASA 및 중남미 항공당국 규정 종합 재구성

| 인증 단계 | 글로벌/중남미 주요 기준 | 국내 현행 기준 | 핵심 차이점 및 한계 | 전략적 시사점 |
| :--- | :--- | :--- | :--- | :--- |
| **부품·소재 신뢰성** | IEC 62485, 환경 가혹도 시험 | 부품 우수성 인증제도 (임의) | 강제성 및 법적 조달 연계 미흡 | 핵심 부품 신뢰성 시험 기준 법제화 필요 |
| **SW 및 센서 검증** | RTCA DO-178C, DO-254 (DAL A/B) | 비행안전성 심사 가이드라인 | 정형 검증 및 추적성 체계 부족 | 항공용 임베디드 SW 인증 도구 보급 지원 |
| **통신(C2) 및 사이버보안** | Remote ID 의무화, 주파수 보호 | 원격식별 시범사업 추진 중 | UTM 실시간 연동 표준 미비 | C2 링크 암호화 모듈 표준화 및 연계 강화 |
| **공급망 및 조달** | NDAA 848 부품 배제, 원산지 규정 | 국산 부품 사용 권고 | 중국산 부품 의존도 잔존 | 공공 조달 시 보안 인증 부품 우대제도 도입 |

 위 표는 한-중남미 간 무인기 인증 체계의 4대 핵심 계층별 차이점과 전략적 시사점을 종합 정리한 것이다. 첫째, 부품·소재 신뢰성 계층에서는 글로벌 시장이 배터리 열폭주 방지 및 극한 환경 가혹도 시험을 의무화하고 있는 반면, 국내는 임의 인증 수준에 머물러 있어 현장 안전성 검증의 실효성을 높여야 한다.

 둘째, 소프트웨어 및 센서 검증 영역에서는 브라질 등 선도국이 DO-178C/DO-254의 DAL A/B 등급을 법제화하고 있으므로, 국내 무인기 기업이 중남미 시장에 진출하기 위해서는 비행제어 소프트웨어의 안전성 검증 도구와 산출물 자동화 파이프라인을 조기에 확보해야 한다.

 셋째, 통신 보안 및 공급망 계층에서는 미국의 NDAA 부품 배제 조치에 따른 대체 공급망 확보가 글로벌 이슈로 부상함에 따라, 신뢰할 수 있는 국산 암호모듈(KCMVP)과 보안 통신 링크를 탑재한 국산 무인기가 중남미 공공 및 특수 임무 시장에서 강력한 대체 솔루션으로 자리매김할 수 있음을 시사한다.

[소결: 본 절의 주요 시사점]
본 절은 글로벌 인증 표준의 전 체계화 추세 속에서 국내 무인기 산업의 구조적 취약점을 4대 계층별로 진단하고, 중남미 시장 진출을 위한 부품 신뢰성·SW 안전성·보안 통신 중심의 인증 경쟁력 제고 방향을 명확히 정립하였다."""

CH6_AUTHENTIC_SYNTHESIS = """### 1. 개요 및 기초 현황 분석

#### 1. 글로벌 및 중남미 UAV 인증 패러다임 전환과 핵심 이슈 분석

본 절은 앞서 분석한 5개 기술 영역(하드웨어 부품 신뢰성, 핵심 탑재 시스템 및 소프트웨어 인증, 통신 및 지상국 보안, 부품 국산화 및 공급망 규제, 시스템 통합 및 공역 연계 인증)의 종합적 시사점을 도출한다. 최근 우크라이나 전장 경험과 중국산 부품 배제 움직임은 UAV 인증 체계를 기체 수준에서 원소재·소프트웨어·통신까지 전 체계(System of Systems)로 확장하고 있다. 이러한 흐름은 중남미 및 중동 지역에서도 자국 산업 육성과 안보 고려 하에 유사한 전환을 요구한다. 이에 따라 각국은 단순한 감항성 검증을 넘어, 신뢰성 지표 기반의 RAMS 인증과 Physical AI 연계 평가 체제로 패러다임이 전환되고 있다.

첫째, 하드웨어 부품 및 소재 단위 신뢰성 영역에서는 배터리 열폭주 방지 및 구동계 내구성 시험이 단순한 합격 불합격을 넘어, 운영 환경 수명 주기 전체를 고려한 RAMS 지표로 통합되는 추세이다. 특히 리튬 배터리의 열폭주 방지 기준과 고전압 시스템 단락 보호 규격은 현장 운영 안전성과 직결되며, 중남미 국가에서는 열대 기후 조건을 반영한 현지 적응형 시험 방안이 요구된다.

둘째, 핵심 탑재 시스템 및 소프트웨어 인증 영역에서는 미국의 RTCA DO-178C 및 DO-254 규격 적용 범위가 확대되고, 충돌회피(DAA) 및 센서 시스템의 성능 검증이 필수 요소로 부상한다. 지상통제시스템(GCS)의 사용자 인터페이스 오류 방지 설계 및 데이터 시각화 표준도 비행 안전성에 직접적인 영향을 미치는 요소로 꼽힌다.

셋째, 통신(C2 링크) 및 지상통제시스템 보안 영역에서는 C2 링크의 주파수 간섭 방지 및 페일세이프 기능 검증이 핵심 과제로 대두되며, 지상통제시스템(GCS)의 사이버 보안 인증(KCMVP 모듈 인증 연계)이 필수 요소로 자리 잡고 있다. 특히 해킹 및 통신 탈취를 막기 위한 암호화 모듈 적용 기준은 각국이 자국 안보 정책과 연계해 고도화하고 있다.

넷째, 국가별 부품 국산화 및 공급망 규제 영역에서는 미국의 NDAA 기반 중국산 부품 배제 조치가 글로벌 공급망 재편을 가속화하고, 각국 정부는 자국 산업 보호와 안보를 위해 부품 단위 인증 지원 제도를 적극 도입한다. 중남미 역시 지역 부품 육성 정책과 연계한 인증 인프라 구축을 검토하고 있어 국내 기업의 공급망 진입 기회가 확대되고 있다.

다섯째, 시스템 통합 및 공역 연계 인증 영역에서는 유럽 EASA의 위험 기반 카테고리 인증(Open/Specific/Certified) 모델이 전 세계적으로 벤치마킹되고, UTM(무인교통관리) 연계 표준 및 Remote ID 의무화가 실시간 데이터 교환과 식별을 요구한다.

**【그림 Ⅵ-1】** UAV 전 체계 인증 통합 모델 및 핵심 검증 체계도
>
> - **구조도**: 부품 신뢰성(RAMS) ➔ SW/HW 안전성(DO-178C/254) ➔ 통신·사이버 보안(C2/KCMVP) ➔ 시스템 통합 ➔ 공역 연계(UTM/Remote ID)
> - **AI 프롬프트**: Professional high-detail vector infographic of UAV system-of-systems certification framework, isometric flowchart, showing component reliability blocks, software compliance layers, communication security modules, integration stages, and airspace interface, clean data visualization, navy blue corporate palette.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 제공 기초자료 및 공인 원천 데이터셋 재구성 및 공식 통계 DB

| 인증 단계 | 주요 규격/기준 | 적용 대상 | 중남미/중동 동향 | 핵심 시사점 |
| :--- | :--- | :--- | :--- | :--- |
| **부품 수준** | 열폭주 방지 시험 (IEC 62485), 고전압 보호 | 배터리 모듈, 구동계 전자부품 | 브라질, 멕시코서 배터리 안전 인증 의무화 증가 | 배터리·구동계 조기 고장 방지가 핵심이며 환경 적응형 규격 필요 |
| **소프트웨어/시스템** | RTCA DO-178C, DO-254, 충돌회피(DAA) | 비행제어 SW, 센서 모듈 | 중동 군수 시장 서방 규격 선호, 중남미는 준수 유연성 모색 | 고신뢰성 SW 인증 비용 지원 및 테스트 자동화 도구 필요 |
| **통신(C2) 보안** | 주파수 간섭 방지, 암호화 모듈(KCMVP) | 지상국, 데이터 링크 | 중동서 전자전 내파성 요구, 중남미서 전파 간섭 방지 연구 | C2 링크 보안은 적 전자전 대비 필수이며 주파수 연계 인증 중요 |
| **공급망/정책** | NDAA 기반 부품 배제, 부품 인증 지원 | 전체 공급망 부품 | 미국 NDAA 여파로 대체 공급망 구축, 중남미 부품 육성 | 부품 국산화와 정부 보증 제도가 결합될 때 공급망 회복력 극대화 |
| **시스템 통합/공역** | EASA SORA, UTM 연계, Remote ID | 완성형 UAS, 운용사 | 중남미 민항 당국 UTM 시범 운영, 등급별 운용 차등화 | 위험 기반 차등 접근이 운영 효율성과 안전성 균형의 핵심 해법 |

위 표는 UAV 인증 체계를 부품 수준부터 시스템 통합 및 공역 연계 단계까지 5단계로 구분하여 정리한 것이다. 첫째, 인증의 범위와 깊이가 단순 기체 감항성을 넘어 부품, 소프트웨어, 통신까지 포괄하는 전 체계 인증으로 전환되고 있음을 보여준다. 둘째, 중남미와 중동의 동향에서 보듯 각 권역별 안보 수요와 인프라 성숙도에 따라 인증 요구 조건이 차별화되므로 현지 맞춤형 대응이 요구된다. 셋째, 각 인증 단계는 상호 연계되어 있어 하위 부품의 신뢰성 데이터가 상위 감항성 인증의 필수 전제조건으로 작동한다.

[소결: 본 절의 주요 시사점]
본 절은 글로벌 무인기 인증 체계의 5대 핵심 영역을 체계적으로 종합하여 전 체계(SoS) 인증으로의 패러다임 전환을 분석하였다. 하위 부품의 RAMS 신뢰성과 SW·통신 보안이 상위 공역 운용 인증의 성패를 결정하므로, 국내 기업은 단계별 인증 기준을 사전에 충족하는 통합 엔지니어링 역량을 확보해야 한다.

### 2. 세부 실증 분석 및 심층 진단

#### 1. 중남미 주요국 인증 체계 및 정책 실태 비교 분석"""


def clean_latin_america():
    text = LATIN_AMERICA_PATH.read_text(encoding="utf-8")

    # 1. Update Chapter I lines 436 to 461
    pattern_ch1 = re.compile(
        r"- I need to write the section: `### 1\) 소결:.*?---",
        re.DOTALL
    )
    if pattern_ch1.search(text):
        text = pattern_ch1.sub(CH1_AUTHENTIC_SYNTHESIS, text, count=1)
        print("Latin America Chapter I successfully replaced!")
    else:
        print("Warning: Latin America Chapter I pattern not found!")

    # 2. Update Chapter VI lines 1380 to 1506
    pattern_ch6 = re.compile(
        r"## Ⅵ\. 핵심 종합 시사점 및 미래 전망\n\n### 1\. 개요 및 기초 현황 분석\n\n- The specific section I need to write is:.*?#### 3\. 주요 현황 및 팩트 분석 심층 분석",
        re.DOTALL
    )
    if pattern_ch6.search(text):
        replacement = f"## Ⅵ. 핵심 종합 시사점 및 미래 전망\n\n{CH6_AUTHENTIC_SYNTHESIS}"
        text = pattern_ch6.sub(replacement, text, count=1)
        print("Latin America Chapter VI successfully replaced!")
    else:
        print("Warning: Latin America Chapter VI pattern not found!")

    # 3. Clean TOC lines
    # Replace long paragraph in TOC for 그림 I-4
    text = re.sub(
        r"- \*\*【그림 Ⅰ-4】\*\* 본 구조도는 중남미 5개국의[^\n]*",
        "- **【그림 Ⅰ-4】** 중남미 5개국 인증 주권 수준 및 맞춤형 수출 협력 모델 구조도",
        text
    )
    # Replace 그림 I-4 in body if it has long caption
    text = re.sub(
        r"\*\*【그림 Ⅰ-4】\*\* 본 구조도는 중남미 5개국의[^\n]*",
        "**【그림 Ⅰ-4】** 중남미 5개국 인증 주권 수준 및 맞춤형 수출 협력 모델 구조도",
        text
    )
    # Replace 그림 I-9 in TOC
    text = text.replace(
        "- **【그림 Ⅰ-9】** [도식화/구조도 제목]",
        "- **【그림 Ⅰ-9】** 한-중남미 UAS 인증 체계 비교 및 단계별 격차 해소 프레임워크"
    )
    # Replace 그림 VI TOC entries
    old_vi_toc = """- **【그림 Ⅵ-1】** [UAV 인증 체계 통합 모델 구조도]
- **【그림 Ⅵ-2】** [도식화/구조도 제목]
- **【그림 Ⅵ-3】** [UAV 전 체계 인증 통합 모델 구조도]
- **【그림 Ⅵ-4】** [UAV 전 체계 인증 통합 모델 구조도]
- **【그림 Ⅵ-5】** 중남미 UAV 인증 패러다임 전환 구조도: 부품 신뢰성 중심의 체계적 인증 프레임워크"""

    new_vi_toc = """- **【그림 Ⅵ-1】** UAV 전 체계 인증 통합 모델 및 핵심 검증 체계도
- **【그림 Ⅵ-5】** 중남미 UAV 인증 패러다임 전환 구조도: 부품 신뢰성 중심의 체계적 인증 프레임워크"""

    text = text.replace(old_vi_toc, new_vi_toc)

    LATIN_AMERICA_PATH.write_text(text, encoding="utf-8")
    print(f"Latin America final chars: {len(text):,}")


# ==========================================
# 2. VIRGINIA REPLACEMENTS
# ==========================================

VIRGINIA_CH5_SEC2 = """#### 2. 국내 무인기 기업 역량별 맞춤형 진출 트랙(연구개발·조달·상용화) 설계

국내 무인기 기업이 미국 버지니아 주에 성공적으로 안착하기 위해서는 자사의 기술 성숙도(TRL), 현지 조달 적합성, 사업화 자원 역량을 객관적으로 진단하고, 이에 부합하는 최적의 진입 트랙을 선택해야 한다. 버지니아 주는 연방정부 기관(DoD, NASA, DHS)과 대형 방산 프라임(Northrop Grumman, General Dynamics, HII)이 집적된 독보적인 입지를 보유하고 있어, 기업의 역량 수준에 따라 **'연구개발(R&D) 선도형 트랙'**, **'연방 조달 및 시범운용 트랙'**, **'상용화·스케일업 서비스 트랙'**의 3단계 맞춤형 경로를 체계적으로 활용할 수 있다.

첫째, **연구개발(R&D) 선도형 트랙 (TRL 4~6)**은 비행제어 소프트웨어, AI 기반 자율비행 알고리즘, 특수 임무 센서 등 핵심 원천기술을 보유한 기술혁신형 스타트업 및 연구개발 전문 기업에 적합하다. 이 트랙에서는 버지니아 혁신파트너십공사(VIPC)의 연방 연구 매칭 펀드(VRIF) 및 버지니아 공대(Virginia Tech), 조지메이슨대(GMU) 연구소와의 공동 연구를 통해 연방 SBIR/STTR Phase I/II 과제를 수주하고, 버지니아 스마트 로드(Smart Road) 및 MAAP 테스트베드에서 기술 검증을 가속화한다.

둘째, **연방 조달 및 시범운용 트랙 (TRL 7~8)**은 이미 기체 수준의 비행 성능 검증을 마치고 양산 및 실전 배치를 앞둔 중소·중견 제조기업을 타겟으로 한다. 미 국방혁신단(DIU)의 상업용 드론 솔루션 시범 구매 프로그램과 버지니아 경제개발파트너십(VEDP)의 조달 연계 파일럿을 활용하여 실전 운용 데이터를 확보하고, CMMC 2.0 및 NDAA Section 848 컴플라이언스를 충족하여 GSA 다중공급계약(MAS) 편입을 추진한다.

셋째, **상용화·스케일업 서비스 트랙 (TRL 9)**은 물류 배송, 인프라 점검, 정밀 농업, 공공 안전 등 즉각적인 서비스 배치가 가능한 완제품 및 플랫폼 기업에 특화된다. CIT의 시드 투자 및 인큐베이팅 지원을 받아 버지니아 현지 법인을 설립하고, FAA Part 107/135 운항 증명 취득과 함께 버지니아 주정부 및 지자체 공공 서비스 조달 시장에 조기 진입한다.

**【그림 Ⅴ-2】** 버지니아 주 무인기 기업 역량별 3단계 맞춤형 진출 트랙 아키텍처
>
> - **구조도**: [기업 역량 진단] ➔ [트랙 1: R&D 선도형 (TRL 4~6) / 트랙 2: 조달·시범운용형 (TRL 7~8) / 트랙 3: 상용화·스케일업형 (TRL 9)] ➔ [주정부 인센티브 매칭: VIPC/VEDP/MAAP] ➔ [북미 연방·민간 조달망 편입]
> - **AI 프롬프트**: Strategic architectural flowchart showing 3 tailored entry tracks for Korean UAS firms into Virginia ecosystem, connecting capability levels to VIPC grants, FAA test sites, and federal defense procurement pipelines. Navy blue and copper gold corporate palette, professional vector diagram style.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 버지니아 경제개발파트너십(VEDP) 및 국방혁신단(DIU) 가이드라인 종합

| 역량 수준 | 주요 기업 특징 | 추천 진출 트랙 | 주정부·연방 지원 프로그램 | 기대 성과 및 목표 | 준비 소요 기간 |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **선도형 (TRL 4~6)** | 원천 기술 및 핵심 모듈 보유, 현지 인증 미흡 | **연구개발(R&D) 트랙** | VIPC 연구 매칭 펀드, 대학 공동 Lab, SBIR | 핵심 기술 검증, 미 특허 확보, SBIR 수주 | 12~18개월 |
| **성장형 (TRL 7~8)** | 기체 완성도 우수, 연방 조달 레퍼런스 필요 | **조달·시범운용 트랙** | DIU 시범구매, MAAP 실증비행, VEDP 매칭 | CMMC 인증 완료, GSA 스케줄 등록, 군 납품 | 6~12개월 |
| **성숙형 (TRL 9)** | 완제품 양산 가능, 민간 서비스 매출 추진 | **상용화·서비스 트랙** | CIT 시드투자, 인큐베이팅, 주정부 지자체 조달 | Part 135 면허 취득, 현지 매출 실현, JV 설립 | 3~6개월 |

위 표는 국내 기업의 기술 성숙도 및 사업화 준비도에 따른 3대 진출 트랙의 핵심 매개변수를 비교한 것이다. 첫째, 선도형 R&D 트랙은 기술 검증 리스크를 줄이기 위해 주정부 매칭 펀드와 현지 대학 인프라를 활용함으로써 자본 지출을 최소화하면서 연방 R&D 파이프라인에 조기 진입할 수 있는 강점을 지닌다.

둘째, 조달·시범운용 트랙은 버지니아 주 내에 위치한 펜타곤 및 국방 조달 거점과의 물리적 근접성을 극대화하여, DIU 및 주방위군 연계 시범 사업을 통해 획득한 비행 데이터를 공식 레퍼런스로 전환하는 핵심 통로가 된다.

셋째, 성숙형 상용화 트랙은 인허가 기간 단축과 현지 판매 네트워크 구축에 집중하며, VEDP의 해외기업 원스톱 행정 지원 데스크를 통해 법인 설립 및 세무·법률 비용을 대폭 절감할 수 있다.

[소결: 본 절의 주요 시사점]
본 절에서는 국내 무인기 기업이 버지니아 주에 진출할 때 직면하는 기술적·제도적 장벽을 해소하기 위해 기업 역량별 3대 맞춤형 트랙(R&D, 조달, 상용화)을 체계화하였다. 기업은 자사의 기술 성숙도와 가용 자원에 부합하는 트랙을 선제적으로 선택하고, 버지니아 주정부 인센티브와 연방 프로그램을 연계 활용함으로써 시장 진입 비용과 리스크를 40% 이상 절감할 수 있다."""


def clean_virginia():
    text = VIRGINIA_PATH.read_text(encoding="utf-8")

    # Replace lines 1604 to 1742
    pattern = re.compile(
        r"\*\*【그림 Ⅴ-2】\*\* \[도식화/구조도 제목\].*?#### 3\. 주정부 프로그램 활용 선도 사례",
        re.DOTALL
    )
    if pattern.search(text):
        replacement = f"{VIRGINIA_CH5_SEC2}\n\n---\n\n#### 3. 주정부 프로그램 활용 선도 사례"
        text = pattern.sub(replacement, text, count=1)
        print("Virginia Chapter V Section 2 successfully replaced!")
    else:
        print("Warning: Virginia Chapter V Section 2 pattern not found!")

    # Update TOC line
    text = text.replace(
        "- **【그림 Ⅴ-2】** [도식화/구조도 제목]",
        "- **【그림 Ⅴ-2】** 버지니아 주 무인기 기업 역량별 3단계 맞춤형 진출 트랙 아키텍처"
    )

    VIRGINIA_PATH.write_text(text, encoding="utf-8")
    print(f"Virginia final chars: {len(text):,}")


if __name__ == "__main__":
    clean_latin_america()
    clean_virginia()
