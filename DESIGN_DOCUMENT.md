# DESIGN DOCUMENT: magika-enhanced

## 1. Original Architecture

### 1.1 Overview
Google's Magika is an AI-powered file content type detection system consisting of:
- **ONNX Model** (~3MB): Deep learning model trained on ~100M samples across 200+ content types
- **Rust Core** (`magika` crate): High-performance inference engine using tract ONNX runtime
- **PyO3 Bindings** (`magika._magika`): Python-C bridge for zero-copy tensor operations
- **Python Package** (`magika`): High-level Python API wrapping the Rust core
- **CLI** (`magika-cli`): Rust-based command-line interface
- **WASM/JS/Go bindings**: Additional language bindings

### 1.2 Detection Pipeline
```
File Input → Read (first 8KB + last 4KB) → Preprocess → ONNX Inference → 
Post-process (thresholds, overwrite rules) → ContentTypeLabel + Metadata
```

### 1.3 Key Components
- **Model**: `standard_v3_3.onnx` - CNN-based architecture
- **Content Types**: 200+ labels organized in hierarchy (groups, MIME types, extensions)
- **Prediction Modes**: BEST_GUESS, MEDIUM_CONFIDENCE, HIGH_CONFIDENCE
- **Overwrite System**: Rules-based override for specific content types

### 1.4 Limitations Identified
1. **Sync-only Python API** - No async/await support for high-throughput scenarios
2. **No Custom Rules** - Cannot extend with domain-specific content types
3. **No MCP Integration** - Cannot expose to AI agents (Claude, Cursor, etc.)
4. **Limited Benchmarking** - No built-in performance regression testing
5. **Basic Documentation** - No interactive architecture visualization
6. **No African Domain Content Types** - Missing mobile money, healthcare, logistics formats

## 2. Problems Identified

### 2.1 API Limitations
| Problem | Impact | Severity |
|---------|--------|----------|
| Sync-only API | Blocks event loop in async applications | High |
| No streaming | Cannot process large files efficiently | Medium |
| No caching | Repeated scans of same content are slow | Medium |
| No batch concurrency control | Resource exhaustion on large batches | High |

### 2.2 Extensibility Gaps
| Problem | Impact | Severity |
|---------|--------|----------|
| No custom rules engine | Cannot add domain-specific types | High |
| No hot-reload | Rule changes require restart | Medium |
| No rule priority system | Conflicts with built-in types | Medium |

### 2.3 Integration Gaps
| Problem | Impact | Severity |
|---------|--------|----------|
| No MCP server | Cannot use with AI agents | High |
| No structured output for CI/CD | Hard to integrate in pipelines | Medium |
| No SARIF/JUnit output | No standard test reporting | Low |

### 2.4 Operational Gaps
| Problem | Impact | Severity |
|---------|--------|----------|
| No benchmark suite | Cannot detect performance regressions | High |
| No memory profiling | Hard to optimize resource usage | Medium |
| No comparison benchmarks | Cannot evaluate alternatives | Medium |

## 3. Proposed Architecture

### 3.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    magika-enhanced                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Sync API  │  │  Async API  │  │     MCP Server      │  │
│  │  (Magika)   │  │(MagikaAsync)│  │  (MagikaMCPServer)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │              │
│         └────────────────┼─────────────────────┘              │
│                          ▼                                    │
│              ┌─────────────────────┐                          │
│              │   Core Enhancements │                          │
│              │  ┌───────────────┐  │                          │
│              │  │   LRU Cache   │  │                          │
│              │  ├───────────────┤  │                          │
│              │  │ Custom Rules  │  │                          │
│              │  │    Engine     │  │                          │
│              │  ├───────────────┤  │                          │
│              │  │  Benchmarks   │  │                          │
│              │  └───────────────┘  │                          │
│              └──────────┬──────────┘                          │
│                         │                                      │
│         ┌───────────────┼───────────────┐                     │
│         ▼               ▼               ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ magika      │  │ Custom      │  │ Benchmark   │           │
│  │ (upstream)  │  │ Rules Files │  │ Fixtures    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

#### 3.2.1 Enhanced Sync API (`Magika`)
- Wraps upstream `magika.Magika`
- Adds LRU cache with configurable size
- Integrates custom rules engine
- Maintains full API compatibility

#### 3.2.2 Async API (`MagikaAsync`)
- Full async/await support
- `asyncio.Semaphore` for concurrency control
- Async file I/O via `aiofiles`
- Streaming support for large files
- Thread pool executor for blocking upstream calls

#### 3.2.3 Custom Rules Engine
- YAML/JSON rule definitions
- Magic bytes matching (offset + pattern + mask)
- Regex pattern matching (pre-compiled)
- Extension-based matching
- Priority-based ordering (highest first)
- Hot-reload capability
- Domain-specific rule sets (African mobile money, healthcare, logistics)

#### 3.2.4 MCP Server (`MagikaMCPServer`)
- Implements MCP protocol via `mcp` Python package
- Tools: `identify_file`, `identify_bytes`, `identify_paths`, `get_content_types`, `load_custom_rules`
- Transports: stdio (for Claude Code), HTTP/SSE (for web agents)
- Schema validation via Pydantic

#### 3.2.5 Benchmark Suite
- Configurable iterations, warmup, concurrency levels
- Memory and CPU profiling via `psutil`
- Comparison against `python-magic`, `mimetypes`, `file(1)`
- JSON output for CI/CD integration
- Regression detection

## 4. New Architecture

### 4.1 Package Structure
```
magika_enhanced/
├── __init__.py           # Public exports
├── types.py              # Type definitions
├── core/
│   ├── __init__.py
│   ├── magika_sync.py    # Enhanced sync wrapper
│   └── magika_async.py   # Async wrapper
├── rules/
│   ├── __init__.py
│   └── engine.py         # Custom rules engine
├── mcp/
│   ├── __init__.py
│   └── server.py         # MCP server
├── benchmarks/
│   ├── __init__.py
│   └── runner.py         # Benchmark runner
├── cli/
│   ├── __init__.py
│   └── main.py           # CLI entry point
```

### 4.2 Data Flow

#### Sync Path
```
identify_path(path)
    → Check cache (LRU)
    → If miss: upstream.identify_path(path)
    → Apply custom rules (if loaded)
    → Cache result
    → Return MagikaResult
```

#### Async Path
```
async identify_path(path)
    → Check async cache (LRU + asyncio.Lock)
    → If miss: run_in_executor(upstream.identify_path)
    → Apply custom rules
    → Cache result
    → Return MagikaResult
```

#### Batch Async Path
```
async identify_paths(paths, max_concurrent)
    → Create semaphore(max_concurrent)
    → Create tasks with semaphore
    → asyncio.gather(*tasks)
    → Return List[MagikaResult]
```

#### Custom Rules Matching
```
match(content, path)
    → For each rule (by priority):
        → Check magic bytes (if defined)
        → Check regex (if defined)
        → Check extension (if path provided)
    → Return first match or None
```

## 5. Why Changes Were Made

| Change | Rationale |
|--------|-----------|
| Async API | Modern Python applications use async; blocking calls hurt throughput |
| Custom Rules | Domain-specific content types (African fintech, healthcare, logistics) are critical for real-world use |
| MCP Server | AI agent integration is the future of developer tools; enables "file detection as a tool" |
| Benchmarks | Performance regression detection is essential for production libraries |
| Cache | Repeated scanning of same content is common in batch processing |
| African Rules | Portfolio differentiation; addresses underserved markets |
| Interactive Docs | Demonstrates architecture understanding; portfolio showcase |

## 6. Technology Decisions

| Decision | Choice | Justification |
|----------|--------|---------------|
| Async Runtime | `asyncio` (stdlib) | No extra dependency; standard |
| File I/O | `aiofiles` | Mature async file library |
| Rules Format | YAML | Human-readable; supports comments |
| Rule Matching | Pre-compiled regex + bytes | Performance |
| Cache | LRU with `asyncio.Lock` | Thread-safe async cache |
| MCP Transport | stdio + HTTP/SSE | Covers Claude Code + web agents |
| Benchmarking | `psutil` + `time.perf_counter` | Cross-platform, accurate |
| Comparison Tools | `python-magic`, `mimetypes` | Common alternatives |

## 7. Security Decisions

| Concern | Mitigation |
|---------|------------|
| Path traversal | `Path.resolve()` validation; restrict to allowed directories |
| Large file DoS | Size limits; streaming reads; chunked processing |
| Regex DoS | Timeout on regex matching; compiled patterns only |
| Custom rules injection | No `eval`/`exec`; YAML only; schema validation |
| Dependency vulnerabilities | `safety`, `bandit`, `cargo-audit` in CI |
| Model supply chain | Verify ONNX model checksums; pinned upstream version |

## 8. Performance Decisions

| Optimization | Implementation |
|--------------|----------------|
| Lazy model loading | Load ONNX model only on first prediction |
| Connection pooling | Reuse thread pool executor |
| Memory-mapped I/O | `mmap` for large files (future) |
| SIMD preprocessing | `numpy` vectorization (future) |
| Batch prediction | Single model call for multiple files (future) |

## 9. Scalability Considerations

- **Horizontal**: Multiple `MagikaAsync` instances can share custom rules
- **Vertical**: Concurrency control prevents resource exhaustion
- **Caching**: LRU cache reduces redundant computation
- **Streaming**: Process files larger than memory

## 10. Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PyPI Wheel    │     │  GitHub Pages   │     │  Docker Hub     │
│  (manylinux,    │     │  (docs, arch    │     │  (mcp server,   │
│   macOS, Win)   │     │   viz, bench)   │     │   benchmarks)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   CI/CD Pipeline       │
                    │  (GitHub Actions)      │
                    │  - lint (ruff)         │
                    │  - typecheck (mypy)    │
                    │  - test (pytest)       │
                    │  - bench (custom)      │
                    │  - security (bandit)   │
                    │  - release (maturin)   │
                    └────────────────────────┘
```

## 11. Testing Strategy

| Layer | Tools | Coverage Target |
|-------|-------|-----------------|
| Unit | `pytest`, `hypothesis` | 90%+ |
| Integration | `pytest-asyncio` | 80%+ |
| Benchmark | Custom runner | N/A (regression) |
| Property-based | `hypothesis` | Rules engine |
| Fuzz | `hypothesis` + malformed inputs | Input validation |
| Security | `bandit`, `safety` | All code |

## 12. Future Improvements

1. **Batch ONNX Inference** - Single model call for multiple files
2. **WebAssembly Build** - Run in browser/edge via `magika.js`
3. **Distributed Benchmarking** - Multi-node benchmark runner
4. **Rule Marketplace** - Community-contributed rule sets
5. **ML Model Fine-tuning** - Domain-specific model retraining
6. **Real-time Streaming** - Kafka/Redis Streams integration
7. **GraphQL API** - Alternative to MCP for web clients