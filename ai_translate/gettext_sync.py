"""PO/MO sync and compilation utilities."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import polib
    POLIB_AVAILABLE = True
except ImportError:
    POLIB_AVAILABLE = False
    polib = None

from ai_translate.output import OutputFilter
from ai_translate.storage import TranslationStorage


class GettextSync:
    """Sync CSV translations to PO/MO files."""

    def __init__(
        self,
        storage: TranslationStorage,
        locale_path: Path,
        output: Optional[OutputFilter] = None,
    ):
        """
        Initialize gettext sync.

        Args:
            storage: Translation storage instance
            locale_path: Path to locale directory
            output: Output filter instance
        """
        self.storage = storage
        self.locale_path = Path(locale_path)
        self.output = output or OutputFilter()
        self.po_path = self.locale_path / f"{storage.lang}.po"
        self.mo_path = self.locale_path / f"{storage.lang}.mo"

    def sync_csv_to_po(self, dry_run: bool = False, merge: bool = True) -> bool:
        """
        Sync CSV translations to PO file using polib.

        Args:
            dry_run: Dry run mode
            merge: Merge with existing PO file if it exists

        Returns:
            True if successful
        """
        entries = self.storage.get_all()
        if not entries:
            self.output.warning("No translations to sync")
            return False

        if dry_run:
            self.output.info(f"Would sync {len(entries)} translations to PO")
            return True

        try:
            if not POLIB_AVAILABLE:
                self.output.error("polib is required for PO file generation. Install it with: pip install polib")
                return False
            
            # Load existing PO file if it exists and merge is enabled
            if merge and self.po_path.exists():
                po = polib.pofile(str(self.po_path))
            else:
                po = polib.POFile()
            
            # Set metadata
            po.metadata.update({
                "Content-Type": "text/plain; charset=UTF-8",
                "Content-Transfer-Encoding": "8bit",
                "Language": self.storage.lang,
                "Plural-Forms": "nplurals=2; plural=(n != 1);",
                "X-Generator": "ai-translate",
                "POT-Creation-Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S%z"),
                "PO-Revision-Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S%z"),
            })
            
            # Add/update entries
            entry_count = 0
            for entry in entries:
                # Check if entry already exists
                existing_entry = po.find(entry.source_text)
                
                if existing_entry:
                    # Update existing entry
                    existing_entry.msgstr = entry.translated_text
                    if entry.source_file:
                        existing_entry.occurrences = [(entry.source_file, entry.line_number)]
                else:
                    # Create new entry
                    po_entry = polib.POEntry(
                        msgid=entry.source_text,
                        msgstr=entry.translated_text,
                    )
                    if entry.source_file:
                        po_entry.occurrences = [(entry.source_file, entry.line_number)]
                    if entry.context:
                        # Add context as comment
                        context_str = f"Layer: {entry.context.layer}"
                        if entry.context.doctype:
                            context_str += f", DocType: {entry.context.doctype}"
                        if entry.context.fieldname:
                            context_str += f", Field: {entry.context.fieldname}"
                        po_entry.comment = context_str
                    po.append(po_entry)
                    entry_count += 1
            
            # Save PO file
            self.po_path.parent.mkdir(parents=True, exist_ok=True)
            po.save(str(self.po_path))

            self.output.success(f"Synced {len(entries)} translations to {self.po_path}")
            return True

        except Exception as e:
            self.output.error(f"Failed to sync PO: {e}")
            return False

    def compile_mo(self, dry_run: bool = False) -> bool:
        """
        Compile MO file from PO.

        Args:
            dry_run: Dry run mode

        Returns:
            True if successful
        """
        if not self.po_path.exists():
            self.output.warning("PO file not found, skipping MO compilation")
            return False

        if dry_run:
            self.output.info(f"Would compile MO from {self.po_path}")
            return True

        try:
            # Use msgfmt to compile MO
            result = subprocess.run(
                ["msgfmt", "-o", str(self.mo_path), str(self.po_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                self.output.error(f"msgfmt failed: {result.stderr}")
                return False

            self.output.success(f"Compiled MO: {self.mo_path}")
            return True

        except FileNotFoundError:
            self.output.warning(
                "msgfmt not found. Install gettext tools to compile MO files."
            )
            return False
        except Exception as e:
            self.output.error(f"Failed to compile MO: {e}")
            return False


