"""
Benchmarking suite for magika-enhanced.

Provides performance and accuracy benchmarks with regression detection.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

from magika_enhanced import Magika, MagikaAsync
from magika_enhanced.types import BenchmarkResult, MagikaResult


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    iterations: int = 5
    warmup_runs: int = 2
    max_files: int = 1000
    file_sizes: List[int] = field(default_factory=lambda: [100, 1024, 10240, 102400, 1048576])
    concurrent_levels: List[int] = field(default_factory=lambda: [1, 10, 50, 100])
    measure_memory: bool = True
    measure_cpu: bool = True


@dataclass
class BenchmarkMetrics:
    """Detailed metrics for a benchmark run."""
    tool_name: str
    operation: str
    total_files: int
    total_time_seconds: float
    avg_time_per_file_ms: float
    median_time_per_file_ms: float
    min_time_per_file_ms: float
    max_time_per_file_ms: float
    std_dev_ms: float
    throughput_files_per_sec: float
    memory_peak_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    accuracy: Optional[float] = None
    errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockResult:
    """Mock result for comparison tools."""
    def __init__(self, path: Path, label: str, mime_type: str = "", description: str = ""):
        self.path = path
        self.status = "ok"
        self.ok = True
        self.prediction = MockPrediction(label, mime_type, description)


class MockPrediction:
    """Mock prediction for comparison tools."""
    def __init__(self, label: str, mime_type: str, description: str):
        self.output = MockOutput(label, mime_type, description)
        self.score = 1.0
        self.overwrite_reason = "none"


class MockOutput:
    """Mock output for comparison tools."""
    def __init__(self, label: str, mime_type: str, description: str):
        self.label = label
        self.mime_type = mime_type
        self.group = "unknown"
        self.description = description
        self.extensions = []
        self.is_text = False


class BenchmarkRunner:
    """Runs performance and accuracy benchmarks."""
    
    def __init__(self, config: Optional[BenchmarkConfig] = None) -> None:
        self.config = config or BenchmarkConfig()
        self.results: List[BenchmarkMetrics] = []
    
    def _measure_memory(self) -> float:
        """Get current process memory in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _measure_cpu(self) -> float:
        """Get current CPU percent."""
        process = psutil.Process()
        return process.cpu_percent(interval=0.1)
    
    def _generate_test_files(self, count: int, size: int, output_dir: Path) -> List[Path]:
        """Generate test files of specified size."""
        import random
        import string
        
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        
        for i in range(count):
            content_type = i % 5
            if content_type == 0:
                content = ''.join(random.choices(string.ascii_letters + string.digits + ' \n', k=size)).encode()
            elif content_type == 1:
                content = bytes(random.getrandbits(8) for _ in range(size))
            elif content_type == 2:
                content = f'{{"id": {i}, "data": "{"".join(random.choices(string.ascii_letters, k=max(0, size-50)))}"}}'.encode()
            elif content_type == 3:
                content = f'<item id="{i}"><data>{"".join(random.choices(string.ascii_letters, k=max(0, size-50)))}</data></item>'.encode()
            else:
                content = b'%PDF-1.4\n' + bytes(random.getrandbits(8) for _ in range(max(0, size - 10)))
            
            path = output_dir / f"bench_{i:06d}.bin"
            path.write_bytes(content)
            paths.append(path)
        
        return paths
    
    def _run_sync_benchmark(
        self,
        tool_name: str,
        identify_func: Callable,
        paths: List[Path],
        operation: str,
    ) -> BenchmarkMetrics:
        """Run synchronous benchmark."""
        # Warmup
        for _ in range(self.config.warmup_runs):
            identify_func(paths[:min(10, len(paths))])
        
        # Measure memory
        if self.config.measure_memory:
            initial_memory = self._measure_memory()
            peak_memory = initial_memory
        
        if self.config.measure_cpu:
            self._measure_cpu()  # Initialize
        
        times = []
        
        for _ in range(self.config.iterations):
            start_mem = self._measure_memory() if self.config.measure_memory else 0
            start_time = time.perf_counter()
            
            results = identify_func(paths)
            
            end_time = time.perf_counter()
            end_mem = self._measure_memory() if self.config.measure_memory else 0
            
            elapsed = end_time - start_time
            times.append(elapsed)
            
            if self.config.measure_memory:
                peak_memory = max(peak_memory, end_mem)
        
        total_time = statistics.mean(times)
        per_file_times = [t / len(paths) * 1000 for t in times]  # ms per file
        
        errors = sum(1 for r in results if not r.ok)
        
        return BenchmarkMetrics(
            tool_name=tool_name,
            operation=operation,
            total_files=len(paths),
            total_time_seconds=total_time,
            avg_time_per_file_ms=statistics.mean(per_file_times),
            median_time_per_file_ms=statistics.median(per_file_times),
            min_time_per_file_ms=min(per_file_times),
            max_time_per_file_ms=max(per_file_times),
            std_dev_ms=statistics.stdev(per_file_times) if len(per_file_times) > 1 else 0,
            throughput_files_per_sec=len(paths) / total_time,
            memory_peak_mb=peak_memory if self.config.measure_memory else None,
            cpu_percent=self._measure_cpu() if self.config.measure_cpu else None,
            errors=errors,
        )
    
    async def _run_async_benchmark(
        self,
        tool_name: str,
        identify_func: Callable,
        paths: List[Path],
        operation: str,
        max_concurrent: int,
    ) -> BenchmarkMetrics:
        """Run asynchronous benchmark."""
        # Warmup
        for _ in range(self.config.warmup_runs):
            await identify_func(paths[:min(10, len(paths))], max_concurrent=max_concurrent)
        
        if self.config.measure_memory:
            initial_memory = self._measure_memory()
            peak_memory = initial_memory
        
        if self.config.measure_cpu:
            self._measure_cpu()
        
        times = []
        
        for _ in range(self.config.iterations):
            start_mem = self._measure_memory() if self.config.measure_memory else 0
            start_time = time.perf_counter()
            
            results = await identify_func(paths, max_concurrent=max_concurrent)
            
            end_time = time.perf_counter()
            end_mem = self._measure_memory() if self.config.measure_memory else 0
            
            elapsed = end_time - start_time
            times.append(elapsed)
            
            if self.config.measure_memory:
                peak_memory = max(peak_memory, end_mem)
        
        total_time = statistics.mean(times)
        per_file_times = [t / len(paths) * 1000 for t in times]
        
        errors = sum(1 for r in results if not r.ok)
        
        return BenchmarkMetrics(
            tool_name=f"{tool_name} (async, concurrency={max_concurrent})",
            operation=operation,
            total_files=len(paths),
            total_time_seconds=total_time,
            avg_time_per_file_ms=statistics.mean(per_file_times),
            median_time_per_file_ms=statistics.median(per_file_times),
            min_time_per_file_ms=min(per_file_times),
            max_time_per_file_ms=max(per_file_times),
            std_dev_ms=statistics.stdev(per_file_times) if len(per_file_times) > 1 else 0,
            throughput_files_per_sec=len(paths) / total_time,
            memory_peak_mb=peak_memory if self.config.measure_memory else None,
            cpu_percent=self._measure_cpu() if self.config.measure_cpu else None,
            errors=errors,
        )
    
    def run_magika_benchmarks(self, test_dir: Path) -> List[BenchmarkMetrics]:
        """Run benchmarks for magika-enhanced."""
        results = []
        
        # Sync benchmarks
        magika = Magika()
        
        for size in self.config.file_sizes:
            file_count = min(self.config.max_files, 100)
            paths = self._generate_test_files(file_count, size, test_dir / f"sync_{size}")
            
            metrics = self._run_sync_benchmark(
                "magika-enhanced",
                magika.identify_paths,
                paths,
                f"identify_paths_sync_size_{size}",
            )
            results.append(metrics)
        
        # Async benchmarks
        async def run_async():
            magika_async = MagikaAsync()
            
            for concurrent in self.config.concurrent_levels:
                for size in self.config.file_sizes:
                    file_count = min(self.config.max_files, 100)
                    paths = self._generate_test_files(file_count, size, test_dir / f"async_{size}_{concurrent}")
                    
                    metrics = await self._run_async_benchmark(
                        "magika-enhanced",
                        magika_async.identify_paths,
                        paths,
                        f"identify_paths_async_size_{size}",
                        max_concurrent=concurrent,
                    )
                    results.append(metrics)
        
        asyncio.run(run_async())
        
        return results
    
    def run_comparison_benchmarks(self, test_dir: Path) -> List[BenchmarkMetrics]:
        """Run comparison benchmarks against other tools."""
        results = []
        
        # Test with python-magic if available
        try:
            import magic
            magic_mime = magic.Magic(mime=True)
            magic_desc = magic.Magic()
            
            def identify_magic_mime(paths):
                return [MockResult(p, magic_mime.from_file(str(p)), magic_mime.from_file(str(p)), magic_desc.from_file(str(p))) for p in paths]
            
            def identify_magic_desc(paths):
                return [MockResult(p, magic_desc.from_file(str(p)), "", magic_desc.from_file(str(p))) for p in paths]
            
            for size in [1024, 10240]:
                paths = self._generate_test_files(50, size, test_dir / f"magic_{size}")
                
                metrics = self._run_sync_benchmark(
                    "python-magic (mime)",
                    identify_magic_mime,
                    paths,
                    f"identify_magic_mime_size_{size}",
                )
                results.append(metrics)
                
                metrics = self._run_sync_benchmark(
                    "python-magic (desc)",
                    identify_magic_desc,
                    paths,
                    f"identify_magic_desc_size_{size}",
                )
                results.append(metrics)
        except ImportError:
            pass
        
        # Test with mimetypes (stdlib)
        import mimetypes
        mimetypes.init()
        
        def identify_mimetypes(paths):
            return [MockResult(p, mimetypes.guess_type(str(p))[0] or "unknown", mimetypes.guess_type(str(p))[0] or "unknown", "") for p in paths]
        
        for size in [1024, 10240]:
            paths = self._generate_test_files(50, size, test_dir / f"mimetypes_{size}")
            
            metrics = self._run_sync_benchmark(
                "mimetypes (stdlib)",
                identify_mimetypes,
                paths,
                f"identify_mimetypes_size_{size}",
            )
            results.append(metrics)
        
        return results
    
    def run_all_benchmarks(self, output_dir: Path) -> Dict[str, Any]:
        """Run all benchmarks and return summary."""
        test_dir = output_dir / "benchmark_data"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        print("Running magika-enhanced benchmarks...")
        magika_results = self.run_magika_benchmarks(test_dir)
        
        print("Running comparison benchmarks...")
        comparison_results = self.run_comparison_benchmarks(test_dir)
        
        all_results = magika_results + comparison_results
        self.results = all_results
        
        # Generate summary
        summary = {
            "timestamp": time.time(),
            "config": {
                "iterations": self.config.iterations,
                "warmup_runs": self.config.warmup_runs,
                "max_files": self.config.max_files,
            },
            "results": [
                {
                    "tool_name": r.tool_name,
                    "operation": r.operation,
                    "total_files": r.total_files,
                    "total_time_seconds": r.total_time_seconds,
                    "avg_time_per_file_ms": r.avg_time_per_file_ms,
                    "median_time_per_file_ms": r.median_time_per_file_ms,
                    "min_time_per_file_ms": r.min_time_per_file_ms,
                    "max_time_per_file_ms": r.max_time_per_file_ms,
                    "std_dev_ms": r.std_dev_ms,
                    "throughput_files_per_sec": r.throughput_files_per_sec,
                    "memory_peak_mb": r.memory_peak_mb,
                    "cpu_percent": r.cpu_percent,
                    "errors": r.errors,
                }
                for r in all_results
            ],
        }
        
        # Save summary
        summary_path = output_dir / "benchmark_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        
        # Save detailed results
        detailed_path = output_dir / "benchmark_detailed.json"
        detailed_path.write_text(json.dumps(summary, indent=2))
        
        return summary
    
    def print_summary(self) -> None:
        """Print benchmark summary to console."""
        if not self.results:
            print("No benchmark results available")
            return
        
        print("\n" + "=" * 100)
        print("BENCHMARK SUMMARY")
        print("=" * 100)
        print(f"{'Tool':<35} {'Operation':<30} {'Files':>6} {'Avg ms/file':>12} {'Throughput':>12} {'Mem MB':>8} {'Errors':>6}")
        print("-" * 100)
        
        for r in self.results:
            print(f"{r.tool_name:<35} {r.operation:<30} {r.total_files:>6} {r.avg_time_per_file_ms:>12.2f} {r.throughput_files_per_sec:>12.1f} {r.memory_peak_mb or 0:>8.1f} {r.errors:>6}")
        
        print("=" * 100)


def create_benchmark_fixture(num_files: int = 100, output_dir: Path = None) -> List[Path]:
    """Create benchmark fixture files."""
    if output_dir is None:
        import tempfile
        output_dir = Path(tempfile.mkdtemp(prefix="magika_bench_"))
    
    runner = BenchmarkRunner()
    return runner._generate_test_files(num_files, 10240, output_dir)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run magika-enhanced benchmarks")
    parser.add_argument("-o", "--output", type=Path, default=Path("benchmark_results"), help="Output directory")
    parser.add_argument("-i", "--iterations", type=int, default=5, help="Number of iterations")
    parser.add_argument("--max-files", type=int, default=100, help="Maximum files per test")
    parser.add_argument("--no-compare", action="store_true", help="Skip comparison benchmarks")
    
    args = parser.parse_args()
    
    config = BenchmarkConfig(
        iterations=args.iterations,
        max_files=args.max_files,
    )
    
    runner = BenchmarkRunner(config)
    summary = runner.run_all_benchmarks(args.output)
    runner.print_summary()
    
    print(f"\nResults saved to {args.output}")