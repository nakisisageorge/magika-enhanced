"""
MCP (Model Context Protocol) server for magika-enhanced.

Exposes file detection capabilities to AI agents via MCP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from pydantic import BaseModel, Field

from magika_enhanced import MagikaAsync, CustomRules
from magika_enhanced.types import ContentTypeLabel, MagikaResult

logger = logging.getLogger(__name__)


class IdentifyFileParams(BaseModel):
    path: str = Field(..., description="Path to file to identify")
    prediction_mode: Optional[str] = Field(None, description="Prediction mode: best_guess, medium_confidence, high_confidence")


class IdentifyBytesParams(BaseModel):
    content: str = Field(..., description="Base64 encoded file content")
    filename: Optional[str] = Field(None, description="Optional filename for extension matching")


class IdentifyPathsParams(BaseModel):
    paths: List[str] = Field(..., description="List of file paths to identify")
    max_concurrent: Optional[int] = Field(None, description="Maximum concurrent operations")


class LoadCustomRulesParams(BaseModel):
    rules_path: str = Field(..., description="Path to custom rules YAML/JSON file")


class GetContentTypesParams(BaseModel):
    pass


class MagikaMCPServer:
    """MCP server for magika-enhanced file detection."""
    
    def __init__(
        self,
        *,
        model_dir: Optional[Path] = None,
        prediction_mode: str = "high_confidence",
        custom_rules_path: Optional[Path] = None,
        max_concurrent: int = 50,
    ) -> None:
        self.magika = MagikaAsync(
            model_dir=model_dir,
            prediction_mode=prediction_mode,
            max_concurrent=max_concurrent,
        )
        
        if custom_rules_path:
            self.magika._custom_rules = CustomRules.from_file(custom_rules_path)
        
        self.server = Server("magika-enhanced")
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register MCP tools."""
        
        @self.server.call_tool()
        async def identify_file(arguments: Dict[str, Any]) -> CallToolResult:
            """Identify a single file by path."""
            try:
                params = IdentifyFileParams(**arguments)
                path = Path(params.path)
                
                if not path.exists():
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"File not found: {path}")],
                        isError=True,
                    )
                
                result = await self.magika.identify_path(path)
                return CallToolResult(
                    content=[TextContent(type="text", text=self._format_result(result))],
                )
            except Exception as e:
                logger.exception("identify_file failed")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )
        
        @self.server.call_tool()
        async def identify_bytes(arguments: Dict[str, Any]) -> CallToolResult:
            """Identify raw bytes content."""
            try:
                params = IdentifyBytesParams(**arguments)
                import base64
                content = base64.b64decode(params.content)
                
                result = await self.magika.identify_bytes(content)
                return CallToolResult(
                    content=[TextContent(type="text", text=self._format_result(result))],
                )
            except Exception as e:
                logger.exception("identify_bytes failed")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )
        
        @self.server.call_tool()
        async def identify_paths(arguments: Dict[str, Any]) -> CallToolResult:
            """Identify multiple files."""
            try:
                params = IdentifyPathsParams(**arguments)
                paths = [Path(p) for p in params.paths]
                
                results = await self.magika.identify_paths(paths, max_concurrent=params.max_concurrent)
                
                output = []
                for r in results:
                    output.append(self._format_result(r))
                
                return CallToolResult(
                    content=[TextContent(type="text", text="\n\n".join(output))],
                )
            except Exception as e:
                logger.exception("identify_paths failed")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )
        
        @self.server.call_tool()
        async def get_content_types(arguments: Dict[str, Any]) -> CallToolResult:
            """Get all supported content type labels."""
            try:
                types = self.magika.get_output_content_types()
                return CallToolResult(
                    content=[TextContent(type="text", text="\n".join(t.value for t in types))],
                )
            except Exception as e:
                logger.exception("get_content_types failed")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )
        
        @self.server.call_tool()
        async def load_custom_rules(arguments: Dict[str, Any]) -> CallToolResult:
            """Load custom rules from file."""
            try:
                params = LoadCustomRulesParams(**arguments)
                self.magika._custom_rules = CustomRules.from_file(params.rules_path)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Loaded custom rules from {params.rules_path}")],
                )
            except Exception as e:
                logger.exception("load_custom_rules failed")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="identify_file",
                    description="Identify the content type of a single file by path",
                    inputSchema=IdentifyFileParams.model_json_schema(),
                ),
                Tool(
                    name="identify_bytes",
                    description="Identify the content type of raw bytes (base64 encoded)",
                    inputSchema=IdentifyBytesParams.model_json_schema(),
                ),
                Tool(
                    name="identify_paths",
                    description="Identify content types of multiple files concurrently",
                    inputSchema=IdentifyPathsParams.model_json_schema(),
                ),
                Tool(
                    name="get_content_types",
                    description="Get list of all supported content type labels",
                    inputSchema=GetContentTypesParams.model_json_schema(),
                ),
                Tool(
                    name="load_custom_rules",
                    description="Load custom rules from YAML/JSON file",
                    inputSchema=LoadCustomRulesParams.model_json_schema(),
                ),
            ]

    def _format_result(self, result: MagikaResult) -> str:
        """Format a MagikaResult for display."""
        if not result.ok:
            return f"Path: {result.path}\nStatus: {result.status.value}\nError: {result.status.value}"
        
        pred = result.prediction
        if pred is None:
            return f"Path: {result.path}\nStatus: {result.status.value}\nNo prediction available"
        
        lines = [
            f"Path: {result.path}",
            f"Status: {result.status.value}",
            f"Label: {pred.output.label.value}",
            f"MIME Type: {pred.output.mime_type}",
            f"Group: {pred.output.group}",
            f"Description: {pred.output.description}",
            f"Score: {pred.score:.2%}",
            f"Overwrite Reason: {pred.overwrite_reason.value}",
        ]
        
        if pred.dl.label != pred.output.label:
            lines.append(f"Deep Learning Label: {pred.dl.label.value}")
            lines.append(f"Deep Learning MIME: {pred.dl.mime_type}")
        
        if pred.output.extensions:
            lines.append(f"Extensions: {', '.join(pred.output.extensions)}")
        
        return "\n".join(lines)

    async def run_stdio(self) -> None:
        """Run MCP server over stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())

    async def run_http(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Run MCP server over HTTP transport."""
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        
        sse = SseServerTransport("/messages/")
        
        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await self.server.run(streams[0], streams[1], self.server.create_initialization_options())
        
        app = Starlette(
            routes=[
                Route("/sse", handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )
        
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


async def main() -> None:
    """Entry point for magika-mcp command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Magika Enhanced MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--model-dir", type=Path, help="Path to Magika model directory")
    parser.add_argument("--prediction-mode", choices=["best_guess", "medium_confidence", "high_confidence"], default="high_confidence")
    parser.add_argument("--custom-rules", type=Path, help="Path to custom rules file")
    parser.add_argument("--max-concurrent", type=int, default=50)
    parser.add_argument("--verbose", "-v", action="store_true")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    server = MagikaMCPServer(
        model_dir=args.model_dir,
        prediction_mode=args.prediction_mode,
        custom_rules_path=args.custom_rules,
        max_concurrent=args.max_concurrent,
    )
    
    if args.transport == "stdio":
        await server.run_stdio()
    else:
        await server.run_http(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())