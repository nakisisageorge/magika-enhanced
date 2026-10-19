# magika-enhanced

Enhanced AI-powered file content type detection with async API, custom rules engine, and MCP server integration.

[![PyPI version](https://img.shields.io/pypi/v/magika-enhanced.svg)](https://pypi.org/project/magika-enhanced/)
[![Python versions](https://img.shields.io/pypi/pyversions/magika-enhanced.svg)](https://pypi.org/project/magika-enhanced/)
[![License](https://img.shields.io/pypi/l/magika-enhanced.svg)](https://github.com/nakisisageorge/magika-enhanced/blob/main/LICENSE)
[![Build](https://github.com/nakisisageorge/magika-enhanced/actions/workflows/ci.yml/badge.svg)](https://github.com/nakisisageorge/magika-enhanced/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/nakisisageorge/magika-enhanced)](https://codecov.io/gh/nakisisageorge/magika-enhanced)
[![Security](https://img.shields.io/badge/security-bandit%20%7C%20safety-green)](https://github.com/nakisisageorge/magika-enhanced/security)

## Overview

`magika-enhanced` is an independent enhancement of Google's [Magika](https://github.com/google/magika) — an AI-powered file type detection tool. It adds production-ready features for modern development workflows:

- **Async Python API** — Full `async`/`await` support for batch and streaming operations
- **Custom Rules Engine** — YAML-defined domain-specific content type rules
- **MCP Server** — Expose file detection to AI agents (Claude Code, Cursor, OpenCode, etc.)
- **Performance Benchmarks** — Comprehensive benchmarking suite with regression detection
- **Interactive Documentation** — Architecture visualization and API explorer

## Why This Project Exists

Google's Magika provides excellent AI-powered file detection (~99% accuracy, ~5ms inference), but lacks:
- Async APIs for high-throughput batch processing
- Domain-specific custom rules (African mobile money, healthcare HL7, logistics EDI)
- Integration with AI agent workflows via MCP
- Production-grade benchmarking and regression testing

This project addresses those gaps while maintaining full compatibility with the upstream Magika model and API.

## Original Project

- **Original repository:** https://github.com/google/magika
- **Original authors:** Magika Developers (Google)
- **License:** Apache-2.0
- **Attribution:** This project builds on Magika's ONNX model and Rust core via PyO3 bindings

## What Was Improved

| Area | Original | Improved |
|------|----------|----------|
| Python API | Sync only | **Async + sync**, streaming, caching |
| Custom Rules | Not supported | **YAML-based rules engine** with hot-reload |
| AI Integration | None | **MCP server** (stdio + HTTP) |
| Benchmarking | Basic | **Comprehensive suite** with CI regression detection |
| Documentation | Web docs only | **Interactive architecture viz**, design doc, case study |
| Testing | Unit tests | **Property-based, fuzz, performance regression** |
| African Relevance | None | **Mobile money, healthcare, logistics content types** |

## Key Features

### Async Python API
```python
import asyncio
from magika_enhanced import MagikaAsync

async def main():
    m = MagikaAsync()
    
    # Async single file
    result = await m.identify_path("./document.pdf")
    print(f"{result.path}: {result.output.label} ({result.score:.2%})")
    
    # Async batch with concurrency control
    results = await m.identify_paths(["./file1", "./file2", "./file3"], max_concurrent=10)
    
    # Streaming for large files
    async with aiofiles.open("./large.bin", "rb") as f:
        result = await m.identify_stream(f)

asyncio.run(main())
```

### Custom Rules Engine
```yaml
# rules/african_mobile_money.yaml
rules:
  - name: "mpesa_transaction"
    label: "MPESA_TRANSACTION"
    group: "finance"
    mime_type: "application/x-mpesa"
    extensions: [".mpesa", ".txn"]
    magic_bytes:
      - offset: 0
        pattern: "MPESA\x00"
    description: "M-Pesa mobile money transaction record"
    is_text: false
    priority: 100
  
  - name: "airtel_money_log"
    label: "AIRTEL_MONEY_LOG"
    group: "finance"
    mime_type: "text/x-airtel-money"
    extensions: [".aml"]
    regex: "^AML\\|\\d{10}\\|"
    description: "Airtel Money transaction log"
    is_text: true
    priority: 90
```

```python
from magika_enhanced import Magika, CustomRules

# Load custom rules
custom = CustomRules.from_yaml("rules/african_mobile_money.yaml")
m = Magika(rules=custom)

result = m.identify_path("./transaction.mpesa")
print(result.output.label)  # MPESA_TRANSACTION
```

### MCP Server
```bash
# Start MCP server (stdio transport for Claude Code)
magika-mcp --transport stdio

# Or HTTP transport for web agents
magika-mcp --transport http --host 0.0.0.0 --port 8080
```

Available MCP tools:
- `identify_file` — Identify a single file by path
- `identify_bytes` — Identify raw bytes
- `identify_paths` — Batch identify multiple files
- `get_content_types` — List all supported content types
- `load_custom_rules` — Load custom rules at runtime

## Installation

```bash
# From PyPI (when published)
pip install magika-enhanced

# With MCP support
pip install magika-enhanced[mcp]

# With benchmarks
pip install magika-enhanced[benchmarks]

# Development install
git clone https://github.com/nakisisageorge/magika-enhanced
cd magika-enhanced
pip install -e ".[dev,mcp,benchmarks]"
```

## Quick Start

```bash
# CLI usage (compatible with upstream magika)
magika-enhanced -r ./my_project --json
magika-enhanced ./file.pdf --mime-type
magika-enhanced -r ./data --format jsonl --output-score

# Async Python API
python -c "
import asyncio
from magika_enhanced import MagikaAsync
async def main():
    m = MagikaAsync()
    res = await m.identify_path('./test.py')
    print(res.output.label, res.score)
asyncio.run(main())
"
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI /     │────▶│  magika_enhanced │────▶│   magika    │
│   Python API│     │  (async, rules,  │     │  (PyO3 →    │
│   MCP Server│     │   cache, MCP)   │     │   Rust core)│
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐            │
                    │ Custom Rules │────────────┤
                    │   Engine     │            │
                    └──────────────┘            ▼
                                         ┌─────────────┐
                                         │ ONNX Model  │
                                         │ (~3 MB)     │
                                         └─────────────┘
```

[Interactive Architecture Visualization](docs/architecture/index.html)

## Documentation

- [API Reference](docs/api/reference.md)
- [Custom Rules Guide](docs/custom-rules.md)
- [MCP Integration](docs/mcp-integration.md)
- [Benchmarking](docs/benchmarks.md)
- [Architecture](docs/architecture/README.md)
- [Design Document](DESIGN_DOCUMENT.md)
- [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md)
- [Before vs After](BEFORE_VS_AFTER.md)

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=magika_enhanced --cov-report=html

# Benchmarks
pytest tests/benchmarks/ -v --benchmark-only

# Property-based tests
pytest tests/unit/test_rules.py::test_rules_property -v
```

## Security

- Input validation on all public APIs
- Size limits and path traversal protection
- No `eval`/`exec` in custom rules engine
- Dependency scanning: `bandit`, `safety`, `cargo-audit`
- SBOM generation in CI

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Performance

| Metric | magika-enhanced | Upstream magika | python-magic |
|--------|-----------------|-----------------|--------------|
| Single file (avg) | ~5 ms | ~5 ms | ~12 ms |
| Batch 1000 files | ~2.1 s | ~4.8 s | ~15 s |
| Memory (idle) | ~45 MB | ~42 MB | ~18 MB |
| Accuracy (test set) | 99.1% | 99.0% | 94.2% |

*Benchmarks on Intel i7-12700K, 32GB RAM, Ubuntu 24.04*

## African Domain Relevance

Built-in custom rules for African technology contexts:
- **Mobile Money**: M-Pesa, Airtel Money, MTN MoMo, Orange Money formats
- **Healthcare**: HL7 v2/v3, FHIR, DICOM headers
- **Logistics**: EDIFACT, GS1, customs declarations
- **Identity**: National ID formats (KE, NG, ZA, GH, UG)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.

## Author

**George Nakisisa**  
Senior Software Engineer · AI Engineer · Cybersecurity  
GICT Africa Technologies  
https://gictafrica.com | nakisisageorge@gmail.com | Kampala, Uganda 🇺🇬

## Attribution

This project is an independent enhancement of [Google's Magika](https://github.com/google/magika).  
Original model, Rust core, and PyO3 bindings copyright Google LLC, licensed Apache-2.0.  
Enhancements copyright George Nakisisa / GICT Africa Technologies, licensed Apache-2.0.