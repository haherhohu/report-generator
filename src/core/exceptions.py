"""Custom exceptions for the report generation pipeline."""

class ReportPipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class ConfigurationError(ReportPipelineError):
    """Raised when configuration files or environment variables are invalid."""
    pass

class ModelInvocationError(ReportPipelineError):
    """Raised when an AI model fails after all retries and fallbacks."""
    pass

class GatekeeperError(ReportPipelineError):
    """Raised when gatekeeper loop or quality control detects an unrecoverable issue."""
    pass

class PreprocessingError(ReportPipelineError):
    """Raised when source documents cannot be parsed or preprocessed."""
    pass

