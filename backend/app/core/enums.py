from enum import Enum


class AnalysisStatus(str, Enum):
    """Lifecycle states for a clinical document analysis.

    Terminal states are COMPLETED and FAILED. See
    docs/architecture/system-architecture.md for the full state
    transition diagram.
    """

    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_ANALYSIS_STATUSES = frozenset({AnalysisStatus.COMPLETED, AnalysisStatus.FAILED})

# Explicit allow-list of forward transitions. Any status may transition to
# FAILED; terminal statuses have no outgoing transitions.
ANALYSIS_STATUS_TRANSITIONS: dict[AnalysisStatus, frozenset[AnalysisStatus]] = {
    AnalysisStatus.PENDING: frozenset({AnalysisStatus.VALIDATING, AnalysisStatus.FAILED}),
    AnalysisStatus.VALIDATING: frozenset({AnalysisStatus.EXTRACTING, AnalysisStatus.FAILED}),
    AnalysisStatus.EXTRACTING: frozenset({AnalysisStatus.ANALYZING, AnalysisStatus.FAILED}),
    AnalysisStatus.ANALYZING: frozenset({AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}),
    AnalysisStatus.COMPLETED: frozenset(),
    AnalysisStatus.FAILED: frozenset(),
}


class DocumentSourceType(str, Enum):
    """How the source clinical document was submitted."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    PDF = "PDF"


class ProcessingEventType(str, Enum):
    """Discrete, auditable events recorded during an analysis lifecycle."""

    STATUS_CHANGED = "STATUS_CHANGED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    AI_ANALYSIS_STARTED = "AI_ANALYSIS_STARTED"
    AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED"
    AI_ANALYSIS_FAILED = "AI_ANALYSIS_FAILED"
    REPORT_PERSISTED = "REPORT_PERSISTED"
    ERROR = "ERROR"
