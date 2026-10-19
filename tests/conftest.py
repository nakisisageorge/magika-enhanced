"""
Pytest configuration and fixtures for magika-enhanced tests.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file."""
    f = temp_dir / "sample.txt"
    f.write_text("Hello, world!\nThis is a test file.\n")
    return f


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file."""
    f = temp_dir / "sample.py"
    f.write_text("import os\nimport sys\n\ndef main():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    main()\n")
    return f


@pytest.fixture
def sample_json_file(temp_dir):
    """Create a sample JSON file."""
    f = temp_dir / "sample.json"
    f.write_text('{"name": "test", "value": 42, "items": [1, 2, 3]}')
    return f


@pytest.fixture
def sample_binary_file(temp_dir):
    """Create a sample binary file."""
    f = temp_dir / "sample.bin"
    f.write_bytes(bytes(range(256)) * 4)  # 1KB of varied bytes
    return f


@pytest.fixture
def empty_file(temp_dir):
    """Create an empty file."""
    f = temp_dir / "empty.txt"
    f.write_bytes(b"")
    return f


@pytest.fixture
def sample_files_dir(temp_dir):
    """Create a directory with various sample files."""
    files = {}
    
    # Text files
    files["text"] = temp_dir / "document.txt"
    files["text"].write_text("This is a plain text document.\n" * 10)
    
    # Python files
    files["python"] = temp_dir / "script.py"
    files["python"].write_text("#!/usr/bin/env python3\n\ndef hello():\n    return 'world'\n\nprint(hello())\n")
    
    # JSON files
    files["json"] = temp_dir / "data.json"
    files["json"].write_text('{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}')
    
    # CSV files
    files["csv"] = temp_dir / "data.csv"
    files["csv"].write_text("id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n")
    
    # Binary files
    files["binary"] = temp_dir / "data.bin"
    files["binary"].write_bytes(bytes([i % 256 for i in range(1024)]))
    
    # Empty file
    files["empty"] = temp_dir / "empty.txt"
    files["empty"].write_bytes(b"")
    
    return files


@pytest.fixture
def custom_rules_yaml(temp_dir):
    """Create a custom rules YAML file."""
    rules_file = temp_dir / "custom_rules.yaml"
    rules_file.write_text("""
name: "test_rules"
version: "1.0"
rules:
  - name: "test_type"
    label: "TEST_TYPE"
    group: "test"
    mime_type: "application/x-test"
    extensions: [".test"]
    magic_bytes:
      offset: 0
      pattern: "54455354"  # "TEST" in hex
    priority: 100
  - name: "custom_text"
    label: "CUSTOM_TEXT"
    group: "test"
    mime_type: "text/x-custom"
    extensions: [".ctxt"]
    regex: "^CUSTOM:"
    priority: 90
""")
    return rules_file


@pytest.fixture
def african_rules_path():
    """Path to African mobile money rules."""
    return Path(__file__).parents[2] / "rules" / "african_mobile_money.yaml"


@pytest.fixture
def healthcare_rules_path():
    """Path to healthcare rules."""
    return Path(__file__).parents[2] / "rules" / "healthcare.yaml"


@pytest.fixture
def logistics_rules_path():
    """Path to logistics rules."""
    return Path(__file__).parents[2] / "rules" / "logistics.yaml"


# Pytest-asyncio configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "benchmark: marks tests as benchmark tests")
    config.addinivalue_line("markers", "requires_magic: marks tests requiring python-magic")
    config.addinivalue_line("markers", "requires_network: marks tests requiring network access")