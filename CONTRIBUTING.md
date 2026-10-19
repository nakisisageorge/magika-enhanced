# Contributing to magika-enhanced

Thank you for your interest in contributing! This project welcomes contributions from the community.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

## Ways to Contribute

- **Bug Reports**: File an issue with reproduction steps
- **Feature Requests**: Propose new features via issues
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve docs, add examples
- **Custom Rules**: Contribute domain-specific rule sets
- **Testing**: Add test cases, improve coverage

## Development Setup

### Prerequisites

- Python 3.8+
- Rust 1.70+ (for upstream magika development)
- `uv` or `pip` for dependency management

### Quick Start

```bash
# Clone the repository
git clone https://github.com/nakisisageorge/magika-enhanced
cd magika-enhanced

# Install development dependencies
pip install -e ".[dev,mcp,benchmarks]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check .
mypy magika_enhanced

# Run security checks
bandit -r magika_enhanced
safety check
```

## Project Structure

```
magika_enhanced/
├── core/           # Sync/Async Magika wrappers
├── rules/          # Custom rules engine
├── mcp/            # MCP server
├── benchmarks/     # Benchmark runner
├── cli/            # CLI entry point
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── benchmarks/     # Benchmark tests
rules/
├── african_mobile_money.yaml
├── healthcare.yaml
├── logistics.yaml
docs/
├── architecture/   # Interactive architecture viz
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### PR Requirements

- All tests pass (`pytest`)
- Code passes linting (`ruff check .`, `mypy magika_enhanced`)
- Security checks pass (`bandit -r magika_enhanced`, `safety check`)
- Type hints on all new public APIs
- Docstrings for new classes/functions
- Update CHANGELOG.md with your changes
- Add tests for new functionality

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

Examples:
```
feat(rules): add M-Pesa STK Push content type
fix(async): handle cancellation in identify_paths
docs(readme): add MCP server usage examples
test(benchmarks): add memory profiling test
```

## Custom Rules Contribution

We welcome custom rules for new domains! To contribute:

1. Create a YAML file in `rules/` following the schema:
```yaml
name: "your_domain"
version: "1.0"
description: "Description of your domain"
rules:
  - name: "your_rule"
    label: "YOUR_LABEL"
    group: "your_group"
    mime_type: "application/x-your-type"
    extensions: [".your_ext"]
    magic_bytes:
      offset: 0
      pattern: "HEX_PATTERN"
    regex: "optional_regex"
    priority: 100
```

2. Add test cases in `tests/unit/test_rules.py`
3. Update documentation in `docs/custom-rules.md`
4. Submit PR

## Testing Guidelines

- Write tests for all new functionality
- Use property-based testing for rules engine (`hypothesis`)
- Test both sync and async APIs
- Include edge cases: empty files, large files, malformed input
- Benchmark tests should be marked `@pytest.mark.slow`

## Security

- Report security vulnerabilities to nakisisageorge@gmail.com
- Do not disclose publicly until fixed
- All dependencies scanned in CI (`safety`, `bandit`, `cargo-audit`)

## Release Process

Releases are automated via GitHub Actions on tag push:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers:
- Multi-platform wheel build (maturin)
- PyPI publication
- GitHub Release creation
- Docker image build
- Documentation deployment

## Questions?

Open an issue or email nakisisageorge@gmail.com