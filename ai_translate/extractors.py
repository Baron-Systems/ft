"""Code and JSON extraction for Layer A."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from ai_translate.policy import TranslationContext


@dataclass
class ExtractedString:
    """Extracted translatable string with context."""

    text: str
    context: TranslationContext
    source_file: str
    line_number: int
    original_line: str


class CodeExtractor:
    """Extract translatable strings from code files."""

    # Python translation functions
    PYTHON_PATTERNS = [
        re.compile(r'__\s*\(\s*["\']([^"\']+)["\']\s*\)'),
        re.compile(r'_\s*\(\s*["\']([^"\']+)["\']\s*\)'),
        re.compile(r'_lt\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    ]

    # JavaScript translation functions
    JS_PATTERNS = [
        re.compile(r'frappe\._\s*\(\s*["\']([^"\']+)["\']\s*\)'),
        re.compile(r'__\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    ]

    # Jinja/HTML patterns
    JINJA_PATTERNS = [
        re.compile(r'\{\{\s*_\s*\(["\']([^"\']+)["\']\s*\)\s*\}\}'),
    ]

    # Vue template patterns
    VUE_PATTERNS = [
        re.compile(r'\{\{\s*\$t\(["\']([^"\']+)["\']\s*\)\s*\}\}'),
    ]

    def __init__(self, app_name: str):
        """
        Initialize extractor.

        Args:
            app_name: App name
        """
        self.app_name = app_name

    def extract_from_file(
        self, file_path: Path, layer: str = "A"
    ) -> Iterator[ExtractedString]:
        """
        Extract translatable strings from a file.

        Args:
            file_path: Path to file
            layer: Layer identifier

        Yields:
            ExtractedString instances
        """
        if not file_path.exists():
            return

        suffix = file_path.suffix.lower()
        patterns = []

        if suffix == ".py":
            patterns = self.PYTHON_PATTERNS
        elif suffix in (".js", ".jsx"):
            patterns = self.JS_PATTERNS
        elif suffix in (".html", ".jinja", ".jinja2"):
            patterns = self.JINJA_PATTERNS
        elif suffix == ".vue":
            patterns = self.VUE_PATTERNS
        else:
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in patterns:
                    for match in pattern.finditer(line):
                        text = match.group(1)
                        context = TranslationContext(
                            layer=layer,
                            app=self.app_name,
                            ui_surface=self._detect_ui_surface(file_path),
                            data_nature="label",
                            intent="user-facing",
                        )
                        yield ExtractedString(
                            text=text,
                            context=context,
                            source_file=str(file_path.relative_to(file_path.parents[2])),
                            line_number=line_num,
                            original_line=line.strip(),
                        )
        except Exception:
            pass  # Skip files that can't be read

    def _detect_ui_surface(self, file_path: Path) -> Optional[str]:
        """Detect UI surface from file path."""
        path_str = str(file_path).lower()
        if "form" in path_str:
            return "form"
        elif "list" in path_str:
            return "list"
        elif "report" in path_str:
            return "report"
        elif "dashboard" in path_str:
            return "dashboard"
        return None


class JSONExtractor:
    """Extract translatable strings from JSON fixtures."""

    # JSON fixture types
    FIXTURE_TYPES = [
        "DocType",
        "Workspace",
        "Report",
        "Dashboard",
        "Dashboard Chart",
        "Number Card",
    ]

    # Fields to extract from each type
    FIELD_MAP = {
        "DocType": ["label", "description", "title"],
        "Workspace": ["label", "title"],
        "Report": ["report_name", "label"],
        "Dashboard": ["dashboard_name", "label"],
        "Dashboard Chart": ["chart_name", "label"],
        "Number Card": ["label"],
    }

    def __init__(self, app_name: str):
        """
        Initialize JSON extractor.

        Args:
            app_name: App name
        """
        self.app_name = app_name

    def extract_from_file(
        self, file_path: Path, layer: str = "A"
    ) -> Iterator[ExtractedString]:
        """
        Extract translatable strings from JSON file.

        Args:
            file_path: Path to JSON file
            layer: Layer identifier

        Yields:
            ExtractedString instances
        """
        if not file_path.exists():
            return

        try:
            content = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return

        # Handle both single objects and arrays
        items = content if isinstance(content, list) else [content]

        for item in items:
            doctype = item.get("doctype") or item.get("type")
            if not doctype:
                continue

            # Extract from mapped fields
            fields_to_extract = self.FIELD_MAP.get(doctype, ["label", "name"])
            for field in fields_to_extract:
                value = item.get(field)
                if isinstance(value, str) and value.strip():
                    context = TranslationContext(
                        layer=layer,
                        app=self.app_name,
                        doctype=doctype,
                        fieldname=field,
                        data_nature="label" if field in ("label", "title") else "metadata",
                        intent="user-facing",
                    )
                    yield ExtractedString(
                        text=value,
                        context=context,
                        source_file=str(file_path.relative_to(file_path.parents[2])),
                        line_number=0,
                        original_line="",
                    )

    def find_fixture_files(self, app_path: Path) -> Iterator[Path]:
        """
        Find JSON fixture files in app.

        Args:
            app_path: App root path

        Yields:
            Paths to fixture files
        """
        fixtures_path = app_path / "fixtures"
        if not fixtures_path.exists():
            return

        for json_file in fixtures_path.rglob("*.json"):
            yield json_file


class LayerAExtractor:
    """Main extractor for Layer A (Code & Files)."""

    def __init__(self, app_name: str, app_path: Path):
        """
        Initialize Layer A extractor.

        Args:
            app_name: App name
            app_path: App root path
        """
        self.app_name = app_name
        self.app_path = app_path
        self.code_extractor = CodeExtractor(app_name)
        self.json_extractor = JSONExtractor(app_name)

    def extract_all(self) -> Iterator[ExtractedString]:
        """Extract all translatable strings from Layer A."""
        # Extract from code files
        code_dirs = ["**/*.py", "**/*.js", "**/*.jsx", "**/*.html", "**/*.vue"]
        for pattern in code_dirs:
            for file_path in self.app_path.rglob(pattern):
                # Skip node_modules, __pycache__, etc.
                if any(
                    part in str(file_path)
                    for part in ["node_modules", "__pycache__", ".git", "dist", "build"]
                ):
                    continue
                yield from self.code_extractor.extract_from_file(file_path)

        # Extract from JSON fixtures
        for fixture_file in self.json_extractor.find_fixture_files(self.app_path):
            yield from self.json_extractor.extract_from_file(fixture_file)

