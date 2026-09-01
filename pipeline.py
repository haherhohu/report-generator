import asyncio
from pydantic import BaseModel, Field
from typing import List, Dict

# 1. 워커 노드 출력 스키마 (라우터 및 워커의 포맷 강제용)
# NIM(Llama/Nemotron) API 호출 시 response_format 또는 파서(Parser)에 주입합니다.
class ChapterResult(BaseModel):
    chapter_id: int
    content: str
    context_for_next: List[str] = Field(
        default_factory=list, 
        description="다음 장으로 넘길 핵심 맥락 (논리적 연결이 필요한 경우에만 작성)"
    )

# 2. 워커 노드 실행 함수 (LLM API 비동기 호출부)
async def generate_chapter(chapter_id: int, previous_context: List[str] = None) -> ChapterResult:
    # 실제 구현 시: 
    # 1. previous_context가 있으면 시스템 프롬프트 상단에 '이전 장 결론'으로 주입
    # 2. Llama/Nemotron API 비동기(Async) 호출 
    
    print(f"[진행] {chapter_id}장 워커 구동 시작... " + 
          (f"(수신된 이전 맥락: {len(previous_context)}건)" if previous_context else "(단독 실행)"))
    
    await asyncio.sleep(2) # LLM API 응답 대기 시간 시뮬레이션
    
    # 4장, 5장은 다음 장을 위해 논리를 요약해 반환하도록 지시
    context_out = []
    if chapter_id in [4, 5]:
        context_out = [f"{chapter_id}장에서 도출된 핵심 논리 A", f"{chapter_id}장의 결론 B"]
        
    print(f"[완료] {chapter_id}장 생성 완료")
    return ChapterResult(
        chapter_id=chapter_id, 
        content=f"{chapter_id}장 본문 내용...", 
        context_for_next=context_out
    )

# 3. 메인 오케스트레이터 (DAG 제어 흐름 강제)
async def run_pipeline():
    print("=== 파이프라인 구동 시작 ===")
    results: Dict[int, ChapterResult] = {}

    # [Group A & C] 완전 독립 병렬 그룹 (2, 3, 7, 8, 9장)
    # Task로 감싸 백그라운드에 던져 즉시 동시 실행시킵니다.
    parallel_chapters = [2, 3, 7, 8, 9]
    parallel_tasks = {
        cid: asyncio.create_task(generate_chapter(cid))
        for cid in parallel_chapters
    }

    # [Group B] 인과 논리 체인 순차 실행 (4 -> 5 -> 6장)
    # await 키워드를 통해 앞 장의 결과(context_for_next)가 나와야만 다음 장 프롬프트에 주입되도록 강제합니다.
    results[4] = await generate_chapter(4)
    results[5] = await generate_chapter(5, previous_context=results[4].context_for_next)
    results[6] = await generate_chapter(6, previous_context=results[5].context_for_next)

    # [Fan-in 대기] 병렬로 돌려둔 A, C 그룹의 작업이 모두 끝날 때까지 여기서 대기합니다.
    for cid, task in parallel_tasks.items():
        results[cid] = await task

    # [Group D] 최종 수렴 (1장 개요)
    # 2~9장의 모든 content가 확보된 상태이므로, 이를 요약하여 1장 워커에게 넘깁니다.
    print("\n[동기화] 모든 본문(2~9장) 생성 완료. 1장(개요 및 요약) 작성을 시작합니다.")
    
    # 실제 구현 시: results 딕셔너리의 내용을 취합하여 요약 후 주입
    results[1] = await generate_chapter(1, previous_context=["2~9장 전체 요약본"])
    
    print("=== 파이프라인 구동 완료 ===")
    return results

# 실행 엔트리포인트
# if __name__ == "__main__":
#     final_report = asyncio.run(run_pipeline())