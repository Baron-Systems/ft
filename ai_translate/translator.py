"""Groq API integration for translation."""

import os
import time
from typing import List, Optional, Tuple

from groq import Groq

from ai_translate.output import OutputFilter
from ai_translate.policy import PolicyEngine


class Translator:
    """Groq API translator with batching and retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        slow_mode: bool = False,
        output: Optional[OutputFilter] = None,
    ):
        """
        Initialize translator.

        Args:
            api_key: Groq API key (or from GROQ_API_KEY env var)
            slow_mode: Enable slow mode (rate limiting)
            output: Output filter instance
        """
        self.output = output or OutputFilter()
        self.slow_mode = slow_mode
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        self.client = Groq(api_key=self.api_key)
        self.policy = PolicyEngine()
        # Use a supported model (llama-3.1-70b-versatile was decommissioned)
        # Try models in order of preference
        self.models = [
            "llama-3.3-70b-versatile",  # Latest versatile model
            "llama-3.1-8b-instant",     # Fast alternative
            "mixtral-8x7b-32768",        # Alternative model
        ]
        self.current_model_index = 0
        self.stats = {
            "translated": 0,
            "failed": 0,
            "skipped": 0,
            "rejected": 0,
        }

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "en",
        context: Optional[str] = None,
    ) -> Tuple[Optional[str], str]:
        """
        Translate a single text.

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code
            context: Optional context for translation

        Returns:
            Tuple of (translated_text, status)
            Status: "ok", "failed", "skipped", "rejected"
        """
        # Check policy first
        from ai_translate.policy import TranslationContext

        # Create minimal context for policy check
        policy_context = TranslationContext(layer="A")
        decision, reason = self.policy.decide(text, policy_context)

        if decision.value == "skip":
            self.stats["skipped"] += 1
            return None, "skipped"
        elif decision.value == "keep_original":
            self.stats["skipped"] += 1
            return text, "skipped"

        # Prepare prompt
        prompt = self._build_prompt(text, target_lang, source_lang, context)

        # Try models in order until one works
        last_error = None
        for model_index in range(self.current_model_index, len(self.models)):
            model = self.models[model_index]
            try:
                # Call Groq API
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional translator. Return ONLY the translated text, nothing else. Preserve all placeholders exactly.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,  # Lower temperature for more consistent output
                    max_tokens=500,  # Reduce max tokens to prevent verbose responses
                )

                translated = response.choices[0].message.content.strip()
                
                # Clean up: Remove any instruction text that might have been included
                # Look for common patterns where the model includes instructions
                lines = translated.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    # Skip lines that look like instructions
                    if any(keyword in line.lower() for keyword in ['important:', 'rules:', 'preserve', 'do not', 'return', 'translation:', 'نص', 'مهم', 'احفظ', 'لا تترجم']):
                        # Check if this line contains actual translation content
                        if not any(keyword in line.lower() for keyword in ['translate', 'ترجمة', 'translation']):
                            continue
                    # Skip empty lines at the start
                    if not cleaned_lines and not line:
                        continue
                    cleaned_lines.append(line)
                
                # Join and clean
                translated = '\n'.join(cleaned_lines).strip()
                
                # If translation still contains instruction-like text, try to extract just the translation part
                if 'translation:' in translated.lower() or 'ترجمة' in translated.lower():
                    # Try to find the actual translation after "Translation:" or similar
                    parts = translated.split(':', 1)
                    if len(parts) > 1:
                        translated = parts[1].strip()
                
                # Final cleanup: remove any remaining instruction markers
                translated = translated.replace('Translation:', '').replace('ترجمة:', '').strip()

                # Guardrail: reject obviously wrong-language outputs (e.g., Chinese when target is Arabic)
                if self._fails_language_guard(translated, target_lang):
                    self.stats["rejected"] += 1
                    return None, "rejected"

                # Validate placeholders
                if not self.policy.validate_placeholders(text, translated):
                    self.stats["rejected"] += 1
                    # Don't show warnings during translation to avoid cluttering progress bar
                    # Warnings will be shown in summary if needed
                    return None, "rejected"

                # Success - update model index for future calls
                self.current_model_index = model_index
                self.stats["translated"] += 1
                return translated, "ok"

            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if model is decommissioned or invalid
                if "decommissioned" in error_str.lower() or "invalid" in error_str.lower() or "not found" in error_str.lower():
                    # Try next model
                    if model_index < len(self.models) - 1:
                        self.output.warning(f"Model {model} not available, trying next model...", verbose_only=True)
                        continue
                
                # If it's a different error and we haven't tried all models, try next
                if model_index < len(self.models) - 1:
                    self.output.warning(f"Error with model {model}, trying next model...", verbose_only=True)
                    continue
                
                # All models failed
                break
        
        # All models failed
        self.stats["failed"] += 1
        error_msg = str(last_error) if last_error else "Unknown error"
        # Only show error once per unique error message to avoid spam
        if not hasattr(self, '_last_error') or self._last_error != error_msg:
            self.output.error(f"Translation failed: {error_msg}")
            self._last_error = error_msg
        return None, "failed"

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "en",
        batch_size: int = 30,
        context: Optional[str] = None,
    ) -> List[Tuple[Optional[str], str]]:
        """
        Translate a batch of texts using true batching.

        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            batch_size: Batch size for API calls (20-50 recommended)
            context: Optional context for translation

        Returns:
            List of (translated_text, status) tuples
        """
        if not texts:
            return []
        
        # Clamp batch size to reasonable range
        batch_size = max(10, min(50, batch_size))
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            
            # Try batch translation first
            batch_results = self._translate_batch_internal(
                batch, target_lang, source_lang, context
            )
            
            # If batch translation failed, fallback to individual
            if batch_results is None:
                # Fallback to individual translation
                for text in batch:
                    result = self.translate(text, target_lang, source_lang, context)
                    results.append(result)
                    
                    # Rate limiting in slow mode
                    if self.slow_mode:
                        time.sleep(0.3)
            else:
                results.extend(batch_results)
                
                # Rate limiting in slow mode
                if self.slow_mode:
                    time.sleep(0.5)
        
        return results
    
    def _translate_batch_internal(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str,
        context: Optional[str],
    ) -> Optional[List[Tuple[Optional[str], str]]]:
        """
        Internal batch translation using single API call.
        
        Returns None if batch translation fails (should fallback to individual).
        """
        try:
            # Build batch prompt
            prompt = self._build_batch_prompt(texts, target_lang, source_lang, context)
            
            # Try models in order
            last_error = None
            for model_index in range(self.current_model_index, len(self.models)):
                model = self.models[model_index]
                try:
                    # Call Groq API
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a professional translator. Return translations in JSON format or newline-separated format. Preserve all placeholders exactly.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                        max_tokens=2000,  # More tokens for batch
                    )
                    
                    translated_text = response.choices[0].message.content.strip()
                    
                    # Parse batch response
                    parsed_results = self._parse_batch_response(
                        translated_text, texts, target_lang
                    )
                    
                    if parsed_results:
                        # Success - update model index
                        self.current_model_index = model_index
                        return parsed_results
                    
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    
                    # Check if model is decommissioned or invalid
                    if "decommissioned" in error_str.lower() or "invalid" in error_str.lower() or "not found" in error_str.lower():
                        if model_index < len(self.models) - 1:
                            self.output.warning(f"Model {model} not available, trying next model...", verbose_only=True)
                            continue
                    
                    # If it's a different error and we haven't tried all models, try next
                    if model_index < len(self.models) - 1:
                        self.output.warning(f"Error with model {model}, trying next model...", verbose_only=True)
                        continue
                    
                    break
            
            # All models failed
            return None
            
        except Exception as e:
            # Batch translation failed, return None to trigger fallback
            self.output.warning(f"Batch translation failed: {e}, falling back to individual translation", verbose_only=True)
            return None

    def _build_prompt(
        self,
        text: str,
        target_lang: str,
        source_lang: str,
        context: Optional[str],
    ) -> str:
        """Build translation prompt for single text."""
        # Build context-aware prompt
        context_part = ""
        if context:
            context_part = f"\nContext: This text is from a {context}. Translate according to the meaning and context, not literally."
        
        prompt = f"""Translate the following text from {source_lang} to {target_lang}.{context_part}

Rules:
- Preserve ALL placeholders exactly as they appear (e.g., {{0}}, {{1}}, %(name)s, {{{{ var }}}})
- Keep the same formatting and structure
- Do NOT translate technical terms, code, URLs, or email addresses
- Translate according to meaning and context, not word-by-word
- Return ONLY the translated text, no explanations, no instructions, no additional text

Text: {text}

Translation:"""
        return prompt

    def _fails_language_guard(self, translated: str, target_lang: str) -> bool:
        """
        Heuristic guard against clearly wrong-language outputs.
        Currently focuses on preventing CJK output when target is Arabic.
        """
        lang = (target_lang or "").strip().lower()
        if lang != "ar":
            return False

        # Arabic blocks + extended Arabic
        arabic_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", translated))
        # CJK Unified + Extensions + Hiragana/Katakana (common Chinese/Japanese outputs)
        cjk_chars = len(re.findall(r"[\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u30FF]", translated))

        # If it contains CJK and essentially no Arabic, it's wrong for --lang ar.
        return cjk_chars > 0 and arabic_chars == 0
    
    def _build_batch_prompt(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str,
        context: Optional[str],
    ) -> str:
        """Build batch translation prompt."""
        # Build context-aware prompt
        context_part = ""
        if context:
            context_part = f"\nContext: These texts are from a {context}. Translate according to the meaning and context, not literally."
        
        # Number each text for reference
        numbered_texts = []
        for i, text in enumerate(texts, 1):
            numbered_texts.append(f"{i}. {text}")
        
        texts_block = "\n".join(numbered_texts)
        
        prompt = f"""Translate the following {len(texts)} texts from {source_lang} to {target_lang}.{context_part}

Rules:
- Preserve ALL placeholders exactly as they appear (e.g., {{0}}, {{1}}, %(name)s, {{{{ var }}}})
- Keep the same formatting and structure
- Do NOT translate technical terms, code, URLs, or email addresses
- Translate according to meaning and context, not word-by-word
- Return translations in the same order, one per line, or as JSON array

Texts:
{texts_block}

Translations (one per line or JSON array):"""
        return prompt
    
    def _parse_batch_response(
        self,
        response: str,
        original_texts: List[str],
        target_lang: str,
    ) -> Optional[List[Tuple[Optional[str], str]]]:
        """
        Parse batch translation response.
        
        Supports:
        - JSON array format: ["trans1", "trans2", ...]
        - Newline-separated format
        - Numbered format: "1. trans1\n2. trans2\n..."
        """
        if not response:
            return None
        
        results = []
        
        # Try JSON format first
        import json
        try:
            # Try to parse as JSON
            if response.strip().startswith('['):
                parsed = json.loads(response)
                if isinstance(parsed, list) and len(parsed) == len(original_texts):
                    for i, trans in enumerate(parsed):
                        if isinstance(trans, str):
                            trans = trans.strip()
                            # Guardrail: wrong-language outputs (e.g., CJK when target is Arabic)
                            if self._fails_language_guard(trans, target_lang):
                                results.append((None, "rejected"))
                                self.stats["rejected"] += 1
                            # Validate placeholders (also blocks introducing new { } fields)
                            elif self.policy.validate_placeholders(original_texts[i], trans):
                                results.append((trans, "ok"))
                                self.stats["translated"] += 1
                            else:
                                results.append((None, "rejected"))
                                self.stats["rejected"] += 1
                        else:
                            results.append((None, "failed"))
                            self.stats["failed"] += 1
                    return results
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try newline-separated format
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Filter out instruction lines
        filtered_lines = []
        for line in lines:
            # Skip lines that look like instructions
            if any(keyword in line.lower() for keyword in ['important:', 'rules:', 'preserve', 'do not', 'return', 'translation:', 'translations:']):
                continue
            # Skip numbered prefixes if present
            if line and line[0].isdigit() and '. ' in line[:5]:
                line = line.split('. ', 1)[1] if '. ' in line else line
            filtered_lines.append(line)
        
        # Match lines to original texts
        if len(filtered_lines) >= len(original_texts):
            # Take first N lines
            for i, trans in enumerate(filtered_lines[:len(original_texts)]):
                # Guardrail: wrong-language outputs
                if self._fails_language_guard(trans, target_lang):
                    results.append((None, "rejected"))
                    self.stats["rejected"] += 1
                # Validate placeholders (also blocks introducing new { } fields)
                elif self.policy.validate_placeholders(original_texts[i], trans):
                    results.append((trans, "ok"))
                    self.stats["translated"] += 1
                else:
                    results.append((None, "rejected"))
                    self.stats["rejected"] += 1
            return results
        
        # If we don't have enough translations, return None to trigger fallback
        return None

    def get_stats(self) -> dict:
        """Get translation statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "translated": 0,
            "failed": 0,
            "skipped": 0,
            "rejected": 0,
        }

