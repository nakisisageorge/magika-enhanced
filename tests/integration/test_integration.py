"""
Integration tests for magika-enhanced.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from magika_enhanced import Magika, MagikaAsync
from magika_enhanced.mcp.server import MagikaMCPServer
from magika_enhanced.rules import CustomRules


class TestMCPIntegration:
    """Tests for MCP server integration."""
    
    @pytest.mark.asyncio
    async def test_mcp_server_creation(self):
        """Test MCP server can be created."""
        server = MagikaMCPServer()
        
        assert server.magika is not None
        assert server.server is not None
    
    @pytest.mark.asyncio
    async def test_mcp_tools_listed(self):
        """Test that MCP tools are properly registered."""
        server = MagikaMCPServer()
        
        tools = await server.server.list_tools()
        
        tool_names = {t.name for t in tools}
        expected = {"identify_file", "identify_bytes", "identify_paths", "get_content_types", "load_custom_rules"}
        assert expected.issubset(tool_names)
    
    @pytest.mark.asyncio
    async def test_identify_file_tool(self):
        """Test identify_file MCP tool."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            test_file.write_text("print('hello')")
            
            server = MagikaMCPServer()
            
            result = await server.server.call_tool("identify_file", {"path": str(test_file)})
            
            assert not result.isError
            assert len(result.content) == 1
            assert "test.py" in result.content[0].text
            assert "PYTHON" in result.content[0].text or "TEXT" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_identify_bytes_tool(self):
        """Test identify_bytes MCP tool."""
        import base64
        
        server = MagikaMCPServer()
        
        content = base64.b64encode(b"print('hello')").decode()
        result = await server.server.call_tool("identify_bytes", {"content": content})
        
        assert not result.isError
        assert "PYTHON" in result.content[0].text or "TEXT" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_get_content_types_tool(self):
        """Test get_content_types MCP tool."""
        server = MagikaMCPServer()
        
        result = await server.server.call_tool("get_content_types", {})
        
        assert not result.isError
        types_text = result.content[0].text
        assert "PYTHON" in types_text
        assert "UNKNOWN" in types_text


class TestRulesIntegration:
    """Tests for rules engine integration."""
    
    def test_load_african_mobile_money_rules(self):
        """Test loading African mobile money rules."""
        rules_path = Path(__file__).parents[2] / "rules" / "african_mobile_money.yaml"
        
        if rules_path.exists():
            custom = CustomRules.from_file(rules_path)
            
            assert len(custom) > 0
            # Check for key rules
            rule_names = {r.name for r in custom.get_all_rules()}
            assert "mpesa_stk_push" in rule_names
            assert "airtel_money_transaction" in rule_names
            assert "mtn_momo_transaction" in rule_names
    
    def test_load_healthcare_rules(self):
        """Test loading healthcare rules."""
        rules_path = Path(__file__).parents[2] / "rules" / "healthcare.yaml"
        
        if rules_path.exists():
            custom = CustomRules.from_file(rules_path)
            
            assert len(custom) > 0
            rule_names = {r.name for r in custom.get_all_rules()}
            assert "hl7_v2_message" in rule_names
            assert "fhir_json_bundle" in rule_names
            assert "dicom_file" in rule_names
    
    def test_load_logistics_rules(self):
        """Test loading logistics rules."""
        rules_path = Path(__file__).parents[2] / "rules" / "logistics.yaml"
        
        if rules_path.exists():
            custom = CustomRules.from_file(rules_path)
            
            assert len(custom) > 0
            rule_names = {r.name for r in custom.get_all_rules()}
            assert "edifact_message" in rule_names
            assert "gs1_epcis_event" in rule_names
            assert "customs_declaration" in rule_names


class TestCLIIntegration:
    """Tests for CLI integration."""
    
    def test_cli_help(self):
        """Test CLI help output."""
        from magika_enhanced.cli.main import create_parser
        
        parser = create_parser()
        
        # Should not raise
        parser.parse_args(["--help"])
    
    def test_cli_version(self):
        """Test CLI version output."""
        from magika_enhanced.cli.main import create_parser
        
        parser = create_parser()
        
        # Should not raise
        try:
            parser.parse_args(["--version"])
        except SystemExit:
            pass  # Expected
    
    def test_cli_basic_usage(self):
        """Test basic CLI usage."""
        import subprocess
        import sys
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            test_file.write_text("print('hello')")
            
            result = subprocess.run([
                sys.executable, "-m", "magika_enhanced.cli.main",
                str(test_file)
            ], capture_output=True, text=True, cwd=Path(__file__).parents[2])
            
            assert result.returncode == 0
            assert "test.py" in result.stdout


class TestEndToEnd:
    """End-to-end tests."""
    
    def test_full_workflow_sync(self):
        """Test full workflow: identify -> custom rules -> batch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test files
            (tmpdir / "file1.py").write_text("import os\nprint('hello')")
            (tmpdir / "file2.json").write_text('{"key": "value"}')
            (tmpdir / "file3.txt").write_text("plain text")
            
            # Run identification
            m = Magika()
            results = m.identify_paths(list(tmpdir.glob("*")))
            
            assert len(results) == 3
            assert all(r.ok for r in results)
            
            # Check labels
            labels = {r.prediction.output.label for r in results if r.prediction}
            assert len(labels) >= 2  # At least 2 different types
    
    @pytest.mark.asyncio
    async def test_full_workflow_async(self):
        """Test full async workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test files
            for i in range(20):
                (tmpdir / f"file{i}.txt").write_text(f"content {i}")
            
            # Run async identification
            m = MagikaAsync(max_concurrent=10)
            results = await m.identify_paths(list(tmpdir.glob("*")))
            
            assert len(results) == 20
            assert all(r.ok for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])