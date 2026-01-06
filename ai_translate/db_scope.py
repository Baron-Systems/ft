"""Database extraction for Layers B & C (whitelist-based, schema-safe)."""

import os
import json
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

from ai_translate.extractors import ExtractedString
from ai_translate.policy import TranslationContext


@dataclass
class DBExtractionScope:
    """Scope for database extraction."""

    doctype: str
    fields: List[str]
    filters: Optional[Dict] = None
    layer: str = "B"


class DBExtractor:
    """Safe database extractor for Layers B & C."""

    # Layer B: UI Metadata
    LAYER_B_SCOPES = [
        DBExtractionScope(
            doctype="Workspace",
            # IMPORTANT: Workspace user-visible labels are often embedded inside `content` (JSON).
            # We parse and extract strings from it safely; we never translate the raw JSON blob.
            fields=["label", "title", "description", "content"],
            layer="B",
        ),
        DBExtractionScope(
            doctype="Report",
            fields=["report_name", "label"],
            layer="B",
        ),
        DBExtractionScope(
            doctype="Dashboard",
            fields=["dashboard_name", "label"],
            layer="B",
        ),
        DBExtractionScope(
            doctype="Dashboard Chart",
            fields=["chart_name", "label"],
            layer="B",
        ),
        DBExtractionScope(
            doctype="Number Card",
            fields=["label"],
            layer="B",
        ),
    ]

    # Layer C: User Content
    LAYER_C_SCOPES = [
        DBExtractionScope(
            doctype="Web Page",
            fields=["title", "content"],
            layer="C",
        ),
        DBExtractionScope(
            doctype="Blog Post",
            fields=["title", "content"],
            layer="C",
        ),
        DBExtractionScope(
            doctype="Email Template",
            fields=["subject", "message"],
            layer="C",
        ),
        DBExtractionScope(
            doctype="Print Format",
            fields=["label", "description"],
            layer="C",
        ),
        DBExtractionScope(
            doctype="Notification",
            fields=["subject", "message"],
            layer="C",
        ),
    ]

    def __init__(self, frappe_db=None, site: Optional[str] = None, bench_path=None):
        """
        Initialize DB extractor.

        Args:
            frappe_db: Frappe database connection (optional)
            site: Site name for Frappe initialization
        """
        self.frappe_db = frappe_db
        self.site = site
        self.bench_path = bench_path
        self._frappe_initialized = False

    def _find_site_packages_dir(self) -> Optional[str]:
        """Find bench env site-packages to import frappe when running outside bench python."""
        try:
            if not self.bench_path:
                return None
            lib = self.bench_path / "env" / "lib"
            if not lib.exists():
                return None
            for p in lib.glob("python*/site-packages"):
                if p.exists():
                    return str(p)
        except Exception:
            return None
        return None

    def _patch_sys_path_for_bench(self):
        """Add bench python paths so `import frappe` works from a global venv/pipx."""
        try:
            import sys

            if not self.bench_path:
                return
            sp = self._find_site_packages_dir()
            if sp and sp not in sys.path:
                sys.path.insert(0, sp)
            apps_dir = str(self.bench_path / "apps")
            if apps_dir not in sys.path:
                sys.path.insert(0, apps_dir)
            frappe_pkg = str(self.bench_path / "apps" / "frappe")
            if frappe_pkg not in sys.path:
                sys.path.insert(0, frappe_pkg)
        except Exception:
            pass

    def get_scopes_for_layers(self, layers: List[str]) -> List[DBExtractionScope]:
        """
        Get extraction scopes for specified layers.

        Args:
            layers: List of layer identifiers (B, C)

        Returns:
            List of extraction scopes
        """
        scopes = []
        if "B" in layers:
            scopes.extend(self.LAYER_B_SCOPES)
        if "C" in layers:
            scopes.extend(self.LAYER_C_SCOPES)
        return scopes

    def _ensure_connection(self, site: Optional[str] = None):
        """Ensure Frappe connection is initialized."""
        if self._frappe_initialized:
            return
        
        site = site or self.site
        if not site:
            return
        
        try:
            self._patch_sys_path_for_bench()
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
                
                frappe.init(site=site)
                frappe.connect(site=site)
            
            self._frappe_initialized = True
        except ImportError:
            # Frappe not available, continue without DB extraction
            pass
        except Exception:
            # Connection failed, continue without DB extraction
            pass

    def extract_messages_for_app(self, app_name: str, site: Optional[str] = None) -> Iterator[ExtractedString]:
        """
        Extract translatable UI messages for an app using frappe.translate.get_messages_for_app.
        This is the most complete way to get user-visible strings when frappe is available.
        """
        site = site or self.site
        if not site:
            return
        self._ensure_connection(site)
        try:
            import frappe
            if not frappe.db:
                return
            try:
                from frappe.translate import get_messages_for_app  # type: ignore
            except Exception:
                return

            messages = get_messages_for_app(app_name, deduplicate=True)
            for msg in messages:
                if isinstance(msg, tuple):
                    text = msg[1] if len(msg) >= 2 and msg[1] else msg[0]
                else:
                    text = msg
                if not isinstance(text, str):
                    continue
                text = text.strip()
                if not text or len(text) <= 1:
                    continue
                if text.startswith("eval:") or text.startswith("fa-") or "icon" in text.lower():
                    continue

                context = TranslationContext(
                    layer="B",
                    app=app_name,
                    ui_surface="messages",
                    data_nature="label",
                    intent="user-facing",
                )
                yield ExtractedString(
                    text=text,
                    context=context,
                    source_file=f"db:messages:{app_name}",
                    line_number=0,
                    original_line=text,
                )
        except Exception:
            return

    def extract_from_doctype(
        self, scope: DBExtractionScope, site: Optional[str] = None
    ) -> Iterator[ExtractedString]:
        """
        Extract records from a DocType.

        Args:
            scope: Extraction scope
            site: Site name (optional)

        Yields:
            ExtractedString objects with doctype, field, value, and context
        """
        site = site or self.site
        if not site:
            return
        
        # Ensure Frappe connection
        self._ensure_connection(site)
        
        try:
            import frappe
            
            if not frappe.db:
                return
            
            # Query all records of this DocType
            filters = scope.filters or {}
            records = frappe.db.get_all(
                scope.doctype,
                fields=["name"] + scope.fields,
                filters=filters,
                limit=None,  # Get all records
            )
            
            for record in records:
                record_name = record.get("name", "")
                
                # Extract each field
                for field_name in scope.fields:
                    field_value = record.get(field_name)
                    
                    # Skip empty values
                    if not field_value or not isinstance(field_value, str):
                        continue

                    # Special handling: Workspace.content is JSON with multiple embedded UI strings.
                    # Extract those strings instead of yielding the JSON blob.
                    if scope.doctype == "Workspace" and field_name == "content":
                        yield from self._extract_from_workspace_content(
                            content_json=field_value,
                            workspace_name=record_name,
                        )
                        continue
                    
                    # Skip if value looks like an identifier or code
                    if self._is_identifier_or_code(field_value):
                        continue
                    
                    # Create context
                    context = TranslationContext(
                        layer=scope.layer,
                        doctype=scope.doctype,
                        fieldname=field_name,
                        data_nature="label" if scope.layer == "B" else "content",
                        intent="user-facing",
                    )
                    
                    # Yield as ExtractedString
                    yield ExtractedString(
                        text=field_value,
                        context=context,
                        source_file=f"db:{scope.doctype}:{record_name}",
                        line_number=0,
                        original_line=f"{field_name}: {field_value}",
                    )
                    
        except ImportError:
            # Frappe not available
            pass
        except Exception:
            # Extraction failed, continue silently
            pass
    
    def _is_identifier_or_code(self, value: str) -> bool:
        """Check if value looks like an identifier or code (should not be translated)."""
        if not value:
            return True
        
        # Check for common identifier patterns
        identifier_patterns = [
            value.isupper() and len(value) > 3,  # UPPERCASE identifiers
            value.replace("_", "").replace("-", "").isalnum() and len(value) < 20 and not " " in value,  # snake_case or kebab-case
            value.startswith("_"),  # Private identifiers
            value.startswith("__"),  # Magic methods
            "/" in value and not " " in value,  # Paths/URLs without spaces
            "@" in value,  # Email addresses
            value.startswith("http"),  # URLs
        ]
        
        return any(identifier_patterns)

    def _extract_from_workspace_content(
        self,
        content_json: str,
        workspace_name: str,
    ) -> Iterator[ExtractedString]:
        """
        Extract user-visible strings embedded in Workspace.content JSON.

        Workspace.content commonly contains headers/sections/link labels that users see in Desk,
        e.g. "Reports & Masters", "Tax Masters", etc.
        """
        s = (content_json or "").strip()
        if not s:
            return

        try:
            data = json.loads(s)
        except Exception:
            # Some installs may store non-JSON content; ignore safely.
            return

        # Keys that are most likely to be user-facing labels in workspace structures.
        candidate_keys = {
            "label",
            "title",
            "description",
            "text",
            "heading",
            "name",  # sometimes used for headers; policy will filter identifiers
        }

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        yield from walk(v)
                    elif isinstance(v, str) and k in candidate_keys:
                        yield (k, v)
            elif isinstance(obj, list):
                for it in obj:
                    yield from walk(it)

        for key, text in walk(data):
            t = (text or "").strip()
            if not t or len(t) <= 1:
                continue
            # Quick exclusions for common non-text tokens in workspace JSON
            if t.startswith("fa-") or t.startswith("eval:") or t.startswith("icon:") or t.startswith("/"):
                continue

            context = TranslationContext(
                layer="B",
                doctype="Workspace",
                fieldname="content",
                ui_surface="workspace",
                data_nature="label",
                intent="user-facing",
            )

            yield ExtractedString(
                text=t,
                context=context,
                source_file=f"db:Workspace:{workspace_name}:content:{key}",
                line_number=0,
                original_line=f"content.{key}: {t}",
            )

    def extract_all(
        self, layers: List[str], site: Optional[str] = None
    ) -> Iterator[ExtractedString]:
        """
        Extract all records for specified layers.

        Args:
            layers: List of layer identifiers
            site: Site name

        Yields:
            ExtractedString objects
        """
        site = site or self.site
        if not site:
            return
        
        scopes = self.get_scopes_for_layers(layers)
        for scope in scopes:
            yield from self.extract_from_doctype(scope, site)

