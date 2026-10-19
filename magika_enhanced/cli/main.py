"""
Command-line interface for magika-enhanced.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from magika_enhanced import Magika, MagikaAsync
from magika_enhanced.rules import CustomRules

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="magika-enhanced",
        description="Enhanced AI-powered file content type detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (compatible with upstream magika)
  magika-enhanced ./file.pdf
  magika-enhanced -r ./project --json
  
  # Async batch processing
  magika-enhanced -r ./data --async --max-concurrent 20 --json
  
  # With custom rules
  magika-enhanced --rules ./rules/african_mobile_money.yaml ./transaction.mpesa
  
  # Output formats
  magika-enhanced ./file --json
  magika-enhanced ./file --jsonl
  magika-enhanced ./file --format custom --template "%p: %l (%s%%)"
""",
    )
    
    # Input
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to analyze",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan directories",
    )
    parser.add_argument(
        "--pattern",
        help="Glob pattern for file matching (e.g., '*.pdf')",
    )
    
    # Model options
    parser.add_argument(
        "--model-dir",
        type=Path,
        help="Path to Magika model directory",
    )
    parser.add_argument(
        "--prediction-mode",
        choices=["best_guess", "medium_confidence", "high_confidence"],
        default="high_confidence",
        help="Prediction confidence threshold",
    )
    
    # Custom rules
    parser.add_argument(
        "--rules",
        type=Path,
        help="Path to custom rules YAML/JSON file",
    )
    parser.add_argument(
        "--rules-files",
        type=Path,
        nargs="*",
        help="Additional custom rules files",
    )
    
    # Output options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output results as JSON Lines",
    )
    parser.add_argument(
        "--format",
        choices=["default", "json", "jsonl", "csv", "custom"],
        default="default",
        help="Output format",
    )
    parser.add_argument(
        "--template",
        help="Custom format template (use with --format custom)",
    )
    parser.add_argument(
        "--output-score",
        action="store_true",
        help="Include prediction score in output",
    )
    parser.add_argument(
        "--output-mime",
        action="store_true",
        help="Output MIME type",
    )
    parser.add_argument(
        "--output-label",
        action="store_true",
        help="Output content type label",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    
    # Async options
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use async API for batch processing",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=50,
        help="Maximum concurrent operations (async mode)",
    )
    
    # Cache
    parser.add_argument(
        "--cache-size",
        type=int,
        default=1024,
        help="Cache size for repeated content (0 to disable)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache",
    )
    
    # Other
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    
    return parser


def format_result_default(result, args) -> str:
    """Format result in default human-readable format."""
    if not result.ok:
        return f"{result.path}: ERROR ({result.status.value})"
    
    pred = result.prediction
    if pred is None:
        return f"{result.path}: UNKNOWN"
    
    parts = [f"{result.path}: {pred.output.label.value}"]
    
    if args.output_mime:
        parts.append(f"({pred.output.mime_type})")
    
    if args.output_score:
        parts.append(f"[{pred.score:.1%}]")
    
    return " ".join(parts)


def format_result_json(result) -> dict:
    """Format result as JSON object."""
    if not result.ok:
        return {
            "path": str(result.path),
            "status": result.status.value,
            "ok": False,
        }
    
    pred = result.prediction
    if pred is None:
        return {
            "path": str(result.path),
            "status": result.status.value,
            "ok": True,
            "prediction": None,
        }
    
    return {
        "path": str(result.path),
        "status": result.status.value,
        "ok": True,
        "prediction": {
            "label": pred.output.label.value,
            "mime_type": pred.output.mime_type,
            "group": pred.output.group,
            "description": pred.output.description,
            "extensions": pred.output.extensions,
            "is_text": pred.output.is_text,
            "score": pred.score,
            "overwrite_reason": pred.overwrite_reason.value,
            "deep_learning": {
                "label": pred.dl.label.value,
                "mime_type": pred.dl.mime_type,
                "group": pred.dl.group,
                "description": pred.dl.description,
            } if pred.dl.label != pred.output.label else None,
        },
    }


def format_result_csv(result) -> List[str]:
    """Format result as CSV row."""
    if not result.ok:
        return [str(result.path), result.status.value, "", "", "", "", "", ""]
    
    pred = result.prediction
    if pred is None:
        return [str(result.path), result.status.value, "", "", "", "", "", ""]
    
    return [
        str(result.path),
        result.status.value,
        pred.output.label.value,
        pred.output.mime_type,
        pred.output.group,
        pred.output.description,
        f"{pred.score:.4f}",
        pred.overwrite_reason.value,
    ]


async def run_async(args, paths: List[Path]) -> List:
    """Run async identification."""
    magika = MagikaAsync(
        model_dir=args.model_dir,
        prediction_mode=args.prediction_mode,
        max_concurrent=args.max_concurrent,
        cache_size=0 if args.no_cache else args.cache_size,
        rules=args.rules,
        rules_files=args.rules_files,
    )
    
    if len(paths) == 1 and not args.recursive:
        return [await magika.identify_path(paths[0])]
    
    return await magika.identify_paths(paths, max_concurrent=args.max_concurrent)


def run_sync(args, paths: List[Path]) -> List:
    """Run synchronous identification."""
    magika = Magika(
        model_dir=args.model_dir,
        prediction_mode=args.prediction_mode,
        cache_size=0 if args.no_cache else args.cache_size,
        rules=args.rules,
        rules_files=args.rules_files,
    )
    
    if len(paths) == 1 and not args.recursive:
        return [magika.identify_path(paths[0])]
    
    return magika.identify_paths(paths)


def collect_paths(args) -> List[Path]:
    """Collect all file paths from arguments."""
    paths = []
    
    for path_str in args.paths:
        path = Path(path_str)
        
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            if args.recursive:
                if args.pattern:
                    paths.extend(path.rglob(args.pattern))
                else:
                    paths.extend(path.rglob("*"))
            else:
                if args.pattern:
                    paths.extend(path.glob(args.pattern))
                else:
                    paths.extend(path.glob("*"))
        else:
            # Try as glob
            import glob
            matches = glob.glob(path_str, recursive=args.recursive)
            paths.extend(Path(m) for m in matches)
    
    # Filter to files only
    paths = [p for p in paths if p.is_file()]
    
    return paths


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Collect paths
    paths = collect_paths(args)
    
    if not paths:
        print("No files to process", file=sys.stderr)
        return 1
    
    # Run identification
    try:
        if args.use_async:
            results = asyncio.run(run_async(args, paths))
        else:
            results = run_sync(args, paths)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        logger.exception("Identification failed")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Output results
    if args.format == "json" or args.json:
        output = [format_result_json(r) for r in results]
        print(json.dumps(output, indent=2))
    elif args.format == "jsonl" or args.jsonl:
        for r in results:
            print(json.dumps(format_result_json(r)))
    elif args.format == "csv":
        import csv
        writer = csv.writer(sys.stdout)
        writer.writerow(["path", "status", "label", "mime_type", "group", "description", "score", "overwrite_reason"])
        for r in results:
            writer.writerow(format_result_csv(r))
    elif args.format == "custom" and args.template:
        for r in results:
            pred = r.prediction
            if pred and r.ok:
                print(args.template
                    .replace("%p", str(r.path))
                    .replace("%l", pred.output.label.value)
                    .replace("%m", pred.output.mime_type)
                    .replace("%g", pred.output.group)
                    .replace("%d", pred.output.description)
                    .replace("%s", f"{pred.score:.1%}")
                    .replace("%r", pred.overwrite_reason.value))
            else:
                print(args.template
                    .replace("%p", str(r.path))
                    .replace("%l", "ERROR")
                    .replace("%m", "")
                    .replace("%g", "")
                    .replace("%d", "")
                    .replace("%s", "0%")
                    .replace("%r", r.status.value))
    else:
        for r in results:
            print(format_result_default(r, args))
    
    # Exit code based on results
    failed = sum(1 for r in results if not r.ok)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())