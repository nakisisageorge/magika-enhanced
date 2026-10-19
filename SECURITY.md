# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Yes             |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, email **nakisisageorge@gmail.com** with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for fix.

## Security Measures

### Input Validation
- All file paths resolved and validated against allowlist
- Maximum file size limits (default 100MB, configurable)
- Path traversal protection via `Path.resolve()`

### Dependency Security
- Automated scanning in CI:
  - `safety` for Python dependencies
  - `bandit` for Python code
  - `cargo-audit` for Rust dependencies (upstream)
- SBOM generation on release (CycloneDX)

### Custom Rules Engine
- No `eval()`/`exec()` - YAML only
- Pre-compiled regex patterns
- Schema validation on rule load
- No user-provided code execution

### MCP Server
- Schema validation on all tool inputs (Pydantic)
- Transport isolation (stdio vs HTTP)
- No arbitrary command execution

### File Handling
- Streaming reads for large files
- No full file loading in memory for detection
- Temporary files cleaned up automatically

## Known Considerations

### Upstream magika
- ONNX model loaded once per process
- Model file integrity should be verified
- Rust dependencies audited via `cargo-audit`

### Deployment
- Use virtual environments
- Pin dependencies in production
- Monitor for dependency updates

## Security Checklist for Contributors

- [ ] No hardcoded secrets in code
- [ ] No `eval()`/`exec()` without explicit review
- [ ] Input validation on all public APIs
- [ ] Path traversal protection
- [ ] Size limits on file operations
- [ ] Dependencies from trusted sources
- [ ] Tests for security edge cases