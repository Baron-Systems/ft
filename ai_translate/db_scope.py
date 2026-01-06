"""Database extraction for Layers B & C (whitelist-based, schema-safe)."""

import os
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
            fields=["label", "title", "description"],
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

    def __init__(self, frappe_db=None, site: Optional[str] = None):
        """
        Initialize DB extractor.

        Args:
            frappe_db: Frappe database connection (optional)
            site: Site name for Frappe initialization
        """
        self.frappe_db = frappe_db
        self.site = site
        self._frappe_initialized = False

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

