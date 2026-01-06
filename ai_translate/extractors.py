"""Code and JSON extraction for Layer A."""

import ast
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

        try:
            if suffix == ".py":
                # Try AST-based extraction first
                yield from self._extract_from_python_ast(file_path, layer)
                # Fallback to regex if AST fails
                yield from self._extract_from_python_regex(file_path, layer)
            elif suffix in (".js", ".jsx"):
                # Try AST-based extraction first (if available)
                yield from self._extract_from_js_ast(file_path, layer)
                # Fallback to regex
                yield from self._extract_from_js_regex(file_path, layer)
            elif suffix in (".html", ".jinja", ".jinja2"):
                yield from self._extract_from_jinja(file_path, layer)
            elif suffix == ".vue":
                yield from self._extract_from_vue(file_path, layer)
        except Exception:
            pass  # Skip files that can't be read
    
    def _extract_from_python_ast(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract using Python AST."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                # Look for function calls: _("text"), __("text"), _lt("text")
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ("_", "__", "_lt"):
                            if node.args and isinstance(node.args[0], (ast.Str, ast.Constant)):
                                # Handle both ast.Str (Python < 3.8) and ast.Constant (Python >= 3.8)
                                if isinstance(node.args[0], ast.Str):
                                    text = node.args[0].s
                                elif isinstance(node.args[0], ast.Constant):
                                    if isinstance(node.args[0].value, str):
                                        text = node.args[0].value
                                    else:
                                        continue
                                else:
                                    continue
                                
                                # Handle f-strings (joined strings)
                                if isinstance(node.args[0], ast.JoinedStr):
                                    # Skip f-strings for now (complex)
                                    continue
                                
                                if text and isinstance(text, str):
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
                                        line_number=node.lineno,
                                        original_line=content.splitlines()[node.lineno - 1] if node.lineno <= len(content.splitlines()) else "",
                                    )
        except (SyntaxError, ValueError):
            # AST parsing failed, will fallback to regex
            pass
    
    def _extract_from_python_regex(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract using regex (fallback)."""
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.PYTHON_PATTERNS:
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
            pass
    
    def _extract_from_js_ast(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract using JavaScript AST (placeholder - would need esprima or similar)."""
        # JavaScript AST parsing requires external library (esprima, acorn, etc.)
        # For now, this is a placeholder that falls back to regex
        # In production, you could use: import esprima
        pass
    
    def _extract_from_js_regex(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract using regex (fallback for JS)."""
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.JS_PATTERNS:
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
            pass
    
    def _extract_from_jinja(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract from Jinja templates."""
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.JINJA_PATTERNS:
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
            pass
    
    def _extract_from_vue(
        self, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract from Vue templates."""
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.VUE_PATTERNS:
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
            pass

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
            
            # Enhanced: Extract from custom fields and nested structures
            yield from self._extract_custom_fields(item, doctype, file_path, layer)
            yield from self._extract_nested_structures(item, doctype, file_path, layer)
    
    def _extract_custom_fields(
        self, item: dict, doctype: str, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract from custom fields."""
        # Look for custom_fields array
        custom_fields = item.get("custom_fields", [])
        for field in custom_fields:
            if isinstance(field, dict):
                # Extract label and description from custom fields
                for field_name in ["label", "description", "default"]:
                    value = field.get(field_name)
                    if isinstance(value, str) and value.strip():
                        context = TranslationContext(
                            layer=layer,
                            app=self.app_name,
                            doctype=doctype,
                            fieldname=f"custom_field.{field.get('fieldname', 'unknown')}.{field_name}",
                            data_nature="label" if field_name in ("label", "description") else "metadata",
                            intent="user-facing",
                        )
                        yield ExtractedString(
                            text=value,
                            context=context,
                            source_file=str(file_path.relative_to(file_path.parents[2])),
                            line_number=0,
                            original_line="",
                        )
    
    def _extract_nested_structures(
        self, item: dict, doctype: str, file_path: Path, layer: str
    ) -> Iterator[ExtractedString]:
        """Extract from nested structures (e.g., fields array in DocType)."""
        # Look for fields array in DocType
        if doctype == "DocType" and "fields" in item:
            fields = item.get("fields", [])
            for field in fields:
                if isinstance(field, dict):
                    # Extract label, description, options, etc.
                    for field_name in ["label", "description", "options"]:
                        value = field.get(field_name)
                        if isinstance(value, str) and value.strip():
                            # Skip if it looks like code or identifier
                            if self._is_code_or_identifier(value):
                                continue
                            
                            context = TranslationContext(
                                layer=layer,
                                app=self.app_name,
                                doctype=doctype,
                                fieldname=f"field.{field.get('fieldname', 'unknown')}.{field_name}",
                                data_nature="label" if field_name in ("label", "description") else "metadata",
                                intent="user-facing",
                            )
                            yield ExtractedString(
                                text=value,
                                context=context,
                                source_file=str(file_path.relative_to(file_path.parents[2])),
                                line_number=0,
                                original_line="",
                            )
    
    def _is_code_or_identifier(self, text: str) -> bool:
        """Check if text looks like code or identifier (should not be translated)."""
        if not text:
            return True
        # Check for common identifier patterns
        if re.match(r'^[a-z_][a-z0-9_]*$', text) and len(text) < 50:
            return True
        if re.match(r'^[A-Z_][A-Z0-9_]*$', text) and len(text) > 1:
            return True
        return False

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

