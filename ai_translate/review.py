"""Review System - Manage translation reviews and approvals."""

from pathlib import Path
from typing import List, Optional

from ai_translate.language_memory import LanguageMemoryManager
from ai_translate.storage import TranslationEntry, TranslationStorage


class ReviewManager:
    """Manager for translation reviews."""
    
    def __init__(
        self,
        storage: TranslationStorage,
        memory_manager: Optional[LanguageMemoryManager] = None,
    ):
        """
        Initialize review manager.
        
        Args:
            storage: Translation storage instance
            memory_manager: Language memory manager (optional)
        """
        self.storage = storage
        self.memory_manager = memory_manager
    
    def list_needing_review(
        self, status: Optional[str] = None
    ) -> List[TranslationEntry]:
        """
        List translations needing review.
        
        Args:
            status: Filter by review status (e.g., "needs_review")
            
        Returns:
            List of translation entries
        """
        all_entries = self.storage.get_all()
        
        if status:
            return [
                e for e in all_entries
                if e.review_status == status or (status == "needs_review" and e.needs_review)
            ]
        else:
            return [
                e for e in all_entries
                if e.needs_review or e.review_status == "needs_review"
            ]
    
    def approve(
        self,
        source_text: str,
        update_memory: bool = True,
    ) -> bool:
        """
        Approve a translation.
        
        Args:
            source_text: Source text to approve
            update_memory: Update language memory with approved translation
            
        Returns:
            True if successful
        """
        # Get entry
        entry = self.storage.get_entry_by_source(source_text)
        if not entry:
            return False
        
        # Update review status
        entry.review_status = "approved"
        entry.needs_review = False
        
        # Update in storage
        self.storage.set(
            entry.source_text,
            entry.translated_text,
            entry.context,
            entry.source_file,
            entry.line_number,
        )
        self.storage.save()
        
        # Update memory if requested
        if update_memory and self.memory_manager:
            memory = self.memory_manager.get_memory(self.storage.lang)
            context_type = self._get_context_type(entry)
            memory.add_translation(
                source=entry.source_text,
                translated=entry.translated_text,
                context=context_type,
                confidence=0.95,
                review_status="approved",
            )
            self.memory_manager.save_memory(self.storage.lang)
        
        return True
    
    def reject(
        self,
        source_text: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Reject a translation.
        
        Args:
            source_text: Source text to reject
            reason: Optional rejection reason
            
        Returns:
            True if successful
        """
        # Get entry
        entry = self.storage.get_entry_by_source(source_text)
        if not entry:
            return False
        
        # Update review status
        entry.review_status = "rejected"
        entry.needs_review = True
        
        # Update in storage
        self.storage.set(
            entry.source_text,
            entry.translated_text,
            entry.context,
            entry.source_file,
            entry.line_number,
        )
        self.storage.save()
        
        return True
    
    def update_confidence(
        self,
        source_text: str,
        confidence: float,
    ) -> bool:
        """
        Update confidence score for a translation.
        
        Args:
            source_text: Source text
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            True if successful
        """
        # Get entry
        entry = self.storage.get_entry_by_source(source_text)
        if not entry:
            return False
        
        # Update confidence
        entry.confidence = max(0.0, min(1.0, confidence))
        
        # Mark for review if confidence is low
        if confidence < 0.7:
            entry.needs_review = True
            entry.review_status = "needs_review"
        
        # Update in storage
        self.storage.set(
            entry.source_text,
            entry.translated_text,
            entry.context,
            entry.source_file,
            entry.line_number,
        )
        self.storage.save()
        
        return True
    
    def _get_context_type(self, entry: TranslationEntry) -> str:
        """Get context type from entry."""
        if entry.context:
            if entry.context.fieldname:
                fieldname = entry.context.fieldname.lower()
                if "button" in fieldname or "action" in fieldname:
                    return "button"
                elif "label" in fieldname or "title" in fieldname:
                    return "label"
                elif "description" in fieldname or "content" in fieldname:
                    return "paragraph"
            
            if entry.context.layer == "A":
                return "label"
            elif entry.context.layer == "B":
                return "label"
            elif entry.context.layer == "C":
                return "paragraph"
        
        return "label"

