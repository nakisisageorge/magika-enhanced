"""
Custom rules engine for domain-specific content type detection.

Supports YAML-defined rules with magic bytes, regex, extensions, and structural validation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import yaml

from magika_enhanced.types import ContentTypeLabel, ContentTypeInfo

logger = logging.getLogger(__name__)


@dataclass
class MagicBytesRule:
    """Magic bytes pattern for file identification."""
    offset: int = 0
    pattern: str = ""  # Hex string or raw bytes pattern
    mask: Optional[str] = None  # Optional mask for wildcard matching


@dataclass
class Rule:
    """Single custom content type detection rule."""
    name: str
    label: ContentTypeLabel
    group: str
    mime_type: str
    extensions: List[str] = field(default_factory=list)
    magic_bytes: Optional[MagicBytesRule] = None
    regex: Optional[str] = None
    description: str = ""
    is_text: bool = False
    priority: int = 0  # Higher priority rules checked first
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.label, str):
            self.label = ContentTypeLabel(self.label)
        if self.magic_bytes and isinstance(self.magic_bytes, dict):
            self.magic_bytes = MagicBytesRule(**self.magic_bytes)


@dataclass
class RuleSet:
    """Collection of rules with metadata."""
    name: str = "custom"
    version: str = "1.0"
    description: str = ""
    rules: List[Rule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def get_rules_for_extension(self, ext: str) -> List[Rule]:
        """Get rules that match a file extension."""
        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        return [r for r in self.rules if ext in [e.lower() for e in r.extensions]]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "rules": [
                {
                    "name": r.name,
                    "label": r.label.value,
                    "group": r.group,
                    "mime_type": r.mime_type,
                    "extensions": r.extensions,
                    "magic_bytes": {
                        "offset": r.magic_bytes.offset,
                        "pattern": r.magic_bytes.pattern,
                        "mask": r.magic_bytes.mask,
                    } if r.magic_bytes else None,
                    "regex": r.regex,
                    "description": r.description,
                    "is_text": r.is_text,
                    "priority": r.priority,
                    "metadata": r.metadata,
                }
                for r in self.rules
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleSet":
        """Deserialize from dictionary."""
        rules = []
        for r_data in data.get("rules", []):
            mb = r_data.get("magic_bytes")
            rule = Rule(
                name=r_data["name"],
                label=r_data["label"],
                group=r_data["group"],
                mime_type=r_data["mime_type"],
                extensions=r_data.get("extensions", []),
                magic_bytes=MagicBytesRule(**mb) if mb else None,
                regex=r_data.get("regex"),
                description=r_data.get("description", ""),
                is_text=r_data.get("is_text", False),
                priority=r_data.get("priority", 0),
                metadata=r_data.get("metadata", {}),
            )
            rules.append(rule)
        
        return cls(
            name=data.get("name", "custom"),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            rules=rules,
            metadata=data.get("metadata", {}),
        )


class CustomRules:
    """
    Custom rules engine for extending magika's detection.
    
    Supports:
    - YAML/JSON rule definitions
    - Magic bytes matching (with offset and mask)
    - Regex pattern matching
    - Extension-based matching
    - Priority-based rule ordering
    - Hot-reload capability
    """

    def __init__(self, rules: Optional[Union[RuleSet, Sequence[Rule], str, Path]] = None) -> None:
        self._rule_sets: List[RuleSet] = []
        self._compiled_regex: Dict[str, re.Pattern] = {}
        self._magic_bytes_cache: Dict[str, bytes] = {}
        
        if rules:
            if isinstance(rules, RuleSet):
                self._rule_sets.append(rules)
            elif isinstance(rules, (str, Path)):
                self.load_from_file(rules)
            elif isinstance(rules, Sequence):
                rs = RuleSet(rules=list(rules))
                self._rule_sets.append(rs)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "CustomRules":
        """Load rules from YAML/JSON file."""
        path = Path(path)
        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                import json
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        
        # Handle both single ruleset and list of rulesets
        if isinstance(data, dict) and "rules" in data:
            rule_sets = [RuleSet.from_dict(data)]
        elif isinstance(data, list):
            rule_sets = [RuleSet.from_dict(d) for d in data]
        else:
            raise ValueError("Invalid rules file format")
        
        instance = cls()
        instance._rule_sets = rule_sets
        instance._compile_patterns()
        return instance

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "CustomRules":
        """Load rules from YAML string."""
        data = yaml.safe_load(yaml_str)
        if isinstance(data, dict) and "rules" in data:
            rule_sets = [RuleSet.from_dict(data)]
        elif isinstance(data, list):
            rule_sets = [RuleSet.from_dict(d) for d in data]
        else:
            raise ValueError("Invalid YAML format")
        
        instance = cls()
        instance._rule_sets = rule_sets
        instance._compile_patterns()
        return instance

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns and magic bytes."""
        self._compiled_regex.clear()
        self._magic_bytes_cache.clear()
        
        for rs in self._rule_sets:
            for rule in rs.rules:
                if rule.regex:
                    try:
                        self._compiled_regex[rule.name] = re.compile(rule.regex, re.MULTILINE)
                    except re.error as e:
                        logger.warning(f"Invalid regex in rule '{rule.name}': {e}")
                
                if rule.magic_bytes and rule.magic_bytes.pattern:
                    # Convert hex string to bytes
                    try:
                        pattern = bytes.fromhex(rule.magic_bytes.pattern.replace(" ", "").replace("\\x", ""))
                        self._magic_bytes_cache[rule.name] = pattern
                    except ValueError:
                        # Try as raw string
                        self._magic_bytes_cache[rule.name] = rule.magic_bytes.pattern.encode()

    def load_from_file(self, path: Union[str, Path]) -> None:
        """Load additional rules from file."""
        path = Path(path)
        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                import json
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        
        if isinstance(data, dict) and "rules" in data:
            self._rule_sets.append(RuleSet.from_dict(data))
        elif isinstance(data, list):
            for d in data:
                self._rule_sets.append(RuleSet.from_dict(d))
        
        self._compile_patterns()

    def merge(self, other: "CustomRules") -> None:
        """Merge another CustomRules instance."""
        self._rule_sets.extend(other._rule_sets)
        self._compile_patterns()

    def get_all_rules(self) -> List[Rule]:
        """Get all rules from all rule sets, sorted by priority."""
        all_rules = []
        for rs in self._rule_sets:
            all_rules.extend(rs.rules)
        return sorted(all_rules, key=lambda r: r.priority, reverse=True)

    def match(self, content: bytes, path: Optional[Path] = None) -> Optional[Rule]:
        """
        Match content against custom rules.
        
        Returns the highest priority matching rule, or None.
        """
        rules = self.get_all_rules()
        
        for rule in rules:
            # Check magic bytes first (fastest)
            if rule.magic_bytes and rule.name in self._magic_bytes_cache:
                pattern = self._magic_bytes_cache[rule.name]
                offset = rule.magic_bytes.offset
                if offset + len(pattern) <= len(content):
                    if content[offset:offset + len(pattern)] == pattern:
                        return rule
            
            # Check regex
            if rule.regex and rule.name in self._compiled_regex:
                try:
                    text = content.decode("utf-8", errors="ignore")
                    if self._compiled_regex[rule.name].search(text):
                        return rule
                except UnicodeDecodeError:
                    pass
            
            # Check extension
            if path and rule.extensions:
                ext = path.suffix.lower()
                if ext in [e.lower() for e in rule.extensions]:
                    return rule
        
        return None

    def to_yaml(self) -> str:
        """Serialize all rule sets to YAML."""
        if len(self._rule_sets) == 1:
            return yaml.dump(self._rule_sets[0].to_dict(), sort_keys=False)
        return yaml.dump([rs.to_dict() for rs in self._rule_sets], sort_keys=False)

    def save(self, path: Union[str, Path]) -> None:
        """Save rules to YAML file."""
        path = Path(path)
        with open(path, "w") as f:
            f.write(self.to_yaml())

    def __len__(self) -> int:
        return sum(len(rs.rules) for rs in self._rule_sets)

    def __bool__(self) -> bool:
        return len(self) > 0