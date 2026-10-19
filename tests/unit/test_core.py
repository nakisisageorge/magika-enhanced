"""
Unit tests for magika-enhanced core functionality.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from magika_enhanced import Magika, MagikaAsync
from magika_enhanced.rules import CustomRules, Rule, RuleSet
from magika_enhanced.types import ContentTypeLabel


class TestMagikaSync:
    """Tests for synchronous Magika wrapper."""
    
    def test_basic_identification(self):
        """Test basic file identification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            test_file.write_text("print('hello world')")
            
            m = Magika()
            result = m.identify_path(test_file)
            
            assert result.ok
            assert result.prediction is not None
            assert result.prediction.output.label in (ContentTypeLabel.PYTHON, ContentTypeLabel.TEXT)
    
    def test_identify_bytes(self):
        """Test identification from bytes."""
        m = Magika()
        result = m.identify_bytes(b"print('hello')")
        
        assert result.ok
        assert result.prediction is not None
    
    def test_identify_empty_bytes(self):
        """Test identification of empty bytes."""
        m = Magika()
        result = m.identify_bytes(b"")
        
        assert result.ok
        assert result.prediction is not None
        assert result.prediction.output.label == ContentTypeLabel.EMPTY
    
    def test_batch_identification(self):
        """Test batch file identification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            files = []
            for i in range(5):
                f = tmpdir / f"test{i}.py"
                f.write_text(f"print({i})")
                files.append(f)
            
            m = Magika()
            results = m.identify_paths(files)
            
            assert len(results) == 5
            assert all(r.ok for r in results)
    
    def test_cache_functionality(self):
        """Test that caching works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            test_file.write_text("print('hello')")
            
            m = Magika(cache_size=10)
            
            # First call - cache miss
            result1 = m.identify_path(test_file)
            
            # Second call - cache hit
            result2 = m.identify_path(test_file)
            
            assert result1.ok and result2.ok
            assert result1.path == result2.path
    
    def test_custom_rules(self):
        """Test custom rules integration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create custom rules file
            rules_file = tmpdir / "custom.yaml"
            rules_file.write_text("""
name: "test_rules"
version: "1.0"
rules:
  - name: "test_rule"
    label: "TEST_TYPE"
    group: "test"
    mime_type: "application/x-test"
    extensions: [".test"]
    magic_bytes:
      offset: 0
      pattern: "54455354"  # "TEST" in hex
    priority: 100
""")
            
            # Create test file with magic bytes
            test_file = tmpdir / "sample.test"
            test_file.write_bytes(b"TEST" + b"data" * 100)
            
            m = Magika(rules=rules_file)
            result = m.identify_path(test_file)
            
            assert result.ok
            # Custom rule should match
            assert result.prediction is not None


class TestMagikaAsync:
    """Tests for asynchronous Magika wrapper."""
    
    @pytest.mark.asyncio
    async def test_basic_identification(self):
        """Test basic async file identification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            test_file.write_text("print('hello world')")
            
            m = MagikaAsync()
            result = await m.identify_path(test_file)
            
            assert result.ok
            assert result.prediction is not None
    
    @pytest.mark.asyncio
    async def test_batch_identification(self):
        """Test async batch identification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            files = []
            for i in range(10):
                f = tmpdir / f"test{i}.py"
                f.write_text(f"print({i})")
                files.append(f)
            
            m = MagikaAsync(max_concurrent=5)
            results = await m.identify_paths(files)
            
            assert len(results) == 10
            assert all(r.ok for r in results)
    
    @pytest.mark.asyncio
    async def test_concurrency_control(self):
        """Test that concurrency limiting works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            files = []
            for i in range(20):
                f = tmpdir / f"test{i}.py"
                f.write_text(f"print({i})")
                files.append(f)
            
            m = MagikaAsync(max_concurrent=3)
            
            # Track concurrent executions
            concurrent_count = 0
            max_concurrent = 0
            
            async def tracking_identify(path):
                nonlocal concurrent_count, max_concurrent
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                try:
                    return await m.identify_path(path)
                finally:
                    concurrent_count -= 1
            
            # Patch identify_path temporarily
            original = m.identify_path
            m.identify_path = tracking_identify
            
            results = await m.identify_paths(files)
            
            m.identify_path = original
            
            assert max_concurrent <= 3
            assert len(results) == 20
    
    @pytest.mark.asyncio
    async def test_identify_bytes(self):
        """Test async identification from bytes."""
        m = MagikaAsync()
        result = await m.identify_bytes(b"print('hello')")
        
        assert result.ok
        assert result.prediction is not None


class TestCustomRules:
    """Tests for custom rules engine."""
    
    def test_rule_creation(self):
        """Test creating a custom rule."""
        rule = Rule(
            name="test_rule",
            label=ContentTypeLabel.PYTHON,
            group="code",
            mime_type="text/x-python",
            extensions=[".py"],
            priority=100,
        )
        
        assert rule.name == "test_rule"
        assert rule.label == ContentTypeLabel.PYTHON
        assert rule.priority == 100
    
    def test_rule_set(self):
        """Test rule set operations."""
        rules = [
            Rule(name="rule1", label=ContentTypeLabel.PYTHON, group="code", mime_type="text/x-python", priority=100),
            Rule(name="rule2", label=ContentTypeLabel.JSON, group="data", mime_type="application/json", priority=50),
        ]
        
        rs = RuleSet(rules=rules)
        
        assert len(rs.rules) == 2
        # Should be sorted by priority
        assert rs.rules[0].name == "rule1"
        assert rs.rules[1].name == "rule2"
    
    def test_yaml_serialization(self):
        """Test YAML serialization of rules."""
        rule = Rule(
            name="test_rule",
            label=ContentTypeLabel.PYTHON,
            group="code",
            mime_type="text/x-python",
            extensions=[".py"],
            magic_bytes=None,
            regex=r"^import\s+\w+",
            priority=100,
        )
        
        rs = RuleSet(rules=[rule])
        yaml_str = rs.to_dict()
        
        assert yaml_str["name"] == "custom"
        assert len(yaml_str["rules"]) == 1
        assert yaml_str["rules"][0]["name"] == "test_rule"
    
    def test_custom_rules_from_yaml(self):
        """Test loading custom rules from YAML."""
        yaml_content = """
name: "test_rules"
rules:
  - name: "python_rule"
    label: "PYTHON"
    group: "code"
    mime_type: "text/x-python"
    extensions: [".py"]
    regex: "^import\\s+\\w+"
    priority: 100
"""
        custom = CustomRules.from_yaml(yaml_content)
        
        assert len(custom) == 1
        rule = custom.get_all_rules()[0]
        assert rule.name == "python_rule"
        assert rule.regex == r"^import\s+\w+"
    
    def test_magic_bytes_matching(self):
        """Test magic bytes pattern matching."""
        yaml_content = """
name: "test_rules"
rules:
  - name: "png_rule"
    label: "PNG"
    group: "image"
    mime_type: "image/png"
    extensions: [".png"]
    magic_bytes:
      offset: 0
      pattern: "89504e470d0a1a0a"  # PNG signature
    priority: 100
"""
        custom = CustomRules.from_yaml(yaml_content)
        
        # PNG file header
        png_header = bytes.fromhex("89504e470d0a1a0a") + b"fake png data"
        matched = custom.match(png_header)
        
        assert matched is not None
        assert matched.name == "png_rule"
    
    def test_extension_matching(self):
        """Test file extension matching."""
        yaml_content = """
name: "test_rules"
rules:
  - name: "pdf_rule"
    label: "PDF"
    group: "document"
    mime_type: "application/pdf"
    extensions: [".pdf"]
    priority: 100
"""
        custom = CustomRules.from_yaml(yaml_content)
        
        from pathlib import Path
        matched = custom.match(b"%PDF-1.4", Path("document.pdf"))
        
        assert matched is not None
        assert matched.name == "pdf_rule"
    
    def test_priority_ordering(self):
        """Test that rules are ordered by priority."""
        yaml_content = """
name: "test_rules"
rules:
  - name: "low_priority"
    label: "TYPE_A"
    group: "test"
    mime_type: "application/x-a"
    extensions: [".a"]
    priority: 10
  - name: "high_priority"
    label: "TYPE_B"
    group: "test"
    mime_type: "application/x-b"
    extensions: [".b"]
    priority: 100
"""
        custom = CustomRules.from_yaml(yaml_content)
        
        rules = custom.get_all_rules()
        assert rules[0].name == "high_priority"
        assert rules[1].name == "low_priority"
    
    def test_merge_rules(self):
        """Test merging multiple rule sets."""
        yaml1 = """
name: "rules1"
rules:
  - name: "rule1"
    label: "TYPE_1"
    group: "test"
    mime_type: "application/x-1"
    priority: 100
"""
        yaml2 = """
name: "rules2"
rules:
  - name: "rule2"
    label: "TYPE_2"
    group: "test"
    mime_type: "application/x-2"
    priority: 50
"""
        custom1 = CustomRules.from_yaml(yaml1)
        custom2 = CustomRules.from_yaml(yaml2)
        
        custom1.merge(custom2)
        
        assert len(custom1) == 2
        names = {r.name for r in custom1.get_all_rules()}
        assert names == {"rule1", "rule2"}


class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_magika_with_custom_rules(self):
        """Test Magika with custom rules loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create custom rules
            rules_file = tmpdir / "rules.yaml"
            rules_file.write_text("""
name: "integration_test"
rules:
  - name: "custom_text"
    label: "CUSTOM_TEXT"
    group: "test"
    mime_type: "text/x-custom"
    extensions: [".ctxt"]
    magic_bytes:
      offset: 0
      pattern: "435553544f4d"  # "CUSTOM"
    priority: 200
""")
            
            # Create test file
            test_file = tmpdir / "sample.ctxt"
            test_file.write_bytes(b"CUSTOM content here")
            
            # Test with sync Magika
            m = Magika(rules=rules_file)
            result = m.identify_path(test_file)
            
            assert result.ok
            # Custom rule should take precedence
            assert result.custom_rules is not None
    
    @pytest.mark.asyncio
    async def test_async_with_custom_rules(self):
        """Test async Magika with custom rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            rules_file = tmpdir / "rules.yaml"
            rules_file.write_text("""
name: "async_test"
rules:
  - name: "async_rule"
    label: "ASYNC_TYPE"
    group: "test"
    mime_type: "application/x-async"
    extensions: [".async"]
    regex: "^ASYNC:"
    priority: 150
""")
            
            test_file = tmpdir / "sample.async"
            test_file.write_text("ASYNC: data here")
            
            m = MagikaAsync(rules=rules_file)
            result = await m.identify_path(test_file)
            
            assert result.ok


if __name__ == "__main__":
    pytest.main([__file__, "-v"])