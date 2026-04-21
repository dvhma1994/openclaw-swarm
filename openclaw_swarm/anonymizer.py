"""
Anonymizer - Privacy-first PII protection
Inspired by: zeroc00I/LLM-anonymization
"""

import os
import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
from rich.console import Console

console = Console()


@dataclass
class PIIEntity:
    """A detected PII entity"""

    type: str  # email, ip, phone, api_key, etc.
    value: str
    start: int  # position in text
    end: int
    confidence: float


@dataclass
class AnonymizedResult:
    """Result of anonymization"""

    original: str
    anonymized: str
    entities: List[PIIEntity]
    mapping: Dict[str, str]  # token -> original
    timestamp: str


class Anonymizer:
    """
    Privacy-first PII protection for LLM prompts

    Features:
    - Detect PII (emails, IPs, phone numbers, API keys, etc.)
    - Replace with tokens
    - Restore after LLM response
    - Configurable patterns
    """

    # Default patterns for PII detection
    DEFAULT_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "ip_address_v6": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
        "phone": r"\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b",
        "api_key": r"\b(?:sk-[a-zA-Z0-9]{20,}|api[_-]?key[_-]?[a-zA-Z0-9]{10,})\b",
        "password": r"\b(?:password|passwd|pwd)\s*[=:]\s*\S+\b",
        "ssn": r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "url": r'https?://[^\s<>"]+|www\.[^\s<>"]+',
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "github_token": r"ghp_[a-zA-Z0-9]{36}",
        "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        "mac_address": r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(
            config_path
            or os.path.join(
                os.path.dirname(__file__), "..", "..", "config", "anonymizer.yaml"
            )
        )

        self.patterns = self.DEFAULT_PATTERNS.copy()
        self.token_prefix = "<PII_"
        self.token_suffix = ">"

        # Session storage for reversibility
        self.session_mapping: Dict[str, str] = {}
        self.vault_path = Path(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "vault")
        )
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def add_pattern(self, name: str, pattern: str) -> None:
        """Add a custom pattern"""
        self.patterns[name] = pattern

    def remove_pattern(self, name: str) -> None:
        """Remove a pattern"""
        self.patterns.pop(name, None)

    def detect_pii(self, text: str) -> List[PIIEntity]:
        """
        Detect all PII entities in text

        Args:
            text: Text to analyze

        Returns:
            List of detected PII entities
        """
        entities = []

        for pii_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                entity = PIIEntity(
                    type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9,  # Default confidence
                )
                entities.append(entity)

        # Sort by position
        entities.sort(key=lambda x: x.start)

        return entities

    def _generate_token(self, pii_type: str, index: int) -> str:
        """Generate a token for PII replacement"""
        return f"{self.token_prefix}{pii_type.upper()}_{index}{self.token_suffix}"

    def anonymize(
        self, text: str, types: Optional[List[str]] = None
    ) -> AnonymizedResult:
        """
        Anonymize PII in text

        Args:
            text: Text to anonymize
            types: Specific PII types to anonymize (None = all)

        Returns:
            AnonymizedResult with mapping
        """
        entities = self.detect_pii(text)

        # Filter by types if specified
        if types:
            entities = [e for e in entities if e.type in types]

        # Create mapping and anonymized text
        mapping: Dict[str, str] = {}
        anonymized = text

        # Process from end to start to preserve positions
        type_counters: Dict[str, int] = {}

        for entity in reversed(entities):
            if entity.type not in type_counters:
                type_counters[entity.type] = 0

            type_counters[entity.type] += 1
            token = self._generate_token(entity.type, type_counters[entity.type])

            mapping[token] = entity.value
            anonymized = anonymized[: entity.start] + token + anonymized[entity.end :]

        # Store in session mapping
        self.session_mapping.update(mapping)

        # Save to vault
        self._save_to_vault(mapping)

        return AnonymizedResult(
            original=text,
            anonymized=anonymized,
            entities=entities,
            mapping=mapping,
            timestamp=datetime.now().isoformat(),
        )

    def de_anonymize(self, text: str, mapping: Optional[Dict[str, str]] = None) -> str:
        """
        Restore original PII from anonymized text

        Args:
            text: Anonymized text
            mapping: Token mapping (uses session mapping if None)

        Returns:
            De-anonymized text
        """
        if mapping is None:
            mapping = self.session_mapping

        result = text
        for token, original in mapping.items():
            result = result.replace(token, original)

        return result

    def _save_to_vault(self, mapping: Dict[str, str]) -> None:
        """Save mapping to encrypted vault"""
        vault_file = (
            self.vault_path / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Hash the values for security (can't retrieve without the session)
        hashed_mapping = {
            token: hashlib.sha256(value.encode()).hexdigest()[:16]
            for token, value in mapping.items()
        }

        with open(vault_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "mapping": hashed_mapping,
                    "types": list(
                        set(
                            t.split("_")[0].replace("<PII_", "") for t in mapping.keys()
                        )
                    ),
                },
                f,
                indent=2,
            )

    def clear_session(self) -> None:
        """Clear session mapping"""
        self.session_mapping.clear()
        console.print("[green]Session mapping cleared[/green]")

    def get_stats(self, text: str) -> Dict[str, int]:
        """
        Get statistics about detected PII

        Args:
            text: Text to analyze

        Returns:
            Dict of PII type -> count
        """
        entities = self.detect_pii(text)

        stats: Dict[str, int] = {}
        for entity in entities:
            stats[entity.type] = stats.get(entity.type, 0) + 1

        return stats

    def is_safe(self, text: str, threshold: int = 0) -> bool:
        """
        Check if text is safe (no PII detected)

        Args:
            text: Text to check
            threshold: Maximum allowed PII entities

        Returns:
            True if safe
        """
        entities = self.detect_pii(text)
        return len(entities) <= threshold

    def process_prompt(
        self, prompt: str, auto_anonymize: bool = True
    ) -> Tuple[str, Dict[str, str]]:
        """
        Process a prompt for LLM

        Args:
            prompt: Original prompt
            auto_anonymize: Whether to automatically anonymize

        Returns:
            (processed_prompt, mapping)
        """
        if not auto_anonymize:
            return prompt, {}

        result = self.anonymize(prompt)

        stats = {
            e.type: len([x for x in result.entities if x.type == e.type])
            for e in result.entities
        }

        if stats:
            console.print(f"[yellow]Anonymized PII: {stats}[/yellow]")

        return result.anonymized, result.mapping

    def process_response(self, response: str, mapping: Dict[str, str]) -> str:
        """
        Process an LLM response

        Args:
            response: LLM response
            mapping: Token mapping from prompt

        Returns:
            De-anonymized response
        """
        # LLM might reference tokens in response
        return self.de_anonymize(response, mapping)


# Convenience functions
def anonymize(text: str) -> Tuple[str, Dict[str, str]]:
    """Quick anonymize"""
    anon = Anonymizer()
    result = anon.anonymize(text)
    return result.anonymized, result.mapping


def de_anonymize(text: str, mapping: Dict[str, str]) -> str:
    """Quick de-anonymize"""
    anon = Anonymizer()
    return anon.de_anonymize(text, mapping)


def check_pii(text: str) -> Dict[str, int]:
    """Check for PII in text"""
    anon = Anonymizer()
    return anon.get_stats(text)
