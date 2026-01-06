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
            storage_path: Base path for storage (can be app translations dir or site dir)
            lang: Language code
        """
        self.storage_path = Path(storage_path)
        self.lang = lang
        
        # Check if storage_path is already the translations directory
        if storage_path.name == "translations":
            self.csv_path = storage_path / f"{lang}.csv"
        else:
            # Assume it's a site path, create translations subdirectory
            self.csv_path = storage_path / "translations" / f"{lang}.csv"
        
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
                # Frappe standard CSV has: source_text, translated_text
                # Our extended format may have additional columns
                for row in reader:
                    if "source_text" not in row or "translated_text" not in row:
                        continue
                    
                    source_text = row["source_text"]
                    translated_text = row["translated_text"]
                    
                    # Use context from row if available, otherwise create default
                    context = TranslationContext(
                        layer=row.get("layer", "A"),
                        app=row.get("app"),
                        doctype=row.get("doctype"),
                        fieldname=row.get("fieldname"),
                    )
                    
                    # Create key using source_text only (Frappe standard)
                    # This allows merging with existing Frappe translation files
                    key = self._make_key(source_text, "")
                    
                    self._cache[key] = TranslationEntry(
                        source_text=source_text,
                        translated_text=translated_text,
                        context=context,
                        source_file=row.get("source_file"),
                        line_number=int(row.get("line_number", 0)),
                    )
        except Exception as e:
            # Start fresh if CSV is corrupted
            pass

    def _make_key(self, source_text: str, context_str: str = "") -> str:
        """Create cache key."""
        combined = f"{source_text}|{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(
        self, source_text: str, context: Optional[TranslationContext] = None
    ) -> Optional[str]:
        """
        Get translation for source text.

        Args:
            source_text: Source text
            context: Translation context (optional, for compatibility)

        Returns:
            Translated text or None
        """
        # Frappe uses source_text as unique key (case-sensitive)
        # Try exact match first (Frappe standard)
        key = self._make_key(source_text, "")
        entry = self._cache.get(key)
        if entry:
            return entry.translated_text
        
        # Try with context if provided (for backward compatibility)
        if context:
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
        # Frappe standard: use source_text as unique key
        # This allows overwriting existing translations and merging with Frappe files
        key = self._make_key(source_text, "")
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

        # Normalize and deduplicate by source_text (Frappe standard)
        normalized: Dict[str, TranslationEntry] = {}
        for entry in self._cache.values():
            # Use source_text as unique key (Frappe standard)
            # If duplicate, keep the most recent one
            normalized_text = self._normalize_text(entry.source_text)
            key = self._make_key(normalized_text, "")
            if key not in normalized:
                normalized[key] = entry
            else:
                # Update if we have a newer translation
                normalized[key] = entry

        # Write to CSV - Frappe standard format: source_text, translated_text
        # We use minimal format compatible with Frappe's translation system
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            # Frappe standard: only source_text and translated_text
            # Additional columns are optional metadata
            fieldnames = [
                "source_text",
                "translated_text",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Sort by source_text for consistent output
            sorted_entries = sorted(normalized.values(), key=lambda e: e.source_text.lower())
            
            for entry in sorted_entries:
                writer.writerow({
                    "source_text": entry.source_text,
                    "translated_text": entry.translated_text,
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

