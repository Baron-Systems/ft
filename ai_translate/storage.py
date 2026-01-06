"""CSV-based translation storage and management."""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ai_translate.policy import TranslationContext


@dataclass
class TranslationEntry:
    """Translation entry with context."""

    source_text: str
    translated_text: str
    context: TranslationContext
    source_file: Optional[str] = None
    line_number: int = 0
    confidence: float = 0.95  # Confidence score (0.0-1.0)
    review_status: str = "approved"  # "approved", "needs_review", "rejected"
    needs_review: bool = False  # Flag for translations needing review


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
        # Frappe translation CSVs are two columns (Source/Translation). Some files include a header
        # row (often: Source,Translation) and some do not. We support reading both styles.
        self._csv_has_header: Optional[bool] = None
        self._load_cache()

    def _iter_existing_rows(self) -> Iterable[Tuple[str, str]]:
        """
        Yield (source_text, translated_text) pairs from the existing CSV.

        Supports both:
        - Header CSV: source_text, translated_text
        - Headerless CSV: two columns per row (Frappe/ERPNext common format)
        """
        if not self.csv_path.exists():
            return

        # First try to sniff header by reading the first row.
        try:
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                first = next(reader, None)
                if not first:
                    self._csv_has_header = False
                    return

                lowered = [c.strip().lower() for c in first]
                # Common header variants
                header_like = (
                    ("source_text" in lowered and "translated_text" in lowered)
                    or ("source" in lowered and "translation" in lowered)
                    or ("source" in lowered and "translated" in lowered)
                )

                # If it looks like a header row, switch to DictReader (rewind the file).
                if header_like:
                    self._csv_has_header = True
        except Exception:
            # If we can't read it, let callers treat as empty.
            return

        # Header CSV
        if self._csv_has_header:
            try:
                with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                    dr = csv.DictReader(f)
                    for row in dr:
                        if not row:
                            continue
                        # Accept a few common fieldname variants
                        src = (row.get("source_text") or row.get("source") or "").strip()
                        tr = (row.get("translated_text") or row.get("translated") or row.get("translation") or "").strip()
                        if src:
                            yield (src, tr)
                return
            except Exception:
                # Fall through to headerless parsing
                self._csv_has_header = False

        # Headerless CSV (default)
        self._csv_has_header = False
        try:
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    # Expect at least 2 columns; ignore extras
                    if len(row) < 2:
                        continue
                    src = (row[0] or "").strip()
                    tr = (row[1] or "").strip()
                    if src:
                        yield (src, tr)
        except Exception:
            return

    def _load_cache(self):
        """Load existing translations from CSV."""
        if not self.csv_path.exists():
            self._csv_has_header = False
            return

        # We intentionally do not normalize or rewrite keys here. Frappe looks up translations by the
        # exact source_text, so preserving existing rows exactly is critical.
        try:
            for source_text, translated_text in self._iter_existing_rows():
                context = TranslationContext(layer="A")
                key = self._make_key(source_text, "")
                self._cache[key] = TranslationEntry(
                    source_text=source_text,
                    translated_text=translated_text,
                    context=context,
                )
        except Exception:
            # Start fresh if CSV is corrupted/unreadable
            self._cache = {}
            if self._csv_has_header is None:
                self._csv_has_header = False

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
    
    def get_entry_by_source(self, source_text: str) -> Optional[TranslationEntry]:
        """
        Get translation entry by source text.
        
        Args:
            source_text: Source text
            
        Returns:
            TranslationEntry or None
        """
        key = self._make_key(source_text, "")
        return self._cache.get(key)

    def set(
        self,
        source_text: str,
        translated_text: str,
        context: TranslationContext,
        source_file: Optional[str] = None,
        line_number: int = 0,
        update_existing: bool = False,
    ):
        """
        Store translation.

        Args:
            source_text: Source text
            translated_text: Translated text
            context: Translation context
            source_file: Source file path
            line_number: Line number
            update_existing: If False, do not overwrite an existing translation for the same key.
        """
        # Frappe standard: use source_text as unique key
        # This allows overwriting existing translations and merging with Frappe files
        key = self._make_key(source_text, "")
        if not update_existing and key in self._cache:
            return
        entry = TranslationEntry(
            source_text=source_text,
            translated_text=translated_text,
            context=context,
            source_file=source_file,
            line_number=line_number,
        )
        self._cache[key] = entry

    def save(self):
        """Save all translations to CSV without deleting existing entries.

        Frappe translation CSV is a two-column dictionary: Source -> Translation.
        We write the header row as: Source,Translation (Frappe docs style).
        """

        # Sort by source_text for consistent output
        entries = sorted(self._cache.values(), key=lambda e: (e.source_text or "").lower())

        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Source", "Translation"])
            for e in entries:
                writer.writerow([e.source_text, e.translated_text])

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

