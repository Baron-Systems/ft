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

    def test_headerless_csv_is_loaded_and_preserved(self):
        """Headerless CSVs should be readable; on save we normalize to include the header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            translations_dir = base / "translations"
            translations_dir.mkdir(parents=True, exist_ok=True)
            csv_path = translations_dir / "ar.csv"

            # Create a headerless CSV (2 columns per row)
            csv_path.write_text("Hello,مرحبا\nWorld,عالم\n", encoding="utf-8")

            storage = TranslationStorage(storage_path=base, lang="ar")
            assert storage.get("Hello") == "مرحبا"
            assert storage.get("World") == "عالم"

            # Add a new translation; save must keep the existing 2 rows.
            context = TranslationContext(layer="A", app="test")
            storage.set("New", "جديد", context, update_existing=False)
            storage.save()

            # Re-load and verify all entries exist.
            storage2 = TranslationStorage(storage_path=base, lang="ar")
            assert storage2.get("Hello") == "مرحبا"
            assert storage2.get("World") == "عالم"
            assert storage2.get("New") == "جديد"

            # Ensure header is present in normalized output.
            content = csv_path.read_text(encoding="utf-8").splitlines()
            assert content
            assert content[0].strip() == "Source,Translation"

    def test_header_csv_is_loaded_but_saved_headerless(self):
        """If a header CSV exists, we can read it, and we keep the header in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            translations_dir = base / "translations"
            translations_dir.mkdir(parents=True, exist_ok=True)
            csv_path = translations_dir / "ar.csv"

            csv_path.write_text("source_text,translated_text\nHello,مرحبا\n", encoding="utf-8")

            storage = TranslationStorage(storage_path=base, lang="ar")
            assert storage.get("Hello") == "مرحبا"

            context = TranslationContext(layer="A", app="test")
            storage.set("World", "عالم", context, update_existing=False)
            storage.save()

            # After save, file should have Frappe header.
            lines = csv_path.read_text(encoding="utf-8").splitlines()
            assert lines
            assert lines[0].strip() == "Source,Translation"

