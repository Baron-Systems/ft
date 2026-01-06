"""Tests for Translation Storage."""

import tempfile
from pathlib import Path

import pytest

from ai_translate.policy import TranslationContext
from ai_translate.storage import TranslationEntry, TranslationStorage


class TestTranslationStorage:
    """Test TranslationStorage."""
    
    def test_init(self):
        """Test storage initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TranslationStorage(storage_path=Path(tmpdir), lang="ar")
            assert storage.lang == "ar"
            assert storage.csv_path.exists() or storage.csv_path.parent.exists()
    
    def test_set_and_get(self):
        """Test set and get operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TranslationStorage(storage_path=Path(tmpdir), lang="ar")
            context = TranslationContext(layer="A", app="test")
            
            storage.set(
                "Hello",
                "مرحبا",
                context,
                "test.py",
                1,
            )
            
            translated = storage.get("Hello", context)
            assert translated == "مرحبا"
    
    def test_save_and_load(self):
        """Test save and load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TranslationStorage(storage_path=Path(tmpdir), lang="ar")
            context = TranslationContext(layer="A", app="test")
            
            storage.set("Hello", "مرحبا", context, "test.py", 1)
            storage.save()
            
            # Create new storage instance to test loading
            storage2 = TranslationStorage(storage_path=Path(tmpdir), lang="ar")
            translated = storage2.get("Hello", context)
            assert translated == "مرحبا"
    
    def test_get_all(self):
        """Test get_all operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TranslationStorage(storage_path=Path(tmpdir), lang="ar")
            context = TranslationContext(layer="A", app="test")
            
            storage.set("Hello", "مرحبا", context, "test.py", 1)
            storage.set("World", "عالم", context, "test.py", 2)
            storage.save()
            
            all_entries = storage.get_all()
            assert len(all_entries) == 2
            assert all_entries[0].source_text in ("Hello", "World")

