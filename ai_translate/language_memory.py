"""Language Memory System - Terminology, Style, and Translation Memory per Language."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from ai_translate.storage import TranslationEntry


@dataclass
class AcceptedTranslation:
    """Accepted translation with context and confidence."""
    
    source: str
    translated: str
    context: str  # e.g., "button", "label", "title", "paragraph"
    confidence: float = 0.95
    review_status: str = "approved"  # "approved", "needs_review", "rejected"


@dataclass
class LanguageMemory:
    """Language memory for a specific language."""
    
    lang: str
    terminology: Dict[str, str]  # source -> translated term
    style_profile: Dict[str, str]  # context_type -> style (formal/informal/neutral)
    accepted_translations: List[AcceptedTranslation]
    
    def get_terminology(self, source: str) -> Optional[str]:
        """Get terminology translation if exists."""
        return self.terminology.get(source)
    
    def get_style(self, context_type: str) -> str:
        """Get style for context type."""
        return self.style_profile.get(context_type, "neutral")
    
    def get_examples(self, context_type: Optional[str] = None) -> List[AcceptedTranslation]:
        """Get example translations, optionally filtered by context type."""
        if context_type:
            return [t for t in self.accepted_translations if t.context == context_type]
        return self.accepted_translations
    
    def add_translation(
        self,
        source: str,
        translated: str,
        context: str,
        confidence: float = 0.95,
        review_status: str = "approved",
    ):
        """Add or update accepted translation."""
        # Remove existing if present
        self.accepted_translations = [
            t for t in self.accepted_translations if t.source != source
        ]
        # Add new
        self.accepted_translations.append(
            AcceptedTranslation(
                source=source,
                translated=translated,
                context=context,
                confidence=confidence,
                review_status=review_status,
            )
        )
    
    def add_terminology(self, source: str, translated: str):
        """Add terminology entry."""
        self.terminology[source] = translated
    
    def set_style(self, context_type: str, style: str):
        """Set style for context type."""
        self.style_profile[context_type] = style


class LanguageMemoryManager:
    """Manager for language memory files."""
    
    def __init__(self, storage_path: Path):
        """
        Initialize language memory manager.
        
        Args:
            storage_path: Base path for storage (translations directory)
        """
        self.storage_path = Path(storage_path)
        self._memories: Dict[str, LanguageMemory] = {}
    
    def get_memory(self, lang: str) -> LanguageMemory:
        """
        Get or create language memory.
        
        Args:
            lang: Language code
            
        Returns:
            LanguageMemory instance
        """
        if lang not in self._memories:
            memory_path = self.storage_path / f"{lang}_memory.json"
            if memory_path.exists():
                self._memories[lang] = self._load_memory(lang, memory_path)
            else:
                self._memories[lang] = LanguageMemory(
                    lang=lang,
                    terminology={},
                    style_profile={},
                    accepted_translations=[],
                )
        
        return self._memories[lang]
    
    def save_memory(self, lang: str):
        """Save language memory to disk."""
        if lang not in self._memories:
            return
        
        memory = self._memories[lang]
        memory_path = self.storage_path / f"{lang}_memory.json"
        
        # Convert to dict
        data = {
            "lang": memory.lang,
            "terminology": memory.terminology,
            "style_profile": memory.style_profile,
            "accepted_translations": [
                asdict(t) for t in memory.accepted_translations
            ],
        }
        
        # Save to JSON
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_memory(self, lang: str, memory_path: Path) -> LanguageMemory:
        """Load language memory from disk."""
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert accepted_translations back to AcceptedTranslation objects
        accepted_translations = [
            AcceptedTranslation(**t) for t in data.get("accepted_translations", [])
        ]
        
        return LanguageMemory(
            lang=data.get("lang", lang),
            terminology=data.get("terminology", {}),
            style_profile=data.get("style_profile", {}),
            accepted_translations=accepted_translations,
        )
    
    def build_memory_from_translations(
        self,
        lang: str,
        entries: List[TranslationEntry],
        extract_terminology: bool = True,
        detect_style: bool = True,
    ):
        """
        Build language memory from translation entries.
        
        Args:
            lang: Language code
            entries: List of translation entries
            extract_terminology: Extract terminology from entries
            detect_style: Detect style from entries
        """
        memory = self.get_memory(lang)
        
        # Extract terminology
        if extract_terminology:
            terminology = self._extract_terminology(entries)
            for source, translated in terminology.items():
                memory.add_terminology(source, translated)
        
        # Detect style
        if detect_style:
            style_profile = self._detect_style(entries)
            for context_type, style in style_profile.items():
                memory.set_style(context_type, style)
        
        # Add accepted translations
        for entry in entries:
            context_type = self._get_context_type(entry)
            memory.add_translation(
                source=entry.source_text,
                translated=entry.translated_text,
                context=context_type,
                confidence=0.95,  # Default confidence
                review_status="approved",
            )
        
        self.save_memory(lang)
    
    def _extract_terminology(self, entries: List[TranslationEntry]) -> Dict[str, str]:
        """
        Extract terminology from translation entries.
        
        Looks for:
        - Capitalized words (likely proper nouns or terms)
        - Repeated patterns
        - Technical terms
        """
        terminology = {}
        
        # Count occurrences of capitalized words
        term_counts: Dict[str, int] = {}
        for entry in entries:
            words = entry.source_text.split()
            for word in words:
                # Check if word looks like a term (capitalized, not at start of sentence)
                if word and word[0].isupper() and len(word) > 2:
                    # Remove punctuation
                    clean_word = word.strip(".,!?;:")
                    if clean_word:
                        term_counts[clean_word] = term_counts.get(clean_word, 0) + 1
        
        # Find terms that appear multiple times (likely terminology)
        for entry in entries:
            words = entry.source_text.split()
            translated_words = entry.translated_text.split()
            
            for i, word in enumerate(words):
                clean_word = word.strip(".,!?;:")
                if clean_word in term_counts and term_counts[clean_word] >= 2:
                    # This is likely a term
                    if i < len(translated_words):
                        translated_word = translated_words[i].strip(".,!?;:")
                        if clean_word not in terminology:
                            terminology[clean_word] = translated_word
        
        return terminology
    
    def _detect_style(self, entries: List[TranslationEntry]) -> Dict[str, str]:
        """
        Detect style from translation entries.
        
        Analyzes translations to determine if they are:
        - formal: Uses formal language, respectful tone
        - informal: Uses casual language, friendly tone
        - neutral: Balanced, professional tone
        """
        # This is a simplified implementation
        # In production, this would use NLP to analyze tone
        
        style_profile = {}
        
        # Group by context type
        context_groups: Dict[str, List[TranslationEntry]] = {}
        for entry in entries:
            context_type = self._get_context_type(entry)
            if context_type not in context_groups:
                context_groups[context_type] = []
            context_groups[context_type].append(entry)
        
        # Default to neutral for all context types
        for context_type in context_groups:
            style_profile[context_type] = "neutral"
        
        return style_profile
    
    def _get_context_type(self, entry: TranslationEntry) -> str:
        """Get context type from entry."""
        if entry.context:
            # Try to infer from context
            if entry.context.fieldname:
                fieldname = entry.context.fieldname.lower()
                if "button" in fieldname or "action" in fieldname:
                    return "button"
                elif "label" in fieldname or "title" in fieldname:
                    return "label"
                elif "description" in fieldname or "content" in fieldname:
                    return "paragraph"
            
            # Default based on layer
            if entry.context.layer == "A":
                return "label"  # Most Layer A content is labels
            elif entry.context.layer == "B":
                return "label"  # Layer B is UI metadata
            elif entry.context.layer == "C":
                return "paragraph"  # Layer C is content
        
        return "label"  # Default

