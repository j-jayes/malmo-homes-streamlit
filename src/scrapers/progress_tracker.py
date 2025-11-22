"""Persistence helper for tracking which property IDs have been scraped."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Optional


class ProgressTracker:
    """Stores hashed property identifiers to prevent duplicate scraping."""

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = Path(cache_file).expanduser().resolve()
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._identifiers: set[str] = set()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        stored = payload.get("identifiers", [])
        self._identifiers = set(stored)

    @staticmethod
    def _fingerprint(identifier: str) -> str:
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        return digest

    def _resolve_identifier(
        self,
        record: Optional[Mapping[str, str]] = None,
        *,
        property_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[str]:
        candidate = property_id or (record.get("property_id") if record else None)
        if not candidate:
            candidate = url or (record.get("url") if record else None)
        return candidate

    def should_skip(
        self,
        record: Optional[Mapping[str, str]] = None,
        *,
        property_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> bool:
        identifier = self._resolve_identifier(record, property_id=property_id, url=url)
        if not identifier:
            return False
        return self._fingerprint(identifier) in self._identifiers

    def record_success(
        self,
        record: Optional[Mapping[str, str]] = None,
        *,
        property_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        identifier = self._resolve_identifier(record, property_id=property_id, url=url)
        if not identifier:
            return
        fingerprint = self._fingerprint(identifier)
        if fingerprint in self._identifiers:
            return
        self._identifiers.add(fingerprint)
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        payload = {"version": 1, "identifiers": sorted(self._identifiers)}
        self.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._dirty = False

    @property
    def count(self) -> int:
        return len(self._identifiers)