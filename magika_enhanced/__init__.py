"""
magika-enhanced: Enhanced AI-powered file type detection.

This package provides async API, custom rules engine, and MCP server integration
on top of Google's Magika.
"""

from __future__ import annotations

from magika_enhanced.core.magika_async import MagikaAsync
from magika_enhanced.core.magika_sync import Magika
from magika_enhanced.rules.engine import CustomRules, Rule, RuleSet
from magika_enhanced.types import (
    ContentTypeInfo,
    ContentTypeLabel,
    MagikaError,
    MagikaPrediction,
    MagikaResult,
    OverwriteReason,
    PredictionMode,
    Status,
)

__version__ = "0.1.0"
__author__ = "George Nakisisa"
__email__ = "nakisisageorge@gmail.com"
__license__ = "Apache-2.0"

__all__ = [
    # Core classes
    "Magika",
    "MagikaAsync",
    # Rules engine
    "CustomRules",
    "Rule",
    "RuleSet",
    # Types (re-exported from magika for compatibility)
    "ContentTypeInfo",
    "ContentTypeLabel",
    "MagikaError",
    "MagikaPrediction",
    "MagikaResult",
    "OverwriteReason",
    "PredictionMode",
    "Status",
]