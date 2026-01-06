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
        decision = self.policy.decide(text, policy_context)

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

                # Validate placeholders
                if not self.policy.validate_placeholders(text, translated):
                    self.stats["rejected"] += 1
                    # Only show warnings in verbose mode to avoid spam
                    self.output.warning(
                        f"Placeholder mismatch: '{text}' -> '{translated}'",
                        verbose_only=True
                    )
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
        batch_size: int = 10,
    ) -> List[Tuple[Optional[str], str]]:
        """
        Translate a batch of texts.

        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            batch_size: Batch size for API calls

        Returns:
            List of (translated_text, status) tuples
        """
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                result = self.translate(text, target_lang, source_lang)
                results.append(result)

                # Rate limiting in slow mode
                if self.slow_mode:
                    time.sleep(0.5)

        return results

    def _build_prompt(
        self,
        text: str,
        target_lang: str,
        source_lang: str,
        context: Optional[str],
    ) -> str:
        """Build translation prompt."""
        # Use a cleaner, more direct prompt
        prompt = f"""Translate the following text from {source_lang} to {target_lang}.

Rules:
- Preserve ALL placeholders exactly as they appear (e.g., {{0}}, {{1}}, %(name)s, {{{{ var }}}})
- Keep the same formatting and structure
- Do NOT translate technical terms, code, URLs, or email addresses
- Return ONLY the translated text, no explanations, no instructions, no additional text

Text: {text}

Translation:"""
        return prompt

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

