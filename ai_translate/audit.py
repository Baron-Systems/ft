"""Translation Audit Module - Statistics and rejection reasons."""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from ai_translate.policy import PolicyEngine, RejectionReason
from ai_translate.storage import TranslationEntry, TranslationStorage


class TranslationAuditor:
    """Auditor for translation statistics and quality."""
    
    def __init__(
        self,
        storage: TranslationStorage,
        policy: Optional[PolicyEngine] = None,
    ):
        """
        Initialize translation auditor.
        
        Args:
            storage: Translation storage instance
            policy: Policy engine instance (optional)
        """
        self.storage = storage
        self.policy = policy or PolicyEngine()
    
    def audit(self) -> Dict:
        """
        Perform comprehensive audit.
        
        Returns:
            Dictionary with audit results
        """
        entries = self.storage.get_all()
        
        results = {
            "total_translations": len(entries),
            "by_doctype": defaultdict(int),
            "by_field": defaultdict(int),
            "rejection_reasons": defaultdict(int),
            "needs_review": [],
            "samples": {},
        }
        
        # Analyze each entry
        for entry in entries:
            # Count by doctype
            if entry.context and entry.context.doctype:
                results["by_doctype"][entry.context.doctype] += 1
            
            # Count by field
            if entry.context and entry.context.fieldname:
                field_key = f"{entry.context.doctype or 'unknown'}.{entry.context.fieldname}"
                results["by_field"][field_key] += 1
            
            # Check rejection reasons
            if entry.context:
                decision, reason = self.policy.decide(entry.source_text, entry.context)
                if reason:
                    results["rejection_reasons"][reason.value] += 1
            
            # Check if needs review
            if entry.needs_review or entry.review_status == "needs_review":
                results["needs_review"].append({
                    "source": entry.source_text,
                    "translated": entry.translated_text,
                    "context": entry.context.doctype if entry.context else None,
                })
        
        # Get samples per doctype
        for doctype in list(results["by_doctype"].keys())[:10]:  # Top 10
            samples = [
                {
                    "source": e.source_text,
                    "translated": e.translated_text,
                }
                for e in entries
                if e.context and e.context.doctype == doctype
            ][:5]  # 5 samples per doctype
            results["samples"][doctype] = samples
        
        return results
    
    def print_report(self, verbose: bool = False):
        """Print audit report."""
        results = self.audit()
        
        print("\n" + "=" * 60)
        print("Translation Audit Report")
        print("=" * 60)
        print(f"\nTotal Translations: {results['total_translations']}")
        
        # Rejection reasons
        if results["rejection_reasons"]:
            print("\nRejection Reasons:")
            for reason, count in sorted(
                results["rejection_reasons"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  - {reason}: {count}")
        
        # By DocType
        if results["by_doctype"]:
            print("\nTranslations by DocType:")
            for doctype, count in sorted(
                results["by_doctype"].items(), key=lambda x: x[1], reverse=True
            )[:10]:
                print(f"  - {doctype}: {count}")
        
        # Needs review
        if results["needs_review"]:
            print(f"\nTranslations Needing Review: {len(results['needs_review'])}")
            if verbose:
                for item in results["needs_review"][:10]:
                    print(f"  - {item['source']} → {item['translated']}")
        
        # Samples
        if verbose and results["samples"]:
            print("\nSamples:")
            for doctype, samples in list(results["samples"].items())[:5]:
                print(f"\n  {doctype}:")
                for sample in samples[:3]:
                    print(f"    - {sample['source']} → {sample['translated']}")
        
        print("\n" + "=" * 60)

