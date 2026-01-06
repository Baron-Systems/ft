"""Tests for Policy Engine."""

import pytest

from ai_translate.policy import Decision, PolicyEngine, RejectionReason, TranslationContext


class TestPolicyEngine:
    """Test PolicyEngine."""
    
    def test_empty_text(self):
        """Test empty text is skipped."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("", context)
        assert decision == Decision.SKIP
        assert reason == RejectionReason.EMPTY_TEXT
    
    def test_numbers_only(self):
        """Test numbers only are skipped."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("123", context)
        assert decision == Decision.SKIP
        assert reason == RejectionReason.TECHNICAL_TERM
    
    def test_urls(self):
        """Test URLs are kept original."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("https://example.com", context)
        assert decision == Decision.KEEP_ORIGINAL
        assert reason == RejectionReason.TECHNICAL_TERM
    
    def test_emails(self):
        """Test emails are kept original."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("user@example.com", context)
        assert decision == Decision.KEEP_ORIGINAL
        assert reason == RejectionReason.TECHNICAL_TERM
    
    def test_translatable_text(self):
        """Test translatable text is translated."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("Hello World", context)
        assert decision == Decision.TRANSLATE
        assert reason is None
    
    def test_placeholder_validation(self):
        """Test placeholder validation."""
        engine = PolicyEngine()
        # Valid: placeholders match
        assert engine.validate_placeholders("Hello {0}", "مرحبا {0}")
        # Invalid: placeholders don't match
        assert not engine.validate_placeholders("Hello {0}", "مرحبا {1}")
        # Valid: no placeholders
        assert engine.validate_placeholders("Hello", "مرحبا")
    
    def test_sql_keywords(self):
        """Test SQL keywords are kept original."""
        engine = PolicyEngine()
        context = TranslationContext(layer="A")
        decision, reason = engine.decide("SELECT", context)
        assert decision == Decision.KEEP_ORIGINAL
        assert reason == RejectionReason.LOGIC_BEARING

