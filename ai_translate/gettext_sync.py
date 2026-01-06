"""PO/MO sync and compilation utilities."""

import subprocess
from pathlib import Path
from typing import Optional

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

    def sync_csv_to_po(self, dry_run: bool = False) -> bool:
        """
        Sync CSV translations to PO file.

        Args:
            dry_run: Dry run mode

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
            # Create PO file content
            po_content = self._generate_po_content(entries)

            # Write PO file
            self.po_path.parent.mkdir(parents=True, exist_ok=True)
            self.po_path.write_text(po_content, encoding="utf-8")

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

    def _generate_po_content(self, entries) -> str:
        """Generate PO file content from entries."""
        lines = [
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            "",
        ]

        for entry in entries:
            # Escape quotes and newlines
            source = self._escape_po_string(entry.source_text)
            translated = self._escape_po_string(entry.translated_text)

            lines.append(f'msgid "{source}"')
            lines.append(f'msgstr "{translated}"')
            lines.append("")

        return "\n".join(lines)

    def _escape_po_string(self, text: str) -> str:
        """Escape string for PO format."""
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )

