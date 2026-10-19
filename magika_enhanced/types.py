"""
Type definitions for magika-enhanced.

Re-exports core types from magika for compatibility, plus enhanced types.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

# Re-export from upstream magika
try:
    from magika.types import (
        ContentTypeInfo as _ContentTypeInfo,
        ContentTypeLabel as _ContentTypeLabel,
        MagikaError as _MagikaError,
        MagikaPrediction as _MagikaPrediction,
        MagikaResult as _MagikaResult,
        OverwriteReason as _OverwriteReason,
        PredictionMode as _PredictionMode,
        Status as _Status,
    )

    ContentTypeInfo = _ContentTypeInfo
    ContentTypeLabel = _ContentTypeLabel
    MagikaError = _MagikaError
    MagikaPrediction = _MagikaPrediction
    MagikaResult = _MagikaResult
    OverwriteReason = _OverwriteReason
    PredictionMode = _PredictionMode
    Status = _Status
except ImportError:
    # Fallback definitions for when magika is not installed
    class ContentTypeLabel(str, Enum):
        UNKNOWN = "unknown"
        EMPTY = "empty"
        DIRECTORY = "directory"
        SYMLINK = "symlink"
        TEXT = "text"
        BINARY = "binary"
        # ... other labels would be defined here

    class Status(str, Enum):
        OK = "ok"
        FILE_NOT_FOUND_ERROR = "file_not_found_error"
        PERMISSION_ERROR = "permission_error"
        UNKNOWN = "unknown"

    class PredictionMode(str, Enum):
        BEST_GUESS = "best_guess"
        MEDIUM_CONFIDENCE = "medium_confidence"
        HIGH_CONFIDENCE = "high_confidence"

    class OverwriteReason(str, Enum):
        NONE = "none"
        LOW_CONFIDENCE = "low_confidence"
        OVERWRITE_MAP = "overwrite_map"
        RULES_VETO = "rules_veto"

    @dataclass
    class ContentTypeInfo:
        label: ContentTypeLabel
        mime_type: str
        group: str
        description: str
        extensions: List[str]
        is_text: bool

    @dataclass
    class MagikaPrediction:
        dl: ContentTypeInfo
        output: ContentTypeInfo
        score: float
        overwrite_reason: OverwriteReason

    @dataclass
    class MagikaResult:
        path: Path
        status: Status
        prediction: Optional[MagikaPrediction] = None

    class MagikaError(Exception):
        pass


# Enhanced types for magika-enhanced
@dataclass
class RuleMatch:
    """Result of a custom rule match."""
    rule_name: str
    label: ContentTypeLabel
    confidence: float
    matched_by: str  # "magic_bytes", "regex", "extension", "structure"


@dataclass
class BatchResult:
    """Result of batch identification."""
    results: List[MagikaResult]
    total_files: int
    successful: int
    failed: int
    elapsed_seconds: float


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    tool_name: str
    total_files: int
    total_time_seconds: float
    avg_time_per_file_ms: float
    accuracy: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    throughput_files_per_sec: Optional[float] = None


PathLike = Union[str, Path]
PathsLike = Sequence[PathLike]