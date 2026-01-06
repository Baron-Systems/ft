"""CLI entrypoint for ai-translate - Language-Agnostic Localization Infrastructure."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console

from ai_translate.db_scope import DBExtractor
from ai_translate.db_write import TranslationDBWriter
from ai_translate.extractors import LayerAExtractor
from ai_translate.fixers import TranslationFixer
from ai_translate.gettext_sync import GettextSync
from ai_translate.manager import BenchManager
from ai_translate.output import OutputFilter
from ai_translate.progress import ProgressTracker
from ai_translate.storage import TranslationEntry, TranslationStorage
from ai_translate.translator import Translator

console = Console()

class DefaultToTranslateGroup(click.Group):
    """
    Click Group that defaults to `translate` when the first token is not a known subcommand.

    This enables the ergonomic (and common) usage:
        ai-translate erpnext --lang ar --site mysite

    which will be treated as:
        ai-translate translate erpnext --lang ar --site mysite
    """

    default_cmd_name = "translate"

    def resolve_command(self, ctx: click.Context, args: List[str]):
        if args and args[0] and not args[0].startswith("-"):
            cmd_name = args[0]
            if cmd_name not in self.commands:
                args.insert(0, self.default_cmd_name)
        return super().resolve_command(ctx, args)


@click.group(cls=DefaultToTranslateGroup)
@click.version_option(version="1.0.0")
def cli():
    """AI-powered Localization Infrastructure for Frappe / ERPNext.
    
    Language-Agnostic translation system that localizes user-visible semantics
    while preserving internal representations and logic.
    """
    pass


@cli.command()
@click.argument('apps', required=True)
@click.option('--lang', '-l', required=True, help='Target language code (e.g., ar, fr, de, es)')
@click.option('--site', '-s', help='Site name (required for Layers B & C)')
@click.option('--context', '-c', help='App description/context (improves meaning-based translations)')
@click.option('--bench-path', '-b', help='Path to bench directory')
@click.option('--db-scope', is_flag=True, hidden=True, help='Include database content (Layers B & C) (advanced)')
@click.option('--db-scope-only', is_flag=True, hidden=True, help='Only process database content (skip Layer A) (advanced)')
@click.option('--db-doc-types', hidden=True, help='Comma-separated allowlist of DocTypes to extract (advanced)')
@click.option('--repair-existing', is_flag=True, hidden=True, help='Re-translate clearly corrupted existing translations (advanced)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--slow-mode', is_flag=True, hidden=True, help='Enable slow mode (rate limiting) (advanced)')
@click.option('--dry-run', is_flag=True, help='Dry run mode (no writes)')
def translate(
    apps: str,
    lang: str,
    site: Optional[str],
    context: Optional[str],
    bench_path: Optional[str],
    db_scope: bool,
    db_scope_only: bool,
    db_doc_types: Optional[str],
    repair_existing: bool,
    verbose: bool,
    slow_mode: bool,
    dry_run: bool,
):
    """Translate app(s) - extracts all user-visible strings and translates missing ones.
    
    Automatically extracts from:
    - Code files (Python, JavaScript, HTML) - Layer A
    - JSON fixtures (DocTypes, Workspaces, Reports, etc.) - Layer A
    - Database content (if --site and --db-scope provided) - Layers B & C
    
    Only translates missing strings - preserves existing translations.
    
    Examples:
        ai-translate erpnext --lang ar --site mysite
        ai-translate translate erpnext --lang ar --site mysite --context "HR Management System"
    """
    _translate_impl(
        apps=apps,
        lang=lang,
        site=site,
        context=context,
        bench_path=bench_path,
        db_scope=db_scope,
        db_scope_only=db_scope_only,
        db_doc_types=db_doc_types,
        repair_existing=repair_existing,
        verbose=verbose,
        slow_mode=slow_mode,
        dry_run=dry_run,
    )


@cli.command(name='list-benches', hidden=True)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def list_benches(verbose: bool):
    """List available benches (including Frappe Manager benches)."""
    output = OutputFilter(verbose=verbose)
    output.info("Searching for benches...")
    
    benches_found = []
    benches_set = set()
    
    # Try Frappe Manager - 'fm bench list'
    try:
        result = subprocess.run(
            ["fm", "bench", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            output.success("Frappe Manager benches found (fm bench list):")
            for line in result.stdout.splitlines():
                if "->" in line:
                    parts = line.split("->")
                    if len(parts) == 2:
                        bench_name = parts[0].strip()
                        bench_path = Path(parts[1].strip()).resolve()
                        if bench_path.exists() and (bench_path / "sites").exists():
                            benches_set.add(bench_path)
                            benches_found.append((bench_name, bench_path))
                            output.info(f"  {bench_name} -> {bench_path}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    except Exception as e:
        if verbose:
            output.warning(f"Error checking 'fm bench list': {e}")
    
    # Try Frappe Manager - 'fm list' (sites)
    try:
        result = subprocess.run(
            ["fm", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Parse table output to extract bench paths from site paths
            site_paths = []
            for line in result.stdout.splitlines():
                if "/sites/" in line or "/frappe/" in line:
                    parts = line.split()
                    for part in parts:
                        if "/sites/" in part:
                            site_path = Path(part.strip())
                            if site_path.exists():
                                site_paths.append(site_path)
            
            if site_paths:
                output.success("Frappe Manager sites found (fm list):")
                # Extract unique bench paths
                for site_path in site_paths:
                    # Frappe Manager structure:
                    # Site path: /home/baron/frappe/sites/site-name
                    # Bench path: /home/baron/frappe/sites/site-name/workspace/frappe-bench
                    
                    # First, check workspace/frappe-bench pattern (Frappe Manager)
                    workspace_bench = site_path / "workspace" / "frappe-bench"
                    if workspace_bench.exists() and (workspace_bench / "sites").exists() and (workspace_bench / "apps").exists():
                        bench_path = workspace_bench.resolve()
                        if bench_path not in benches_set:
                            benches_set.add(bench_path)
                            site_name = site_path.name
                            benches_found.append((f"bench (site: {site_name})", bench_path))
                            output.info(f"  Site: {site_name} -> Bench: {bench_path}")
                            continue
                    
                    # Legacy: Try parent directory (for non-Frappe Manager setups)
                    potential_bench = site_path.parent
                    if (potential_bench / "sites").exists() and (potential_bench / "apps").exists():
                        bench_path = potential_bench.resolve()
                        if bench_path not in benches_set:
                            benches_set.add(bench_path)
                            site_name = site_path.name
                            benches_found.append((f"bench (site: {site_name})", bench_path))
                            output.info(f"  Site: {site_name} -> Bench: {bench_path}")
                    
                    # Also check parent's parent
                    potential_bench2 = potential_bench.parent
                    if (potential_bench2 / "sites").exists() and (potential_bench2 / "apps").exists():
                        bench_path = potential_bench2.resolve()
                        if bench_path not in benches_set:
                            benches_set.add(bench_path)
                            site_name = site_path.name
                            benches_found.append((f"bench (site: {site_name})", bench_path))
                            output.info(f"  Site: {site_name} -> Bench: {bench_path}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        output.info("Frappe Manager (fm) not available")
    except Exception as e:
        if verbose:
            output.warning(f"Error checking 'fm list': {e}")
    
    # Check current directory
    cwd = Path.cwd()
    if (cwd / "sites").exists():
        benches_found.append(("current directory", cwd))
        output.info(f"\nCurrent directory is a bench: {cwd}")
    
    # Check common locations
    common_paths = [
        ("~/.local/share/frappe-bench", Path.home() / ".local" / "share" / "frappe-bench"),
        ("~/frappe-bench", Path.home() / "frappe-bench"),
        ("/home/frappe/frappe-bench", Path("/home/frappe/frappe-bench")),
        ("/opt/frappe/frappe-bench", Path("/opt/frappe/frappe-bench")),
    ]
    
    found_common = False
    for name, path in common_paths:
        if path.exists() and (path / "sites").exists():
            if not any(bp == path for _, bp in benches_found):
                benches_found.append((name, path))
                if not found_common:
                    output.info("\nOther benches found:")
                    found_common = True
                output.info(f"  {name} -> {path}")
    
    if not benches_found:
        output.warning("No benches found")
        output.info("\nTo use a bench, specify it with --bench-path:")
        output.info("  ai-translate translate erpnext --lang ar --site site-name --bench-path /path/to/bench")
    else:
        output.success(f"\nFound {len(benches_found)} bench(es)")
        output.info("\nUse --bench-path to specify which bench to use")


@cli.command()
@click.argument('apps', required=True)
@click.option('--lang', '-l', required=True, help='Language code to review')
@click.option('--context', '-c', help='App description/context for better translation')
@click.option('--bench-path', '-b', help='Path to bench directory')
@click.option('--status', help='Filter by review status (e.g., needs_review)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def review(
    apps: str,
    lang: str,
    context: Optional[str],
    bench_path: Optional[str],
    status: Optional[str],
    verbose: bool,
):
    """Review and improve translations with AI context.
    
    Allows you to provide app context/description to improve translations
    based on meaning and context rather than literal translation.
    
    Example:
        ai-translate review erpnext --lang ar --context "Enterprise Resource Planning System"
    """
    output = OutputFilter(verbose=verbose)
    
    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        output.error("GROQ_API_KEY environment variable is required")
        sys.exit(1)
    
    # Initialize bench manager
    bench_manager = BenchManager(bench_path=bench_path, output=output)
    if not bench_manager.bench_path:
        output.error("Could not find bench directory")
        sys.exit(1)
    
    # Parse app names
    app_names = [a.strip() for a in apps.split(",") if a.strip()]
    if not app_names:
        output.error("At least one app name must be specified")
        sys.exit(1)
    
    # Initialize translator with context
    try:
        translator = Translator(api_key=api_key, slow_mode=False, output=output)
    except Exception as e:
        output.error(f"Failed to initialize translator: {e}")
        sys.exit(1)
    
    output.info(f"Reviewing translations for: {', '.join(app_names)}")
    if context:
        output.info(f"App context: {context}")
    
    # Process each app
    for app_name in app_names:
        app_path = bench_manager.get_app_path(app_name)
        if not app_path:
            output.warning(f"App path not found: {app_name}")
            continue
        
        app_translations_path = app_path / app_name / "translations"
        storage = TranslationStorage(storage_path=app_translations_path, lang=lang)
        
        if not storage.csv_path.exists():
            output.warning(f"Translation file not found: {storage.csv_path}")
            continue
        
        output.info(f"\nReviewing: {app_name}")
        output.info(f"Translation file: {storage.csv_path}")
        
        # Load all translations
        all_entries = storage.get_all()
        
        # Filter by status if provided
        if status:
            # This will be implemented when review_status is added to TranslationEntry
            pass
        
        output.info(f"Found {len(all_entries)} translations")
        
        if not all_entries:
            output.info("No translations to review")
            continue
        
        # Review each translation
        reviewed_count = 0
        with ProgressTracker(total=len(all_entries), description="Reviewing") as progress:
            batch_size = 50
            for i in range(0, len(all_entries), batch_size):
                batch_entries = all_entries[i : i + batch_size]
                batch_texts = [e.source_text for e in batch_entries]
                results = translator.translate_batch(
                    batch_texts,
                    lang,
                    source_lang="en",
                    batch_size=batch_size,
                    context=context,
                )

                for entry, (translated, trans_status) in zip(batch_entries, results):
                    if trans_status == "ok" and translated and translated != entry.translated_text:
                        # Update if translation improved
                        storage.set(
                            entry.source_text,
                            translated,
                            entry.context,
                            entry.source_file,
                            entry.line_number,
                            update_existing=True,
                        )
                        reviewed_count += 1

                    progress.update()
        
        # Save reviewed translations
        storage.save()
        output.success(f"✓ Reviewed {reviewed_count} translations for {app_name}")


@cli.command(hidden=True)
@click.argument('apps', required=True)
@click.option('--lang', '-l', required=True, help='Language code to audit')
@click.option('--bench-path', '-b', help='Path to bench directory')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def audit(
    apps: str,
    lang: str,
    bench_path: Optional[str],
    verbose: bool,
):
    """Audit translations - show statistics and rejection reasons.
    
    Provides comprehensive statistics per language including:
    - Translation counts
    - Rejection reasons summary
    - Samples per DocType/field
    - New translations needing review
    
    Example:
        ai-translate audit erpnext --lang ar
    """
    # This will be implemented when audit module is created
    output = OutputFilter(verbose=verbose)
    output.info("Audit functionality will be available after audit module implementation")
    output.info(f"Auditing translations for: {apps}, language: {lang}")


def _translate_impl(
    apps: str,
    lang: str,
    site: Optional[str],
    context: Optional[str],
    bench_path: Optional[str],
    db_scope: bool,
    db_scope_only: bool,
    db_doc_types: Optional[str],
    repair_existing: bool,
    verbose: bool,
    slow_mode: bool,
    dry_run: bool,
):
    """
    Implementation of translate command.
    
    Automatically extracts from:
    - Code files (Python, JavaScript, HTML)
    - JSON fixtures (DocTypes, Workspaces, Reports, etc.)
    - Database content (if --site and --db-scope provided)
    
    Only translates missing strings - preserves existing translations.
    """
    
    # Initialize output
    output = OutputFilter(verbose=verbose)

    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        output.error("GROQ_API_KEY environment variable is required")
        sys.exit(1)

    # Determine layers to process
    layer_list = []
    # UX default: if a site is provided and user didn't explicitly ask for "db-only", include DB by default.
    effective_db_scope = db_scope or (bool(site) and not db_scope_only)

    if not db_scope_only:
        layer_list.append("A")  # Always include Layer A unless db-scope-only
    if effective_db_scope or db_scope_only:
        if not site:
            output.error("--site is required to include database content")
            sys.exit(1)
        layer_list.extend(["B", "C"])  # Add database layers
    
    if not layer_list:
        output.error("No layers to process. Use --db-scope to include database content.")
        sys.exit(1)

    # Parse db_doc_types allowlist
    doc_types_allowlist = None
    if db_doc_types:
        doc_types_allowlist = [dt.strip() for dt in db_doc_types.split(",") if dt.strip()]

    # Initialize bench manager
    # If site is provided but bench_path is not, try to get bench from site name using Frappe Manager
    if site and not bench_path:
        temp_manager = BenchManager(bench_path=None, output=output)
        bench_from_site = temp_manager.get_bench_path_from_site(site)
        if bench_from_site:
            bench_path = str(bench_from_site)
            output.info(f"Found bench from site '{site}': {bench_path}", verbose_only=True)
    
    bench_manager = BenchManager(bench_path=bench_path, output=output)
    if not bench_manager.bench_path:
        output.error("Could not find bench directory")
        output.info("")
        output.info("Tips:")
        output.info("  1. Use --bench-path to specify the bench directory explicitly")
        output.info("  2. If using Frappe Manager, the tool will try to find bench from site name")
        output.info("  3. Run: fm list to see available sites")
        output.info("  4. Navigate to the bench directory and run the command from there")
        output.info("")
        output.info("Example:")
        output.info("  ai-translate translate erpnext --lang ar --site site-name")
        output.info("  ai-translate translate erpnext --lang ar --site site-name --bench-path /path/to/bench")
        sys.exit(1)

    output.info(f"Bench path: {bench_manager.bench_path}")

    # Parse app names
    app_names = [a.strip() for a in apps.split(",") if a.strip()]

    if not app_names:
        output.error("No apps found to process")
        sys.exit(1)

    output.info(f"Processing {len(app_names)} app(s): {', '.join(app_names)}")
    output.info(f"Layers: {', '.join(layer_list)}")
    if context:
        output.info(f"Context: {context}")

    # Initialize translator
    try:
        translator = Translator(api_key=api_key, slow_mode=slow_mode, output=output)
    except Exception as e:
        output.error(f"Failed to initialize translator: {e}")
        sys.exit(1)

    # Process each app separately
    all_app_stats = []

    # Create a single PolicyEngine for the whole run so stats are accurate
    from ai_translate.policy import PolicyEngine
    policy = PolicyEngine()

    def _contains_cjk(s: str) -> bool:
        import re
        return bool(re.search(r"[\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u30FF]", s or ""))

    def _contains_arabic(s: str) -> bool:
        import re
        return bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", s or ""))

    def _should_repair_existing(source_text: str, translated_text: str) -> bool:
        # Empty translations are always broken
        if not (translated_text or "").strip():
            return True
        # Placeholder corruption (also catches introducing "{ }", "{}" etc)
        if not policy.validate_placeholders(source_text, translated_text):
            return True
        # Wrong script for Arabic target: Chinese/Japanese output with no Arabic letters
        if (lang or "").strip().lower() == "ar" and _contains_cjk(translated_text) and not _contains_arabic(translated_text):
            return True
        return False

    # Load frappe core translations as a read-only fallback (legacy script behavior)
    frappe_storage = None
    try:
        frappe_app_path = bench_manager.get_app_path("frappe")
        if frappe_app_path:
            frappe_translations_path = frappe_app_path / "frappe" / "translations"
            if frappe_translations_path.exists():
                frappe_storage = TranslationStorage(storage_path=frappe_translations_path, lang=lang)
    except Exception:
        frappe_storage = None

    for app_name in app_names:
        app_path = bench_manager.get_app_path(app_name)
        if not app_path:
            output.warning(f"App path not found: {app_name}")
            continue

        output.info(f"Processing app: {app_name}")

        # Initialize storage for this app - use app's translation directory
        # Frappe standard: apps/app_name/app_name/translations/lang.csv
        app_translations_path = app_path / app_name / "translations"
        storage = TranslationStorage(storage_path=app_translations_path, lang=lang)
        output.info(f"Using translation file: {storage.csv_path}")

        # Extract strings for this app only
        app_extracted = []

        # Layer A: Code & Files
        if "A" in layer_list:
            extractor = LayerAExtractor(app_name=app_name, app_path=app_path)
            extracted = list(extractor.extract_all())
            app_extracted.extend(extracted)
            output.info(f"Extracted {len(extracted)} strings from Layer A")

        # Layers B & C: Database
        if {"B", "C"} & set(layer_list):
            db_extractor = DBExtractor(bench_path=bench_manager.bench_path, site=site)
            if doc_types_allowlist:
                # Filter scopes by allowlist
                scopes = db_extractor.get_scopes_for_layers(layer_list)
                filtered_scopes = [s for s in scopes if s.doctype in doc_types_allowlist]
                db_extracted = []
                for scope in filtered_scopes:
                    db_extracted.extend(list(db_extractor.extract_from_doctype(scope, site=site)))
            else:
                db_extracted = list(
                    db_extractor.extract_all(layers=layer_list, site=site)
                )
            # DBExtractor already yields ExtractedString objects; include them in the pipeline
            app_extracted.extend(db_extracted)
            output.info(f"Extracted {len(db_extracted)} strings from Layers B/C")

            # Additionally extract app UI messages via frappe.translate.get_messages_for_app (legacy behavior)
            try:
                msg_extracted = list(db_extractor.extract_messages_for_app(app_name, site=site))
                if msg_extracted:
                    app_extracted.extend(msg_extracted)
                    output.info(f"Extracted {len(msg_extracted)} strings from app messages (get_messages_for_app)")
            except Exception:
                pass

        # Filter and translate for this app only
        output.info(f"Total extracted for {app_name}: {len(app_extracted)}")

        # Apply policy and filter
        # Deduplicate by source_text (Frappe CSV key) to avoid re-sending duplicates from different files/scopes.
        unique_by_text = {}

        for extracted in app_extracted:
            decision, reason = policy.decide(extracted.text, extracted.context)
            if decision.value == "translate":
                # Check if already translated
                existing_entry = storage.get_entry_by_source(extracted.text)
                if existing_entry and not repair_existing:
                    continue
                if existing_entry and repair_existing:
                    # Only retranslate clearly corrupted existing entries
                    if not _should_repair_existing(extracted.text, existing_entry.translated_text):
                        continue
                # If not present in app translations, also respect frappe core translations
                if not existing_entry and not repair_existing and frappe_storage:
                    if frappe_storage.get(extracted.text):
                        continue
                # Translate missing strings OR ones selected for repair
                if extracted.text not in unique_by_text:
                    unique_by_text[extracted.text] = extracted

        to_translate = list(unique_by_text.values())
        total_to_translate = len(to_translate)
        output.info(f"Strings to translate: {total_to_translate}")

        if total_to_translate == 0:
            output.info(f"No new strings to translate for {app_name}")
            continue

        # Translate
        translation_stats = {
            "translated": 0,
            "failed": 0,
            "skipped": 0,
            "rejected": 0,
        }
        
        if not dry_run:
            # Batch translation for speed: 1 API call per ~50 strings (with safe fallback).
            batch_size = 50
            with ProgressTracker(total=total_to_translate, description=f"Translating {app_name}") as progress:
                for i in range(0, len(to_translate), batch_size):
                    batch_items = to_translate[i : i + batch_size]
                    batch_texts = [x.text for x in batch_items]
                    results = translator.translate_batch(
                        batch_texts,
                        lang,
                        source_lang="en",
                        batch_size=batch_size,
                        context=context,
                    )

                    for extracted, (translated, trans_status) in zip(batch_items, results):
                        if trans_status == "ok" and translated:
                            translation_stats["translated"] += 1
                            storage.set(
                                extracted.text,
                                translated,
                                extracted.context,
                                extracted.source_file,
                                extracted.line_number,
                                update_existing=bool(repair_existing),
                            )
                        elif trans_status == "failed":
                            translation_stats["failed"] += 1
                        elif trans_status == "skipped":
                            translation_stats["skipped"] += 1
                        elif trans_status == "rejected":
                            translation_stats["rejected"] += 1

                        progress.update()

            # Save storage for this app
            storage.save()
            output.success(f"✓ Translations saved to: {storage.csv_path}")
        else:
            output.info("Dry run - no translations saved")
        
        # Store stats for summary
        all_app_stats.append((app_name, translation_stats, app_extracted))

    # Print comprehensive statistics for all apps
    policy_stats = policy.get_stats()
    
    # Aggregate stats from all apps
    total_final_stats = {
        "translated": 0,
        "failed": 0,
        "skipped": 0,
        "rejected": 0,
    }
    
    for app_name, app_stats, app_extracted in all_app_stats:
        for key in total_final_stats:
            total_final_stats[key] += app_stats.get(key, 0)
    
    final_stats = total_final_stats

    # Print summary only after progress bar is done
    console.print()  # Empty line after progress bar
    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]📊 Translation Summary[/bold]")
    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]\n")
    
    console.print("[bold]Policy Decisions:[/bold]")
    console.print(f"  ✓ TRANSLATE: [green]{policy_stats.get('translate', 0)}[/green]")
    console.print(f"  ⊘ SKIP: [yellow]{policy_stats.get('skip', 0)}[/yellow]")
    console.print(f"  ⊘ KEEP_ORIGINAL: [yellow]{policy_stats.get('keep_original', 0)}[/yellow]\n")
    
    console.print("[bold]Translation Results:[/bold]")
    console.print(f"  ✓ Translated: [green]{final_stats.get('translated', 0)}[/green]")
    if final_stats.get('failed', 0) > 0:
        console.print(f"  ✗ Failed: [red]{final_stats.get('failed', 0)}[/red]")
    if final_stats.get('skipped', 0) > 0:
        console.print(f"  ⊘ Skipped: [yellow]{final_stats.get('skipped', 0)}[/yellow]")
    if final_stats.get('rejected', 0) > 0:
        console.print(f"  ⚠ Rejected (validation issues): [yellow]{final_stats.get('rejected', 0)}[/yellow]")
        if verbose:
            output.info("Use --verbose to see details of rejected translations", verbose_only=True)
    
    # Calculate success rate
    total_processed = sum(final_stats.values())
    if total_processed > 0:
        success_rate = (final_stats.get('translated', 0) / total_processed) * 100
        console.print(f"\n  Success Rate: [bold]{success_rate:.1f}%[/bold]")
    
    console.print("\n[bold green]═══════════════════════════════════════════════════════════[/bold green]\n")


def cli_entrypoint():
    """CLI entrypoint for console script."""
    cli()


# Make app callable for direct execution
if __name__ == "__main__":
    cli_entrypoint()
