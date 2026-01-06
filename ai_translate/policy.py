"""Policy Engine - Context-aware decision making for translation."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set


class Decision(Enum):
    """Translation decision types."""

    TRANSLATE = "translate"
    SKIP = "skip"
    KEEP_ORIGINAL = "keep_original"


@dataclass
class TranslationContext:
    """Context information for translation decisions."""

    layer: str  # A, B, or C
    app: Optional[str] = None
    doctype: Optional[str] = None
    fieldname: Optional[str] = None
    ui_surface: Optional[str] = None  # form, list, report, etc.
    data_nature: Optional[str] = None  # label, description, content, etc.
    intent: Optional[str] = None  # user-facing, technical, etc.

    def __post_init__(self):
        """Normalize layer to uppercase."""
        self.layer = self.layer.upper()


class PolicyEngine:
    """Context-aware policy engine for translation decisions."""

    # SQL keywords that should never be translated
    SQL_KEYWORDS: Set[str] = {
        "select", "from", "where", "join", "inner", "outer", "left", "right",
        "group", "by", "order", "having", "union", "insert", "update", "delete",
        "create", "alter", "drop", "table", "index", "view", "procedure",
        "function", "trigger", "grant", "revoke", "commit", "rollback",
        "transaction", "database", "schema", "constraint", "primary", "key",
        "foreign", "references", "default", "null", "not", "and", "or", "as",
        "distinct", "limit", "offset", "case", "when", "then", "else", "end",
        "like", "in", "exists", "between", "is", "all", "any", "some",
    }

    # Code-like patterns
    CODE_PATTERNS = [
        re.compile(r'^[a-z_][a-z0-9_]*$', re.IGNORECASE),  # identifiers
        re.compile(r'^[A-Z_][A-Z0-9_]*$'),  # constants
        re.compile(r'^[a-z]+://'),  # URLs
        re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),  # emails
        re.compile(r'^\d+$'),  # numbers only
        re.compile(r'^[\w\-]+\.(py|js|json|html|css|scss|yml|yaml)$'),  # file paths
    ]

    # Placeholder patterns
    PLACEHOLDER_PATTERNS = [
        re.compile(r'\{[0-9]+\}'),  # {0}, {1}
        re.compile(r'%\([a-zA-Z_][a-zA-Z0-9_]*\)s'),  # %(name)s
        re.compile(r'\{\{[^}]+\}\}'),  # {{ var }}
        re.compile(r'%[sd]'),  # %s, %d
    ]

    def __init__(self):
        """Initialize policy engine."""
        self.stats = {
            Decision.TRANSLATE: 0,
            Decision.SKIP: 0,
            Decision.KEEP_ORIGINAL: 0,
        }

    def decide(self, text: str, context: TranslationContext) -> Decision:
        """
        Make translation decision based on text and context.

        Args:
            text: Text to evaluate
            context: Translation context

        Returns:
            Decision enum value
        """
        # Normalize text
        text = text.strip()

        # Empty or whitespace-only
        if not text:
            decision = Decision.SKIP
        # Numbers only
        elif re.match(r'^\d+$', text):
            decision = Decision.SKIP
        # ALL_CAPS constants
        elif re.match(r'^[A-Z_][A-Z0-9_]*$', text) and len(text) > 1:
            decision = Decision.SKIP
        # URLs
        elif re.match(r'^[a-z]+://', text, re.IGNORECASE):
            decision = Decision.KEEP_ORIGINAL
        # Emails
        elif re.match(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text
        ):
            decision = Decision.KEEP_ORIGINAL
        # SQL keywords (exact match)
        elif text.lower() in self.SQL_KEYWORDS:
            decision = Decision.KEEP_ORIGINAL
        # Code-like identifiers (single word, underscore/camelCase)
        elif self._is_code_like(text):
            decision = Decision.KEEP_ORIGINAL
        # Field names that are identifiers
        elif context.fieldname and self._is_identifier(context.fieldname):
            decision = Decision.KEEP_ORIGINAL
        # Layer-specific rules
        elif context.layer == "A":
            decision = self._decide_layer_a(text, context)
        elif context.layer == "B":
            decision = self._decide_layer_b(text, context)
        elif context.layer == "C":
            decision = self._decide_layer_c(text, context)
        # Default: translate if uncertain but looks translatable
        elif self._looks_translatable(text):
            decision = Decision.TRANSLATE
        else:
            # Fail-safe: keep original if uncertain
            decision = Decision.KEEP_ORIGINAL

        self.stats[decision] += 1
        return decision

    def _is_code_like(self, text: str) -> bool:
        """Check if text looks like code."""
        # Single word identifiers
        if re.match(r'^[a-z_][a-z0-9_]*$', text) and len(text) < 50:
            return True
        # File paths
        if re.match(r'^[\w\-./]+\.(py|js|json|html|css|scss|yml|yaml)$', text):
            return True
        return False

    def _is_identifier(self, text: str) -> bool:
        """Check if text is an identifier."""
        return bool(re.match(r'^[a-z_][a-z0-9_]*$', text, re.IGNORECASE))

    def _looks_translatable(self, text: str) -> bool:
        """Check if text looks like translatable content."""
        # Has spaces or punctuation (likely natural language)
        if ' ' in text or any(c in text for c in '.,!?;:'):
            return True
        # Has multiple words
        if len(text.split()) > 1:
            return True
        return False

    def _decide_layer_a(self, text: str, context: TranslationContext) -> Decision:
        """Decision logic for Layer A (Code & Files)."""
        # In code, be very conservative
        if context.fieldname in ('route', 'api_key', 'name', 'fieldname'):
            return Decision.KEEP_ORIGINAL
        # DocType names, field names
        if context.doctype and context.fieldname == 'name':
            return Decision.KEEP_ORIGINAL
        # If it looks like translatable string in code
        if self._looks_translatable(text):
            return Decision.TRANSLATE
        return Decision.KEEP_ORIGINAL

    def _decide_layer_b(self, text: str, context: TranslationContext) -> Decision:
        """Decision logic for Layer B (UI Metadata)."""
        # UI labels and descriptions should be translated
        if context.data_nature in ('label', 'description', 'title'):
            if self._looks_translatable(text):
                return Decision.TRANSLATE
        # Technical identifiers
        if context.fieldname in ('name', 'route', 'link'):
            return Decision.KEEP_ORIGINAL
        return Decision.TRANSLATE if self._looks_translatable(text) else Decision.KEEP_ORIGINAL

    def _decide_layer_c(self, text: str, context: TranslationContext) -> Decision:
        """Decision logic for Layer C (User Content)."""
        # User content should generally be translated
        if context.data_nature in ('content', 'body', 'message', 'subject'):
            return Decision.TRANSLATE
        # But preserve technical fields
        if context.fieldname in ('name', 'route', 'slug', 'url'):
            return Decision.KEEP_ORIGINAL
        return Decision.TRANSLATE if self._looks_translatable(text) else Decision.KEEP_ORIGINAL

    def validate_placeholders(self, original: str, translated: str) -> bool:
        """
        Validate that placeholders are preserved in translation.

        Args:
            original: Original text
            translated: Translated text

        Returns:
            True if placeholders are preserved, False otherwise
        """
        # Extract placeholders from original
        original_placeholders = []
        for pattern in self.PLACEHOLDER_PATTERNS:
            original_placeholders.extend(pattern.findall(original))

        # Extract placeholders from translated
        translated_placeholders = []
        for pattern in self.PLACEHOLDER_PATTERNS:
            translated_placeholders.extend(pattern.findall(translated))

        # Sort for comparison
        original_placeholders.sort()
        translated_placeholders.sort()

        return original_placeholders == translated_placeholders

    def get_stats(self) -> dict:
        """Get decision statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            Decision.TRANSLATE: 0,
            Decision.SKIP: 0,
            Decision.KEEP_ORIGINAL: 0,
        }

