"""Policy Engine - Context-aware decision making for translation."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set, Tuple


class Decision(Enum):
    """Translation decision types."""

    TRANSLATE = "translate"
    SKIP = "skip"
    KEEP_ORIGINAL = "keep_original"


class RejectionReason(Enum):
    """Rejection reasons for translation decisions."""

    CONTAINS_IDENTIFIER = "contains_identifier"
    LOGIC_BEARING = "logic_bearing"
    AMBIGUOUS_CONTEXT = "ambiguous_context"
    TRANSACTIONAL_DATA = "transactional_data"
    UNSAFE_STRUCTURE = "unsafe_structure"
    EMPTY_TEXT = "empty_text"
    CODE_LIKE = "code_like"
    TECHNICAL_TERM = "technical_term"


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
    _SINGLE_BRACE_FIELD = re.compile(r'(?<!\{)\{[^{}]*\}(?!\})')  # {..} but not {{..}}
    _SINGLE_OPEN_BRACE = re.compile(r'(?<!\{)\{(?!\{)')
    _SINGLE_CLOSE_BRACE = re.compile(r'(?<!\})\}(?!\})')

    # Enhanced blacklist patterns
    BLACKLIST_PATTERNS = [
        # DocType names (all contexts)
        re.compile(r'^[A-Z][a-zA-Z0-9]*$'),  # PascalCase
        # Fieldnames (all contexts)
        re.compile(r'^[a-z_][a-z0-9_]*$'),  # snake_case
        # Routes/slugs
        re.compile(r'^[\w\-]+$'),  # alphanumeric with hyphens
        # Status values
        re.compile(r'^(draft|submitted|approved|rejected|cancelled)$', re.IGNORECASE),
        # Role IDs
        re.compile(r'^[A-Z_]+$'),  # ALL_CAPS
        # API names
        re.compile(r'^[a-z_]+\.(get|set|create|update|delete)$'),
        # Permission identifiers
        re.compile(r'^[A-Z][a-zA-Z0-9]*\.[A-Z][a-zA-Z0-9]*$'),  # DocType.Field
    ]

    def __init__(self):
        """Initialize policy engine."""
        self.stats = {
            Decision.TRANSLATE: 0,
            Decision.SKIP: 0,
            Decision.KEEP_ORIGINAL: 0,
        }
        self.rejection_reasons = {
            reason: 0 for reason in RejectionReason
        }

    def decide(
        self, text: str, context: TranslationContext
    ) -> Tuple[Decision, Optional[RejectionReason]]:
        """
        Make translation decision based on text and context.

        Args:
            text: Text to evaluate
            context: Translation context

        Returns:
            Tuple of (Decision, Optional[RejectionReason])
        """
        # Normalize text
        text = text.strip()

        # Empty or whitespace-only
        if not text:
            decision = Decision.SKIP
            reason = RejectionReason.EMPTY_TEXT
        # Numbers only
        elif re.match(r'^\d+$', text):
            decision = Decision.SKIP
            reason = RejectionReason.TECHNICAL_TERM
        # ALL_CAPS constants
        elif re.match(r'^[A-Z_][A-Z0-9_]*$', text) and len(text) > 1:
            decision = Decision.SKIP
            reason = RejectionReason.CONTAINS_IDENTIFIER
        # URLs
        elif re.match(r'^[a-z]+://', text, re.IGNORECASE):
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.TECHNICAL_TERM
        # Emails
        elif re.match(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text
        ):
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.TECHNICAL_TERM
        # SQL keywords (exact match)
        elif text.lower() in self.SQL_KEYWORDS:
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.LOGIC_BEARING
        # Code-like identifiers (single word, underscore/camelCase)
        elif self._is_code_like(text):
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.CODE_LIKE
        # Blacklist patterns
        elif self._matches_blacklist(text):
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.CONTAINS_IDENTIFIER
        # Field names that are identifiers
        elif context.fieldname and self._is_identifier(context.fieldname):
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.CONTAINS_IDENTIFIER
        # Layer-specific rules
        elif context.layer == "A":
            decision, reason = self._decide_layer_a(text, context)
        elif context.layer == "B":
            decision, reason = self._decide_layer_b(text, context)
        elif context.layer == "C":
            decision, reason = self._decide_layer_c(text, context)
        # Default: translate if uncertain but looks translatable
        elif self._looks_translatable(text):
            decision = Decision.TRANSLATE
            reason = None
        else:
            # Fail-safe: keep original if uncertain
            decision = Decision.KEEP_ORIGINAL
            reason = RejectionReason.AMBIGUOUS_CONTEXT

        self.stats[decision] += 1
        if reason:
            self.rejection_reasons[reason] += 1
        return decision, reason
    
    def _matches_blacklist(self, text: str) -> bool:
        """Check if text matches blacklist patterns."""
        for pattern in self.BLACKLIST_PATTERNS:
            if pattern.match(text):
                return True
        return False

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

    def _decide_layer_a(
        self, text: str, context: TranslationContext
    ) -> Tuple[Decision, Optional[RejectionReason]]:
        """Decision logic for Layer A (Code & Files)."""
        # In code, be very conservative
        if context.fieldname in ('route', 'api_key', 'name', 'fieldname'):
            return Decision.KEEP_ORIGINAL, RejectionReason.CONTAINS_IDENTIFIER
        # DocType names, field names
        if context.doctype and context.fieldname == 'name':
            return Decision.KEEP_ORIGINAL, RejectionReason.CONTAINS_IDENTIFIER
        # If it looks like translatable string in code
        if self._looks_translatable(text):
            return Decision.TRANSLATE, None
        return Decision.KEEP_ORIGINAL, RejectionReason.CODE_LIKE

    def _decide_layer_b(
        self, text: str, context: TranslationContext
    ) -> Tuple[Decision, Optional[RejectionReason]]:
        """Decision logic for Layer B (UI Metadata)."""
        # UI labels and descriptions should be translated
        if context.data_nature in ('label', 'description', 'title'):
            if self._looks_translatable(text):
                return Decision.TRANSLATE, None
        # Technical identifiers
        if context.fieldname in ('name', 'route', 'link'):
            return Decision.KEEP_ORIGINAL, RejectionReason.CONTAINS_IDENTIFIER
        if self._looks_translatable(text):
            return Decision.TRANSLATE, None
        return Decision.KEEP_ORIGINAL, RejectionReason.AMBIGUOUS_CONTEXT

    def _decide_layer_c(
        self, text: str, context: TranslationContext
    ) -> Tuple[Decision, Optional[RejectionReason]]:
        """Decision logic for Layer C (User Content)."""
        # User content should generally be translated
        if context.data_nature in ('content', 'body', 'message', 'subject'):
            return Decision.TRANSLATE, None
        # But preserve technical fields
        if context.fieldname in ('name', 'route', 'slug', 'url'):
            return Decision.KEEP_ORIGINAL, RejectionReason.CONTAINS_IDENTIFIER
        if self._looks_translatable(text):
            return Decision.TRANSLATE, None
        return Decision.KEEP_ORIGINAL, RejectionReason.AMBIGUOUS_CONTEXT

    def validate_placeholders(self, original: str, translated: str) -> bool:
        """
        Validate that placeholders are preserved in translation.

        Args:
            original: Original text
            translated: Translated text

        Returns:
            True if placeholders are preserved, False otherwise
        """
        # Fast fail on unbalanced single braces (common corruption: introducing "{ }")
        orig_open = len(self._SINGLE_OPEN_BRACE.findall(original))
        orig_close = len(self._SINGLE_CLOSE_BRACE.findall(original))
        trans_open = len(self._SINGLE_OPEN_BRACE.findall(translated))
        trans_close = len(self._SINGLE_CLOSE_BRACE.findall(translated))
        if orig_open != orig_close:
            # Original itself is odd; don't block on it
            pass
        else:
            if trans_open != trans_close:
                return False

        def _extract_tokens(text: str) -> list[str]:
            tokens: list[str] = []
            # Named/standard printf placeholders and jinja placeholders
            for pattern in self.PLACEHOLDER_PATTERNS:
                tokens.extend(pattern.findall(text))
            # Any single-brace python format fields: catches {0}, {name}, {} , { }
            tokens.extend(self._SINGLE_BRACE_FIELD.findall(text))
            tokens.sort()
            return tokens

        # Compare tokens exactly: preserves both presence and multiplicity
        return _extract_tokens(original) == _extract_tokens(translated)

    def get_stats(self) -> dict:
        """Get decision statistics."""
        stats = {}
        for decision, count in self.stats.items():
            stats[decision.value] = count
        return stats
    
    def get_rejection_stats(self) -> dict:
        """Get rejection reason statistics."""
        stats = {}
        for reason, count in self.rejection_reasons.items():
            if count > 0:
                stats[reason.value] = count
        return stats

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            Decision.TRANSLATE: 0,
            Decision.SKIP: 0,
            Decision.KEEP_ORIGINAL: 0,
        }

