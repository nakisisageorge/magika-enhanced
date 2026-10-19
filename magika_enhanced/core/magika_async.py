"""
Asynchronous Magika wrapper for high-throughput operations.

Provides async/await API, concurrent batch processing, and streaming support.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, List, Optional, Sequence, Union

import aiofiles
from magika import Magika as UpstreamMagika, PredictionMode
from magika.types import MagikaResult, MagikaError

from magika_enhanced.rules.engine import CustomRules, RuleSet
from magika_enhanced.types import BatchResult, ContentTypeLabel, MagikaPrediction, PathLike, PathsLike

logger = logging.getLogger(__name__)


class MagikaAsync:
    """
    Enhanced asynchronous Magika wrapper.
    
    Features:
    - Full async/await API
    - Configurable concurrency for batch operations
    - Streaming identification for large files
    - LRU cache with async access
    - Custom rules engine integration
    """

    def __init__(
        self,
        *,
        model_dir: Optional[Path] = None,
        prediction_mode: PredictionMode = PredictionMode.HIGH_CONFIDENCE,
        no_dereference: bool = False,
        verbose: bool = False,
        debug: bool = False,
        use_colors: bool = False,
        rules: Optional[Union[str, Path, CustomRules, RuleSet]] = None,
        rules_files: Optional[Sequence[Union[str, Path]]] = None,
        cache_size: int = 1024,
        max_concurrent: int = 50,
    ) -> None:
        """
        Initialize async Magika.
        
        Args:
            model_dir: Path to model directory
            prediction_mode: Confidence threshold for predictions
            no_dereference: Don't follow symlinks
            verbose: Enable verbose logging
            debug: Enable debug logging
            use_colors: Use colored output in logs
            rules: CustomRules instance, RuleSet, or path to rules file
            rules_files: Additional paths to rules files
            cache_size: Maximum cache entries (0 to disable)
            max_concurrent: Maximum concurrent operations for batch processing
        """
        self._upstream = UpstreamMagika(
            model_dir=model_dir,
            prediction_mode=prediction_mode,
            no_dereference=no_dereference,
            verbose=verbose,
            debug=debug,
            use_colors=use_colors,
            rules=rules,
            rules_files=rules_files,
        )
        
        self._prediction_mode = prediction_mode
        self._no_dereference = no_dereference
        self._cache_size = cache_size
        self._max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cache = {} if cache_size > 0 else None
        self._cache_order = []
        self._cache_lock = asyncio.Lock()
        
        # Load custom rules
        self._custom_rules: Optional[CustomRules] = None
        if rules is not None:
            if isinstance(rules, (str, Path)):
                self._custom_rules = CustomRules.from_file(rules)
            elif isinstance(rules, (CustomRules, RuleSet)):
                self._custom_rules = rules if isinstance(rules, CustomRules) else CustomRules(rules)
        
        if rules_files:
            for rf in rules_files:
                additional = CustomRules.from_file(rf)
                if self._custom_rules:
                    self._custom_rules.merge(additional)
                else:
                    self._custom_rules = additional

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    def _cache_key(self, content: bytes) -> bytes:
        """Generate cache key from content sample."""
        import hashlib
        sample = content[:8192]
        return hashlib.sha256(sample + str(len(content)).encode()).digest()[:16]

    async def _get_cached(self, key: bytes) -> Optional[MagikaPrediction]:
        """Get cached prediction if available (async)."""
        if self._cache is None:
            return None
        async with self._cache_lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache_order.remove(key)
                self._cache_order.append(key)
                return self._cache[key]
        return None

    async def _set_cached(self, key: bytes, prediction: MagikaPrediction) -> None:
        """Cache prediction with LRU eviction (async)."""
        if self._cache is None:
            return
        async with self._cache_lock:
            if len(self._cache) >= self._cache_size and self._cache_size > 0:
                oldest = self._cache_order.pop(0)
                del self._cache[oldest]
            self._cache[key] = prediction
            self._cache_order.append(key)

    async def identify_path(self, path: PathLike) -> MagikaResult:
        """
        Identify content type of a file by path (async).
        
        Uses cache for repeated content. Runs upstream in thread pool.
        """
        path = Path(path)
        
        # Check cache first
        if self._cache is not None:
            try:
                async with aiofiles.open(path, "rb") as f:
                    content = await f.read(8192)
                key = self._cache_key(content)
                cached = await self._get_cached(key)
                if cached is not None:
                    return MagikaResult(path=path, status=cached.status, prediction=cached)
            except (OSError, IOError):
                pass
        
        # Run upstream in thread pool (blocking call)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._upstream.identify_path, path)
        
        # Cache successful results
        if self._cache is not None and result.ok and result.prediction:
            try:
                async with aiofiles.open(path, "rb") as f:
                    content = await f.read(8192)
                key = self._cache_key(content)
                await self._set_cached(key, result.prediction)
            except (OSError, IOError):
                pass
        
        return result

    async def identify_paths(
        self, 
        paths: PathsLike, 
        *,
        max_concurrent: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[MagikaResult]:
        """
        Identify content types of multiple files concurrently.
        
        Args:
            paths: Sequence of file paths
            max_concurrent: Override default concurrency limit
            progress_callback: Optional async callback(current, total, result)
        
        Returns:
            List of MagikaResult in same order as input paths
        """
        semaphore = asyncio.Semaphore(max_concurrent or self._max_concurrent)
        paths_list = list(paths)
        results: List[Optional[MagikaResult]] = [None] * len(paths_list)
        completed = 0
        
        async def process_one(idx: int, path: Path) -> None:
            nonlocal completed
            async with semaphore:
                result = await self.identify_path(path)
                results[idx] = result
                completed += 1
                if progress_callback:
                    await progress_callback(completed, len(paths_list), result)
        
        tasks = [process_one(i, Path(p)) for i, p in enumerate(paths_list)]
        await asyncio.gather(*tasks)
        
        # Type narrowing - all should be filled now
        return [r for r in results if r is not None]

    async def identify_bytes(self, content: bytes) -> MagikaResult:
        """
        Identify content type of raw bytes (async).
        
        Uses cache for repeated content.
        """
        if self._cache is not None:
            key = self._cache_key(content)
            cached = await self._get_cached(key)
            if cached is not None:
                return MagikaResult(path=Path("-"), status=cached.status, prediction=cached)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._upstream.identify_bytes, content)
        
        if self._cache is not None and result.ok and result.prediction:
            key = self._cache_key(content)
            await self._set_cached(key, result.prediction)
        
        return result

    async def identify_stream(self, stream) -> MagikaResult:
        """
        Identify content type from an async binary stream.
        
        Reads beginning and end of stream for detection.
        """
        # For async streams, we need to read the content
        # This is a simplified implementation
        content = b""
        try:
            # Try to read first chunk and last chunk
            stream.seek(0)
            head = stream.read(4096)
            stream.seek(0, 2)  # Seek to end
            size = stream.tell()
            if size > 4096:
                stream.seek(-4096, 2)
                tail = stream.read(4096)
            else:
                tail = head
            content = head + tail
            stream.seek(0)
        except (AttributeError, OSError, IOError):
            # Fallback: read all (not recommended for large streams)
            content = stream.read()
            stream.seek(0)
        
        return await self.identify_bytes(content)

    async def identify_async_stream(self, stream: AsyncIterator[bytes]) -> MagikaResult:
        """
        Identify content type from an async iterator of bytes.
        
        Buffers first and last chunks for detection.
        """
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        
        if not chunks:
            return await self.identify_bytes(b"")
        
        # Combine first and last chunks
        head = chunks[0][:4096]
        tail = chunks[-1][-4096:] if len(chunks) > 1 else head
        content = head + tail
        
        return await self.identify_bytes(content)

    async def identify_file_stream(self, path: PathLike, chunk_size: int = 4096) -> MagikaResult:
        """
        Identify content type by streaming file (memory efficient).
        
        Reads only first and last chunk for detection.
        """
        path = Path(path)
        
        try:
            async with aiofiles.open(path, "rb") as f:
                # Read head
                head = await f.read(chunk_size)
                
                # Seek to end and read tail
                await f.seek(0, 2)
                size = await f.tell()
                
                if size > chunk_size:
                    await f.seek(-chunk_size, 2)
                    tail = await f.read(chunk_size)
                else:
                    tail = head
                
                content = head + tail
                return await self.identify_bytes(content)
        except (OSError, IOError) as e:
            return MagikaResult(
                path=path,
                status=MagikaResult.Status.FILE_NOT_FOUND_ERROR if isinstance(e, FileNotFoundError) else MagikaResult.Status.PERMISSION_ERROR,
                prediction=None,
            )

    async def scan_directory(
        self,
        root: PathLike,
        *,
        recursive: bool = True,
        pattern: Optional[str] = None,
        max_concurrent: Optional[int] = None,
        follow_symlinks: bool = False,
    ) -> AsyncIterator[MagikaResult]:
        """
        Asynchronously scan directory and yield results.
        
        Memory efficient for large directory trees.
        """
        root = Path(root)
        semaphore = asyncio.Semaphore(max_concurrent or self._max_concurrent)
        
        async def process_file(path: Path) -> MagikaResult:
            async with semaphore:
                return await self.identify_path(path)
        
        if recursive:
            paths = root.rglob("*") if pattern is None else root.rglob(pattern)
        else:
            paths = root.glob("*") if pattern is None else root.glob(pattern)
        
        tasks = []
        for path in paths:
            if path.is_file() or (follow_symlinks and path.is_symlink()):
                tasks.append(process_file(path))
                # Yield in batches to control memory
                if len(tasks) >= (max_concurrent or self._max_concurrent) * 2:
                    for coro in asyncio.as_completed(tasks):
                        yield await coro
                    tasks = []
        
        # Process remaining
        for coro in asyncio.as_completed(tasks):
            yield await coro

    def get_output_content_types(self) -> List[ContentTypeLabel]:
        """Get list of all possible output content type labels."""
        return [ContentTypeLabel(ct) for ct in self._upstream.get_output_content_types()]

    def get_model_content_types(self) -> List[ContentTypeLabel]:
        """Get list of all model content type labels."""
        return [ContentTypeLabel(ct) for ct in self._upstream.get_model_content_types()]

    @property
    def prediction_mode(self) -> PredictionMode:
        return self._prediction_mode

    @property
    def custom_rules(self) -> Optional[CustomRules]:
        return self._custom_rules

    async def clear_cache(self) -> None:
        """Clear the prediction cache."""
        if self._cache is not None:
            async with self._cache_lock:
                self._cache.clear()
                self._cache_order.clear()

    def cache_info(self) -> dict:
        """Get cache statistics."""
        if self._cache is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "size": len(self._cache),
            "max_size": self._cache_size,
        }