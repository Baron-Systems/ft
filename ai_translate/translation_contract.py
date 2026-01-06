"""Translation Contract Builder - Language-specific translation contracts."""

from typing import Dict, List, Optional

from ai_translate.language_memory import LanguageMemory


class TranslationContract:
    """Translation contract for a specific language."""
    
    def __init__(self, memory: LanguageMemory):
        """
        Initialize translation contract.
        
        Args:
            memory: Language memory instance
        """
        self.memory = memory
        self.lang = memory.lang
    
    def build_prompt(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "en",
        context_type: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Build context-aware translation prompt.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code
            context_type: UI element type (button, label, title, paragraph)
            additional_context: Additional context string
            
        Returns:
            Formatted prompt string
        """
        # Get terminology constraints
        terminology_section = self._build_terminology_section(text)
        
        # Get style guidance
        style = self.memory.get_style(context_type or "label")
        style_section = self._build_style_section(style, context_type)
        
        # Get examples
        examples_section = self._build_examples_section(context_type)
        
        # Build context part
        context_part = ""
        if additional_context:
            context_part = f"\nAdditional Context: {additional_context}"
        
        prompt = f"""Translate the following text from {source_lang} to {target_lang}.{context_part}

{terminology_section}

{style_section}

{examples_section}

Rules:
- Preserve ALL placeholders exactly as they appear (e.g., {{0}}, {{1}}, %(name)s, {{{{ var }}}})
- Keep the same formatting and structure
- Do NOT translate technical terms, code, URLs, or email addresses
- Translate according to meaning and context, not word-by-word
- Use consistent terminology from the terminology list above
- Follow the style guidelines above
- Return ONLY the translated text, no explanations, no instructions, no additional text

Text: {text}

Translation:"""
        
        return prompt
    
    def _build_terminology_section(self, text: str) -> str:
        """Build terminology section from memory."""
        # Extract potential terms from text
        words = text.split()
        relevant_terms = {}
        
        for word in words:
            clean_word = word.strip(".,!?;:")
            if clean_word in self.memory.terminology:
                relevant_terms[clean_word] = self.memory.terminology[clean_word]
        
        if not relevant_terms:
            return ""
        
        # Build terminology list
        term_lines = ["Terminology (use these translations consistently):"]
        for source, translated in relevant_terms.items():
            term_lines.append(f"  - {source} → {translated}")
        
        return "\n".join(term_lines)
    
    def _build_style_section(self, style: str, context_type: Optional[str]) -> str:
        """Build style guidance section."""
        style_guidance = {
            "formal": "Use formal language with respectful tone. Avoid casual expressions.",
            "informal": "Use friendly, casual language. Be approachable and conversational.",
            "neutral": "Use professional, balanced language. Neither too formal nor too casual.",
        }
        
        guidance = style_guidance.get(style, style_guidance["neutral"])
        
        if context_type:
            return f"Style ({context_type}, {style}): {guidance}"
        else:
            return f"Style ({style}): {guidance}"
    
    def _build_examples_section(self, context_type: Optional[str]) -> str:
        """Build examples section from memory."""
        examples = self.memory.get_examples(context_type)
        
        if not examples:
            return ""
        
        # Take up to 3 examples
        example_list = examples[:3]
        
        example_lines = ["Examples (follow this style and terminology):"]
        for ex in example_list:
            example_lines.append(f"  - {ex.source} → {ex.translated}")
        
        return "\n".join(example_lines)
    
    def validate_consistency(
        self, source: str, translated: str, context_type: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate translation consistency with memory.
        
        Args:
            source: Source text
            translated: Translated text
            context_type: Context type
            
        Returns:
            Tuple of (is_consistent, reason_if_not)
        """
        # Check terminology consistency
        words = source.split()
        for word in words:
            clean_word = word.strip(".,!?;:")
            if clean_word in self.memory.terminology:
                expected_translation = self.memory.terminology[clean_word]
                # Check if expected term appears in translation
                if expected_translation.lower() not in translated.lower():
                    return False, f"Term '{clean_word}' should be translated as '{expected_translation}'"
        
        # Check against examples
        examples = self.memory.get_examples(context_type)
        for ex in examples:
            if ex.source.lower() == source.lower():
                # Check if translation matches example
                if ex.translated.lower() != translated.lower():
                    # Allow slight variations, but flag for review
                    return True, "Translation differs from example, may need review"
        
        return True, None
    
    def check_terminology(self, text: str) -> Dict[str, str]:
        """
        Check which terminology terms appear in text.
        
        Args:
            text: Text to check
            
        Returns:
            Dictionary of found terms and their translations
        """
        found_terms = {}
        words = text.split()
        
        for word in words:
            clean_word = word.strip(".,!?;:")
            if clean_word in self.memory.terminology:
                found_terms[clean_word] = self.memory.terminology[clean_word]
        
        return found_terms

