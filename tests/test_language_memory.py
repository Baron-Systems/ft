"""Tests for Language Memory."""

import tempfile
from pathlib import Path

import pytest

from ai_translate.language_memory import (
    AcceptedTranslation,
    LanguageMemory,
    LanguageMemoryManager,
)
from ai_translate.policy import TranslationContext
from ai_translate.storage import TranslationEntry


class TestLanguageMemory:
    """Test LanguageMemory."""
    
    def test_init(self):
        """Test memory initialization."""
        memory = LanguageMemory(
            lang="ar",
            terminology={},
            style_profile={},
            accepted_translations=[],
        )
        assert memory.lang == "ar"
    
    def test_add_translation(self):
        """Test adding translation."""
        memory = LanguageMemory(
            lang="ar",
            terminology={},
            style_profile={},
            accepted_translations=[],
        )
        memory.add_translation("Hello", "مرحبا", "label", 0.95, "approved")
        assert len(memory.accepted_translations) == 1
        assert memory.accepted_translations[0].source == "Hello"
        assert memory.accepted_translations[0].translated == "مرحبا"
    
    def test_get_terminology(self):
        """Test getting terminology."""
        memory = LanguageMemory(
            lang="ar",
            terminology={"Customer": "عميل"},
            style_profile={},
            accepted_translations=[],
        )
        assert memory.get_terminology("Customer") == "عميل"
        assert memory.get_terminology("Invoice") is None
    
    def test_get_examples(self):
        """Test getting examples."""
        memory = LanguageMemory(
            lang="ar",
            terminology={},
            style_profile={},
            accepted_translations=[
                AcceptedTranslation("Hello", "مرحبا", "label", 0.95, "approved"),
                AcceptedTranslation("World", "عالم", "button", 0.95, "approved"),
            ],
        )
        examples = memory.get_examples("label")
        assert len(examples) == 1
        assert examples[0].source == "Hello"


class TestLanguageMemoryManager:
    """Test LanguageMemoryManager."""
    
    def test_get_memory(self):
        """Test getting memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LanguageMemoryManager(storage_path=Path(tmpdir))
            memory = manager.get_memory("ar")
            assert memory.lang == "ar"
    
    def test_save_and_load(self):
        """Test save and load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LanguageMemoryManager(storage_path=Path(tmpdir))
            memory = manager.get_memory("ar")
            memory.add_translation("Hello", "مرحبا", "label", 0.95, "approved")
            manager.save_memory("ar")
            
            # Load again
            memory2 = manager.get_memory("ar")
            assert len(memory2.accepted_translations) == 1

