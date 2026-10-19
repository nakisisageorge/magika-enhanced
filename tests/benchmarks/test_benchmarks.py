"""
Benchmark tests for magika-enhanced.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from magika_enhanced.benchmarks import BenchmarkConfig, BenchmarkRunner, create_benchmark_fixture


class TestBenchmarkRunner:
    """Tests for benchmark runner."""
    
    def test_benchmark_config_defaults(self):
        """Test default benchmark configuration."""
        config = BenchmarkConfig()
        
        assert config.iterations == 5
        assert config.warmup_runs == 2
        assert config.max_files == 1000
        assert 1024 in config.file_sizes
        assert 10 in config.concurrent_levels
        assert config.measure_memory is True
    
    def test_benchmark_config_custom(self):
        """Test custom benchmark configuration."""
        config = BenchmarkConfig(
            iterations=10,
            warmup_runs=5,
            max_files=500,
            file_sizes=[100, 1024],
            concurrent_levels=[1, 5],
            measure_memory=False,
        )
        
        assert config.iterations == 10
        assert config.warmup_runs == 5
        assert config.max_files == 500
        assert config.file_sizes == [100, 1024]
        assert config.concurrent_levels == [1, 5]
        assert config.measure_memory is False
    
    def test_create_benchmark_fixture(self):
        """Test creating benchmark fixture files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            files = create_benchmark_fixture(num_files=10, output_dir=tmpdir)
            
            assert len(files) == 10
            assert all(f.exists() for f in files)
            assert all(f.stat().st_size > 0 for f in files)
    
    def test_benchmark_runner_creation(self):
        """Test creating benchmark runner."""
        config = BenchmarkConfig(iterations=2, max_files=10)
        runner = BenchmarkRunner(config)
        
        assert runner.config.iterations == 2
        assert runner.config.max_files == 10
        assert runner.results == []
    
    @pytest.mark.slow
    def test_sync_benchmark_execution(self):
        """Test synchronous benchmark execution (smoke test)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = BenchmarkConfig(
                iterations=1,
                warmup_runs=0,
                max_files=5,
                file_sizes=[1024],
                measure_memory=False,
            )
            runner = BenchmarkRunner(config)
            
            # Run a minimal benchmark
            results = runner.run_magika_benchmarks(tmpdir)
            
            assert len(results) > 0
            for r in results:
                assert r.tool_name == "magika-enhanced"
                assert r.total_files > 0
                assert r.avg_time_per_file_ms > 0
                assert r.throughput_files_per_sec > 0


class TestBenchmarkMetrics:
    """Tests for benchmark metrics."""
    
    def test_benchmark_metrics_creation(self):
        """Test creating benchmark metrics."""
        from magika_enhanced.benchmarks import BenchmarkMetrics
        
        metrics = BenchmarkMetrics(
            tool_name="test-tool",
            operation="test_op",
            total_files=100,
            total_time_seconds=1.5,
            avg_time_per_file_ms=15.0,
            median_time_per_file_ms=14.0,
            min_time_per_file_ms=10.0,
            max_time_per_file_ms=25.0,
            std_dev_ms=3.0,
            throughput_files_per_sec=66.67,
            memory_peak_mb=128.5,
            cpu_percent=45.2,
            errors=0,
        )
        
        assert metrics.tool_name == "test-tool"
        assert metrics.total_files == 100
        assert metrics.avg_time_per_file_ms == 15.0
    
    def test_benchmark_metrics_optional_fields(self):
        """Test benchmark metrics with optional fields."""
        from magika_enhanced.benchmarks import BenchmarkMetrics
        
        metrics = BenchmarkMetrics(
            tool_name="test-tool",
            operation="test_op",
            total_files=100,
            total_time_seconds=1.5,
            avg_time_per_file_ms=15.0,
            median_time_per_file_ms=14.0,
            min_time_per_file_ms=10.0,
            max_time_per_file_ms=25.0,
            std_dev_ms=3.0,
            throughput_files_per_sec=66.67,
        )
        
        assert metrics.memory_peak_mb is None
        assert metrics.cpu_percent is None
        assert metrics.accuracy is None
        assert metrics.errors == 0
        assert metrics.metadata == {}


class TestBenchmarkComparison:
    """Tests for comparison benchmarks."""
    
    @pytest.mark.requires_magic
    @pytest.mark.slow
    def test_python_magic_comparison(self):
        """Test comparison with python-magic if available."""
        pytest.skip("Requires python-magic package")
    
    def test_mimetypes_comparison(self):
        """Test comparison with stdlib mimetypes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = BenchmarkConfig(
                iterations=1,
                warmup_runs=0,
                max_files=10,
                file_sizes=[1024],
                measure_memory=False,
            )
            runner = BenchmarkRunner(config)
            
            results = runner.run_comparison_benchmarks(tmpdir)
            
            # Should have at least mimetypes results
            tool_names = {r.tool_name for r in results}
            assert any("mimetypes" in name.lower() for name in tool_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])