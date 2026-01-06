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

        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate accurately while preserving placeholders, formatting, and technical terms.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            translated = response.choices[0].message.content.strip()

            # Validate placeholders
            if not self.policy.validate_placeholders(text, translated):
                self.stats["rejected"] += 1
                self.output.warning(
                    f"Placeholder mismatch: '{text}' -> '{translated}'"
                )
                return None, "rejected"

            self.stats["translated"] += 1
            return translated, "ok"

        except Exception as e:
            self.stats["failed"] += 1
            self.output.error(f"Translation failed: {e}")
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
        prompt = f"Translate the following text from {source_lang} to {target_lang}."
        if context:
            prompt += f"\n\nContext: {context}"
        prompt += "\n\nImportant:"
        prompt += "\n- Preserve all placeholders exactly (e.g., {0}, %(name)s, {{ var }})"
        prompt += "\n- Preserve formatting and line breaks"
        prompt += "\n- Do not translate technical terms, URLs, or email addresses"
        prompt += "\n- Only return the translated text, nothing else"
        prompt += f"\n\nText to translate:\n{text}"
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

