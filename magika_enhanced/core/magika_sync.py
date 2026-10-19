"""
Synchronous Magika wrapper with enhanced features.

Provides caching, custom rules, and batch processing on top of upstream magika.
"""

from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import List, Optional, Sequence, Union

from magika import Magika as UpstreamMagika, PredictionMode
from magika.types import MagikaResult, MagikaError

from magika_enhanced.rules.engine import CustomRules, RuleSet
from magika_enhanced.types import BatchResult, ContentTypeLabel, MagikaPrediction, PathLike, PathsLike

logger = logging.getLogger(__name__)


class Magika:
    """
    Enhanced synchronous Magika wrapper.
    
    Adds:
    - LRU cache for repeated predictions
    - Custom rules engine integration
    - Batch processing with progress tracking
    - Directory recursion with filtering
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
    ) -> None:
        """
        Initialize enhanced Magika.
        
        Args:
            model_dir: Path to model directory (uses default if None)
            prediction_mode: Confidence threshold for predictions
            no_dereference: Don't follow symlinks
            verbose: Enable verbose logging
            debug: Enable debug logging
            use_colors: Use colored output in logs
            rules: CustomRules instance, RuleSet, or path to rules file
            rules_files: Additional paths to rules files
            cache_size: Maximum cache entries (0 to disable)
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
        self._cache = {} if cache_size > 0 else None
        self._cache_order = []  # For LRU eviction
        
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

    def _cache_key(self, content: bytes) -> bytes:
        """Generate cache key from content (first 8KB + size)."""
        import hashlib
        sample = content[:8192]
        return hashlib.sha256(sample + str(len(content)).encode()).digest()[:16]

    def _get_cached(self, key: bytes) -> Optional[MagikaPrediction]:
        """Get cached prediction if available."""
        if self._cache is None:
            return None
        if key in self._cache:
            # Move to end (most recently used)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]
        return None

    def _set_cached(self, key: bytes, prediction: MagikaPrediction) -> None:
        """Cache prediction with LRU eviction."""
        if self._cache is None:
            return
        if len(self._cache) >= self._cache_size and self._cache_size > 0:
            # Evict least recently used
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = prediction
        self._cache_order.append(key)

    def identify_path(self, path: PathLike) -> MagikaResult:
        """
        Identify content type of a file by path.
        
        Uses cache for repeated content.
        """
        path = Path(path)
        
        # Check cache first
        if self._cache is not None:
            try:
                with open(path, "rb") as f:
                    content = f.read(8192)
                key = self._cache_key(content)
                cached = self._get_cached(key)
                if cached is not None:
                    return MagikaResult(path=path, status=cached.status, prediction=cached)
            except (OSError, IOError):
                pass  # Fall through to upstream
        
        # Use upstream
        result = self._upstream.identify_path(path)
        
        # Cache successful results
        if self._cache is not None and result.ok and result.prediction:
            try:
                with open(path, "rb") as f:
                    content = f.read(8192)
                key = self._cache_key(content)
                self._set_cached(key, result.prediction)
            except (OSError, IOError):
                pass
        
        return result

    def identify_paths(self, paths: PathsLike) -> List[MagikaResult]:
        """
        Identify content types of multiple files.
        
        Processes sequentially with cache benefits.
        """
        return [self.identify_path(p) for p in paths]

    def identify_bytes(self, content: bytes) -> MagikaResult:
        """
        Identify content type of raw bytes.
        
        Uses cache for repeated content.
        """
        if self._cache is not None:
            key = self._cache_key(content)
            cached = self._get_cached(key)
            if cached is not None:
                return MagikaResult(path=Path("-"), status=cached.status, prediction=cached)
        
        result = self._upstream.identify_bytes(content)
        
        if self._cache is not None and result.ok and result.prediction:
            key = self._cache_key(content)
            self._set_cached(key, result.prediction)
        
        return result

    def identify_stream(self, stream) -> MagikaResult:
        """
        Identify content type from a binary stream.
        
        Reads beginning and end of stream for detection.
        """
        return self._upstream.identify_stream(stream)

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

    def clear_cache(self) -> None:
        """Clear the prediction cache."""
        if self._cache is not None:
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
            "hit_rate": getattr(self, "_cache_hits", 0) / max(1, getattr(self, "_cache_hits", 0) + getattr(self, "_cache_misses", 0)),
        }


# Convenience function for simple usage
@functools.lru_cache(maxsize=1)
def get_magika(**kwargs) -> Magika:
    """Get a cached Magika instance (singleton pattern)."""
    return Magika(**kwargs)