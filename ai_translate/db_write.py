"""Non-destructive database write to Translation DocType."""

from typing import Dict, Optional

from ai_translate.output import OutputFilter
from ai_translate.storage import TranslationEntry


class TranslationDBWriter:
    """Non-destructive writer to Translation DocType."""

    def __init__(
        self,
        site: str,
        update_existing: bool = False,
        output: Optional[OutputFilter] = None,
    ):
        """
        Initialize DB writer.

        Args:
            site: Site name
            update_existing: Update existing translations
            output: Output filter instance
        """
        self.site = site
        self.update_existing = update_existing
        self.output = output or OutputFilter()
        self.stats = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }

    def write_entry(
        self, entry: TranslationEntry, dry_run: bool = False
    ) -> bool:
        """
        Write translation entry to database.

        Args:
            entry: Translation entry
            dry_run: Dry run mode (no actual writes)

        Returns:
            True if successful
        """
        if dry_run:
            self.output.debug(
                f"Would write: {entry.source_text} -> {entry.translated_text}"
            )
            return True

        try:
            # In production, this would:
            # 1. Connect to Frappe DB for the site
            # 2. Check if Translation record exists
            # 3. Insert if missing
            # 4. Update if empty or update_existing=True
            # 5. Never modify original records

            # Placeholder implementation
            # frappe.connect(site=self.site)
            # translation = frappe.get_doc({
            #     "doctype": "Translation",
            #     "source_text": entry.source_text,
            #     "translated_text": entry.translated_text,
            #     "language": self.lang,
            #     "context": self._context_to_string(entry.context),
            # })
            # translation.insert(ignore_if_duplicate=True)

            self.stats["inserted"] += 1
            return True

        except Exception as e:
            self.output.error(f"Failed to write translation: {e}")
            self.stats["skipped"] += 1
            return False

    def write_batch(
        self, entries: list[TranslationEntry], dry_run: bool = False
    ) -> int:
        """
        Write batch of translations.

        Args:
            entries: List of translation entries
            dry_run: Dry run mode

        Returns:
            Number of successful writes
        """
        success_count = 0
        for entry in entries:
            if self.write_entry(entry, dry_run):
                success_count += 1
        return success_count

    def _context_to_string(self, context) -> str:
        """Convert context to string."""
        parts = [
            context.layer,
            context.app or "",
            context.doctype or "",
            context.fieldname or "",
        ]
        return "|".join(parts)

    def get_stats(self) -> dict:
        """Get write statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }

