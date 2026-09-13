"""Model client and deterministic fallback engines."""
from src.models.client import UnifiedModelClient, ModelGenerationResult
from src.models.fallback_engine import (
    generate_fallback_outline,
    generate_fallback_section,
    generate_fallback_citations_glossary,
)

__all__ = [
    "UnifiedModelClient",
    "ModelGenerationResult",
    "generate_fallback_outline",
    "generate_fallback_section",
    "generate_fallback_citations_glossary",
]

