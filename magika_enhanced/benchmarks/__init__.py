"""
Benchmarking module for magika-enhanced.
"""

from __future__ import annotations

from magika_enhanced.benchmarks.runner import (
    BenchmarkConfig,
    BenchmarkMetrics,
    BenchmarkRunner,
    create_benchmark_fixture,
)

__all__ = [
    "BenchmarkConfig",
    "BenchmarkMetrics",
    "BenchmarkRunner",
    "create_benchmark_fixture",
]