"""Non-destructive database write to Translation DocType."""

import os
from typing import Dict, Optional

from ai_translate.output import OutputFilter
from ai_translate.storage import TranslationEntry


class TranslationDBWriter:
    """Non-destructive writer to Translation DocType."""

    def __init__(
        self,
        site: str,
        lang: str,
        update_existing: bool = False,
        output: Optional[OutputFilter] = None,
    ):
        """
        Initialize DB writer.

        Args:
            site: Site name
            lang: Language code
            update_existing: Update existing translations
            output: Output filter instance
        """
        self.site = site
        self.lang = lang
        self.update_existing = update_existing
        self.output = output or OutputFilter()
        self.stats = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }
        self._frappe_initialized = False

    def _ensure_connection(self):
        """Ensure Frappe connection is initialized."""
        if self._frappe_initialized:
            return
        
        try:
            import frappe
            
            # Initialize Frappe if not already initialized
            if not frappe.db:
                # Try to find bench path from environment or current directory
                bench_path = os.getenv("FRAPPE_BENCH_PATH")
                if not bench_path:
                    # Try to find from current directory
                    cwd = os.getcwd()
                    if "frappe-bench" in cwd or "sites" in cwd:
                        # Navigate to bench root
                        parts = cwd.split("frappe-bench")
                        if parts:
                            bench_path = parts[0] + "frappe-bench"
                        else:
                            parts = cwd.split("sites")
                            if parts:
                                bench_path = parts[0]
                
                if bench_path:
                    os.chdir(bench_path)
                
                frappe.init(site=self.site)
                frappe.connect(site=self.site)
            
            self._frappe_initialized = True
        except ImportError:
            # Frappe not available
            self._frappe_initialized = False
        except Exception as e:
            # Connection failed
            self.output.warning(f"Failed to connect to Frappe: {e}", verbose_only=True)
            self._frappe_initialized = False

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
                f"Would write: {entry.source_text} -> {entry.translated_text}",
                verbose_only=True
            )
            return True

        # Ensure Frappe connection
        self._ensure_connection()
        
        if not self._frappe_initialized:
            # Frappe not available, skip silently
            return False

        try:
            import frappe
            
            if not frappe.db:
                return False
            
            # Check if Translation record exists
            existing = frappe.db.get_value(
                "Translation",
                {
                    "source_text": entry.source_text,
                    "language": self.lang,
                },
                ["name", "translated_text"],
            )
            
            if existing:
                existing_name, existing_translated = existing
                
                # Only update if update_existing is True and translation is different
                if self.update_existing and existing_translated != entry.translated_text:
                    try:
                        translation_doc = frappe.get_doc("Translation", existing_name)
                        translation_doc.translated_text = entry.translated_text
                        translation_doc.save(ignore_permissions=True)
                        self.stats["updated"] += 1
                        return True
                    except Exception as e:
                        self.output.warning(f"Failed to update translation: {e}", verbose_only=True)
                        self.stats["skipped"] += 1
                        return False
                else:
                    # Skip if already exists and update_existing is False
                    self.stats["skipped"] += 1
                    return False
            else:
                # Insert new translation
                try:
                    translation_doc = frappe.get_doc({
                        "doctype": "Translation",
                        "source_text": entry.source_text,
                        "translated_text": entry.translated_text,
                        "language": self.lang,
                        "context": self._context_to_string(entry.context) if entry.context else "",
                    })
                    translation_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    self.stats["inserted"] += 1
                    return True
                except frappe.DuplicateEntryError:
                    # Already exists, skip
                    self.stats["skipped"] += 1
                    return False
                except Exception as e:
                    self.output.warning(f"Failed to insert translation: {e}", verbose_only=True)
                    self.stats["skipped"] += 1
                    return False

        except ImportError:
            # Frappe not available
            return False
        except Exception as e:
            self.output.warning(f"Failed to write translation: {e}", verbose_only=True)
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

