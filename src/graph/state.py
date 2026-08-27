from typing import TypedDict, NotRequired, Any

# 병렬 처리를 지원하는 상태 스키마 뼈대
class ReportState(TypedDict):
    topic: str
    direction: str
    target_perspective: str
    is_blank_slate: bool
    source_materials: NotRequired[list[Any]]
    reference_paths: NotRequired[list[str]]
    keywords: NotRequired[list[str]]
    sections: NotRequired[list[dict[str, Any]]]
    expanded_sections: NotRequired[list[dict[str, Any]]]
    foundation_report_path: NotRequired[str]
    loop_count: NotRequired[int]
    max_loops: NotRequired[int]
    max_concurrency: NotRequired[int]
    target_sections_for_loop: NotRequired[list[str]]
    target_6_min_length: NotRequired[int]
    target_total_min_length: NotRequired[int]
    next_step: NotRequired[str]
    final_report_path: NotRequired[str]
