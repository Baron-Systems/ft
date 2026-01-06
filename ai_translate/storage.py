"""CSV-based translation storage and management."""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ai_translate.policy import TranslationContext


@dataclass
class TranslationEntry:
    """Translation entry with context."""

    source_text: str
    translated_text: str
    context: TranslationContext
    source_file: Optional[str] = None
    line_number: int = 0


class TranslationStorage:
    """CSV-based translation storage."""

    def __init__(self, storage_path: Path, lang: str):
        """
        Initialize translation storage.

        Args:
            storage_path: Base path for storage
            lang: Language code
        """
        self.storage_path = Path(storage_path)
        self.lang = lang
        self.csv_path = self.storage_path / "translations" / f"{lang}.csv"
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, TranslationEntry] = {}
        self._load_cache()

    def _load_cache(self):
        """Load existing translations from CSV."""
        if not self.csv_path.exists():
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_key(row["source_text"], row.get("context", ""))
                    context = TranslationContext(
                        layer=row.get("layer", "A"),
                        app=row.get("app"),
                        doctype=row.get("doctype"),
                        fieldname=row.get("fieldname"),
                    )
                    self._cache[key] = TranslationEntry(
                        source_text=row["source_text"],
                        translated_text=row["translated_text"],
                        context=context,
                        source_file=row.get("source_file"),
                        line_number=int(row.get("line_number", 0)),
                    )
        except Exception:
            pass  # Start fresh if CSV is corrupted

    def _make_key(self, source_text: str, context_str: str = "") -> str:
        """Create cache key."""
        combined = f"{source_text}|{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(
        self, source_text: str, context: TranslationContext
    ) -> Optional[str]:
        """
        Get translation for source text.

        Args:
            source_text: Source text
            context: Translation context

        Returns:
            Translated text or None
        """
        context_str = self._context_to_string(context)
        key = self._make_key(source_text, context_str)
        entry = self._cache.get(key)
        if entry:
            return entry.translated_text
        return None

    def set(
        self,
        source_text: str,
        translated_text: str,
        context: TranslationContext,
        source_file: Optional[str] = None,
        line_number: int = 0,
    ):
        """
        Store translation.

        Args:
            source_text: Source text
            translated_text: Translated text
            context: Translation context
            source_file: Source file path
            line_number: Line number
        """
        context_str = self._context_to_string(context)
        key = self._make_key(source_text, context_str)
        entry = TranslationEntry(
            source_text=source_text,
            translated_text=translated_text,
            context=context,
            source_file=source_file,
            line_number=line_number,
        )
        self._cache[key] = entry

    def save(self):
        """Save all translations to CSV."""
        if not self._cache:
            return

        # Normalize and deduplicate
        normalized: Dict[str, TranslationEntry] = {}
        for entry in self._cache.values():
            normalized_text = self._normalize_text(entry.source_text)
            key = self._make_key(normalized_text, self._context_to_string(entry.context))
            if key not in normalized:
                normalized[key] = entry

        # Write to CSV
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "source_text",
                "translated_text",
                "layer",
                "app",
                "doctype",
                "fieldname",
                "source_file",
                "line_number",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in normalized.values():
                writer.writerow({
                    "source_text": entry.source_text,
                    "translated_text": entry.translated_text,
                    "layer": entry.context.layer,
                    "app": entry.context.app or "",
                    "doctype": entry.context.doctype or "",
                    "fieldname": entry.context.fieldname or "",
                    "source_file": entry.source_file or "",
                    "line_number": entry.line_number,
                })

    def _normalize_text(self, text: str) -> str:
        """Normalize text for deduplication."""
        return " ".join(text.split())

    def _context_to_string(self, context: TranslationContext) -> str:
        """Convert context to string for key generation."""
        parts = [
            context.layer,
            context.app or "",
            context.doctype or "",
            context.fieldname or "",
        ]
        return "|".join(parts)

    def get_all(self) -> List[TranslationEntry]:
        """Get all translation entries."""
        return list(self._cache.values())

    def deduplicate(self):
        """Remove duplicate entries."""
        seen: Set[str] = set()
        unique: Dict[str, TranslationEntry] = {}
        for key, entry in self._cache.items():
            normalized = self._normalize_text(entry.source_text)
            if normalized not in seen:
                seen.add(normalized)
                unique[key] = entry
        self._cache = unique

