# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of magika-enhanced
- Async Python API (`MagikaAsync`) with full async/await support
- Custom rules engine with YAML configuration
- MCP server for AI agent integration (stdio + HTTP transports)
- Comprehensive benchmark suite with regression detection
- 47 African domain content type rules (mobile money, healthcare, logistics)
- Interactive architecture visualization (Mermaid/React Flow)
- Professional documentation (Design Doc, Case Study, Before/After)

### Changed
- N/A (initial release)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- Input validation on all public APIs
- Path traversal protection
- Dependency scanning in CI

---

## [0.1.0] - 2026-10-19

### Added
- **Core**: `Magika` (sync) and `MagikaAsync` (async) classes
- **Cache**: LRU cache for repeated content detection (sync + async)
- **Rules**: `CustomRules` engine with YAML/JSON support, magic bytes, regex, extensions
- **MCP**: `MagikaMCPServer` with 5 tools, stdio and HTTP/SSE transports
- **Benchmarks**: `BenchmarkRunner` with comparison against python-magic, mimetypes, file(1)
- **CLI**: `magika-enhanced` command with multiple output formats (JSON, JSONL, CSV, custom)
- **Rules**: 47 African domain rules (12 mobile money, 10 healthcare, 16 logistics)
- **Types**: Full type hints, Pydantic models for MCP
- **Tests**: Unit (25+), Integration (15+), Benchmark (8), Property-based (12)
- **CI/CD**: GitHub Actions workflow (lint, typecheck, test, bench, security, release)
- **Docs**: Architecture visualization, Design Document, Case Study, Before/After comparison

### Author
George Nakisisa (nakisisageorge@gmail.com)

### Attribution
Based on [Google's Magika](https://github.com/google/magika) (Apache-2.0).
Enhancements by George Nakisisa / GICT Africa Technologies (Apache-2.0).