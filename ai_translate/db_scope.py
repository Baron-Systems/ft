"""Database extraction for Layers B & C (whitelist-based, schema-safe)."""

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

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

    def __init__(self, frappe_db=None):
        """
        Initialize DB extractor.

        Args:
            frappe_db: Frappe database connection (optional)
        """
        self.frappe_db = frappe_db

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

    def extract_from_doctype(
        self, scope: DBExtractionScope, site: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Extract records from a DocType.

        Args:
            scope: Extraction scope
            site: Site name (optional)

        Yields:
            Dictionary with doctype, name, field, value, and context
        """
        if not self.frappe_db:
            # In dry-run mode or without DB connection, return empty
            return

        try:
            # This would use frappe.db.get_all in real implementation
            # For now, return structure
            # In production, this would:
            # 1. Connect to Frappe DB
            # 2. Query doctype with filters
            # 3. Extract specified fields
            # 4. Yield structured data

            # Placeholder structure
            yield {
                "doctype": scope.doctype,
                "name": "example",
                "field": scope.fields[0],
                "value": "example value",
                "context": TranslationContext(
                    layer=scope.layer,
                    doctype=scope.doctype,
                    fieldname=scope.fields[0],
                    data_nature="label" if scope.layer == "B" else "content",
                    intent="user-facing",
                ),
            }
        except Exception:
            pass  # Fail silently in extraction

    def extract_all(
        self, layers: List[str], site: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Extract all records for specified layers.

        Args:
            layers: List of layer identifiers
            site: Site name

        Yields:
            Extracted records
        """
        scopes = self.get_scopes_for_layers(layers)
        for scope in scopes:
            yield from self.extract_from_doctype(scope, site)

