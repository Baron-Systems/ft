"""Context Profile Builder - Builds language-specific context profiles from translations."""

from pathlib import Path
from typing import Dict, List, Optional

from ai_translate.language_memory import LanguageMemory, LanguageMemoryManager
from ai_translate.storage import TranslationEntry, TranslationStorage


class ContextProfileBuilder:
    """Builds context profiles for languages from existing translations."""
    
    def __init__(self, storage_path: Path):
        """
        Initialize context profile builder.
        
        Args:
            storage_path: Base path for storage (translations directory)
        """
        self.storage_path = Path(storage_path)
        self.memory_manager = LanguageMemoryManager(storage_path)
    
    def build_profile(self, lang: str, app_name: Optional[str] = None) -> LanguageMemory:
        """
        Build language context profile from existing translations.
        
        Args:
            lang: Language code
            app_name: Optional app name to filter translations
            
        Returns:
            LanguageMemory instance
        """
        # Load translations from CSV
        entries = self._load_translations(lang, app_name)
        
        if not entries:
            # Return empty memory
            return self.memory_manager.get_memory(lang)
        
        # Build memory from translations
        self.memory_manager.build_memory_from_translations(
            lang=lang,
            entries=entries,
            extract_terminology=True,
            detect_style=True,
        )
        
        return self.memory_manager.get_memory(lang)
    
    def _load_translations(
        self, lang: str, app_name: Optional[str] = None
    ) -> List[TranslationEntry]:
        """Load translations from CSV files."""
        entries = []
        
        # Try to load from app translations directory
        if app_name:
            app_translations_path = self.storage_path / app_name / "translations"
            if app_translations_path.exists():
                storage = TranslationStorage(storage_path=app_translations_path, lang=lang)
                entries.extend(storage.get_all())
        else:
            # Try to load from site translations directory
            site_translations_path = self.storage_path / "translations"
            if site_translations_path.exists():
                storage = TranslationStorage(storage_path=site_translations_path, lang=lang)
                entries.extend(storage.get_all())
        
        return entries
    
    def extract_terminology(self, entries: List[TranslationEntry]) -> Dict[str, str]:
        """
        Extract terminology from translation entries.
        
        Args:
            entries: List of translation entries
            
        Returns:
            Dictionary mapping source terms to translated terms
        """
        terminology = {}
        
        # Use memory manager's terminology extraction
        lang = entries[0].context.app if entries and entries[0].context.app else "en"
        memory = self.memory_manager.get_memory(lang)
        
        # Build memory to extract terminology
        self.memory_manager.build_memory_from_translations(
            lang=lang,
            entries=entries,
            extract_terminology=True,
            detect_style=False,
        )
        
        return memory.terminology
    
    def detect_style(self, entries: List[TranslationEntry]) -> Dict[str, str]:
        """
        Detect style from translation entries.
        
        Args:
            entries: List of translation entries
            
        Returns:
            Dictionary mapping context types to styles
        """
        lang = entries[0].context.app if entries and entries[0].context.app else "en"
        memory = self.memory_manager.get_memory(lang)
        
        # Build memory to detect style
        self.memory_manager.build_memory_from_translations(
            lang=lang,
            entries=entries,
            extract_terminology=False,
            detect_style=True,
        )
        
        return memory.style_profile
    
    def get_examples(
        self, lang: str, context_type: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get example translations for a context type.
        
        Args:
            lang: Language code
            context_type: Optional context type filter
            
        Returns:
            List of example dictionaries with 'source' and 'translated'
        """
        memory = self.memory_manager.get_memory(lang)
        examples = memory.get_examples(context_type)
        
        return [
            {
                "source": ex.source,
                "translated": ex.translated,
                "context": ex.context,
            }
            for ex in examples
        ]

