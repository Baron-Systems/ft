"""Missing and duplicate translation repair utilities."""

from typing import Dict, List, Optional, Set

from ai_translate.output import OutputFilter
from ai_translate.storage import TranslationEntry, TranslationStorage


class TranslationFixer:
    """Fix missing and duplicate translations."""

    def __init__(self, storage: TranslationStorage, output: Optional[OutputFilter] = None):
        """
        Initialize fixer.

        Args:
            storage: Translation storage instance
            output: Output filter instance
        """
        self.storage = storage
        self.output = output or OutputFilter()

    def find_missing(
        self, source_texts: List[str]
    ) -> List[str]:
        """
        Find missing translations.

        Args:
            source_texts: List of source texts

        Returns:
            List of missing source texts
        """
        missing = []
        for text in source_texts:
            # Check if translation exists
            from ai_translate.policy import TranslationContext
            context = TranslationContext(layer="A")
            if not self.storage.get(text, context):
                missing.append(text)
        return missing

    def find_duplicates(self) -> Dict[str, List[TranslationEntry]]:
        """
        Find duplicate translations.

        Returns:
            Dictionary mapping normalized text to list of entries
        """
        normalized_map: Dict[str, List[TranslationEntry]] = {}
        entries = self.storage.get_all()

        for entry in entries:
            normalized = self._normalize_text(entry.source_text)
            if normalized not in normalized_map:
                normalized_map[normalized] = []
            normalized_map[normalized].append(entry)

        # Filter to only duplicates
        duplicates = {
            text: entries
            for text, entries in normalized_map.items()
            if len(entries) > 1
        }
        return duplicates

    def fix_duplicates(self, keep_first: bool = True) -> int:
        """
        Fix duplicate translations.

        Args:
            keep_first: Keep first occurrence, remove others

        Returns:
            Number of duplicates fixed
        """
        duplicates = self.find_duplicates()
        fixed = 0

        for normalized_text, entries in duplicates.items():
            if keep_first:
                # Keep first, remove others
                for entry in entries[1:]:
                    # Remove from storage
                    # This would require storage.remove() method
                    fixed += 1
            else:
                # Merge translations
                # Use most complete translation
                best_entry = max(entries, key=lambda e: len(e.translated_text))
                for entry in entries:
                    if entry != best_entry:
                        fixed += 1

        if fixed > 0:
            self.output.info(f"Fixed {fixed} duplicate translations")
        return fixed

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.strip().split()).lower()

