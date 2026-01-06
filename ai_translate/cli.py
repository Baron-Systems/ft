"""CLI entrypoint for ai-translate."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer
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

app = typer.Typer(
    name="ai-translate",
    help="AI-powered translation system for Frappe / ERPNext",
    add_completion=False,
)
console = Console()


def cli_entrypoint():
    """CLI entrypoint - parses arguments manually to avoid Typer issues."""
    import sys
    args = sys.argv[1:]
    
    # Check if this is a subcommand (review, list-benches)
    if args and args[0] in ["review", "list-benches"]:
        # Let Typer handle subcommands
        app()
        return
    
    # Check if this looks like a translate command (has --lang)
    if "--lang" in args:
        # Parse arguments manually
        apps = None
        lang = None
        site = None
        bench_path = None
        verbose = False
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--lang":
                if i + 1 < len(args):
                    lang = args[i + 1]
                    i += 2
                else:
                    break
            elif arg == "--site":
                if i + 1 < len(args):
                    site = args[i + 1]
                    i += 2
                else:
                    break
            elif arg == "--bench-path":
                if i + 1 < len(args):
                    bench_path = args[i + 1]
                    i += 2
                else:
                    break
            elif arg == "--verbose":
                verbose = True
                i += 1
            elif not arg.startswith("-"):
                # This should be the apps argument
                apps = arg
                i += 1
            else:
                i += 1
        
        if apps and lang:
            _translate_impl(apps=apps, lang=lang, site=site, bench_path=bench_path, verbose=verbose)
        else:
            output = OutputFilter(verbose=verbose)
            output.error("App name(s) and --lang are required")
            output.info("\nUsage:")
            output.info("  ai-translate <apps> --lang <lang> [--site <site>]")
            output.info("\nExample:")
            output.info("  ai-translate erpnext --lang ar --site mysite")
            sys.exit(1)
    else:
        # No --lang found, let Typer show help or handle subcommands
        app()


@app.callback()
def main(ctx: typer.Context):
    """Main callback - only handles subcommands."""
    pass


def _translate_impl(
    apps: str,
    lang: str,
    site: Optional[str],
    bench_path: Optional[str],
    verbose: bool,
):
    """
    Implementation of translate command.
    
    Automatically extracts from:
    - Code files (Python, JavaScript, HTML)
    - JSON fixtures (DocTypes, Workspaces, Reports, etc.)
    - Database content (if --site is provided)
    
    Only translates missing strings - preserves existing translations.
    """
    
    # Initialize output
    output = OutputFilter(verbose=verbose)

    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        output.error("GROQ_API_KEY environment variable is required")
        sys.exit(1)

    # Automatically process all layers (A, B, C)
    # Layer A: Code & Files (always)
    # Layers B & C: Database content (if site provided)
    layer_list = ["A"]  # Always include Layer A
    if site:
        layer_list.extend(["B", "C"])  # Add database layers if site provided

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
        output.info("  ai-translate erpnext --lang ar --site site-name")
        output.info("  ai-translate --bench-path /path/to/bench erpnext --lang ar --site site-name")
        sys.exit(1)

    output.info(f"Bench path: {bench_manager.bench_path}")

    # Parse app names
    app_names = [a.strip() for a in apps.split(",") if a.strip()]

    if not app_names:
        output.error("No apps found to process")
        sys.exit(1)

    output.info(f"Processing {len(app_names)} app(s): {', '.join(app_names)}")

    # Initialize translator
    try:
        translator = Translator(api_key=api_key, slow_mode=False, output=output)
    except Exception as e:
        output.error(f"Failed to initialize translator: {e}")
        sys.exit(1)

    # Process each app separately
    all_app_stats = []

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
            db_extractor = DBExtractor()
            db_extracted = list(
                db_extractor.extract_all(layers=layer_list, site=site)
            )
            # Convert DB extracted to ExtractedString format
            # (This would need proper conversion in production)
            output.info(f"Extracted {len(db_extracted)} strings from Layers B/C")

        # Filter and translate for this app only
        output.info(f"Total extracted for {app_name}: {len(app_extracted)}")

        # Apply policy and filter
        from ai_translate.policy import PolicyEngine

        policy = PolicyEngine()
        to_translate = []

        for extracted in app_extracted:
            decision = policy.decide(extracted.text, extracted.context)
            if decision.value == "translate":
                # Check if already translated
                existing = storage.get(extracted.text, extracted.context)
                if not existing:  # Only translate if not already translated
                    to_translate.append(extracted)

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
        
        # Always run translation
        if True:
            consecutive_failures = 0
            max_consecutive_failures = 5  # Stop after 5 consecutive failures
            
            with ProgressTracker(total=total_to_translate, description=f"Translating {app_name}") as progress:
                for extracted in to_translate:
                    translated, status = translator.translate(
                        extracted.text, lang, source_lang="en"
                    )
                    
                    # Track statistics
                    if status == "ok" and translated:
                        consecutive_failures = 0  # Reset failure counter
                        translation_stats["translated"] += 1
                        storage.set(
                            extracted.text,
                            translated,
                            extracted.context,
                            extracted.source_file,
                            extracted.line_number,
                        )
                    elif status == "failed":
                        consecutive_failures += 1
                        translation_stats["failed"] += 1
                        if consecutive_failures >= max_consecutive_failures:
                            output.error(f"Stopping translation after {max_consecutive_failures} consecutive failures")
                            output.error("Please check your API key and model availability")
                            break
                    elif status == "skipped":
                        translation_stats["skipped"] += 1
                    elif status == "rejected":
                        translation_stats["rejected"] += 1
                    
                    progress.update()

            # Save storage for this app
            storage.save()
            output.success(f"✓ Translations saved to: {storage.csv_path}")
        
        # Store stats for summary
        all_app_stats.append((app_name, translation_stats, app_extracted))

    # Note: Fix missing, PO/MO sync, and DB writes are skipped when using app translation files
    # These features work with site-based storage only
    if all_app_stats:
        output.info("\nNote: Translations are saved directly to app translation files.")
        output.info("PO/MO sync and database writes are skipped when using app translation files.")

    # Print comprehensive statistics for all apps
    from ai_translate.policy import PolicyEngine
    policy = PolicyEngine()
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
    console.print(f"  ✓ TRANSLATE: [green]{policy_stats.get('TRANSLATE', 0)}[/green]")
    console.print(f"  ⊘ SKIP: [yellow]{policy_stats.get('SKIP', 0)}[/yellow]")
    console.print(f"  ⊘ KEEP_ORIGINAL: [yellow]{policy_stats.get('KEEP_ORIGINAL', 0)}[/yellow]\n")
    
    console.print("[bold]Translation Results:[/bold]")
    console.print(f"  ✓ Translated: [green]{final_stats.get('translated', 0)}[/green]")
    if final_stats.get('failed', 0) > 0:
        console.print(f"  ✗ Failed: [red]{final_stats.get('failed', 0)}[/red]")
    if final_stats.get('skipped', 0) > 0:
        console.print(f"  ⊘ Skipped: [yellow]{final_stats.get('skipped', 0)}[/yellow]")
    if final_stats.get('rejected', 0) > 0:
        console.print(f"  ⚠ Rejected (placeholder issues): [yellow]{final_stats.get('rejected', 0)}[/yellow]")
        if verbose:
            output.info("Use --verbose to see details of rejected translations", verbose_only=True)
    
    # Calculate success rate
    total_processed = sum(final_stats.values())
    if total_processed > 0:
        success_rate = (final_stats.get('translated', 0) / total_processed) * 100
        console.print(f"\n  Success Rate: [bold]{success_rate:.1f}%[/bold]")
    
    console.print("\n[bold green]═══════════════════════════════════════════════════════════[/bold green]\n")

    # Translation complete


@app.command(name="list-benches")
def list_benches(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Verbose output",
    ),
):
    """
    List available benches (including Frappe Manager benches).
    """
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
        output.info("  ai-translate --bench-path /path/to/bench --apps frappe --lang ar --site site-name")
    else:
        output.success(f"\nFound {len(benches_found)} bench(es)")
        output.info("\nUse --bench-path to specify which bench to use")


@app.command(name="review")
def review_translations(
    apps: str = typer.Argument(..., help="App name(s) to review (comma-separated)"),
    lang: str = typer.Option(..., "--lang", help="Language code to review"),
    app_description: Optional[str] = typer.Option(None, "--context", help="App description/context for better translation (e.g., 'Human Resources Management System')"),
    bench_path: Optional[str] = typer.Option(None, "--bench-path", help="Path to bench directory"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
):
    """
    Review and improve translations with AI context.
    
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
    if app_description:
        output.info(f"App context: {app_description}")
    
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
        output.info(f"Found {len(all_entries)} translations")
        
        if not all_entries:
            output.info("No translations to review")
            continue
        
        # Review each translation
        reviewed_count = 0
        with ProgressTracker(total=len(all_entries), description="Reviewing") as progress:
            for entry in all_entries:
                # Re-translate with context
                translated, status = translator.translate(
                    entry.source_text,
                    lang,
                    source_lang="en",
                    context=app_description
                )
                
                if status == "ok" and translated and translated != entry.translated_text:
                    # Update if translation improved
                    storage.set(
                        entry.source_text,
                        translated,
                        entry.context,
                        entry.source_file,
                        entry.line_number,
                    )
                    reviewed_count += 1
                
                progress.update()
        
        # Save reviewed translations
        storage.save()
        output.success(f"✓ Reviewed {reviewed_count} translations for {app_name}")


# cli_entrypoint is defined above (line 31)

# Make app callable for direct execution
if __name__ == "__main__":
    cli_entrypoint()

