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
from ai_translate.storage import TranslationStorage
from ai_translate.translator import Translator

app = typer.Typer(
    name="ai-translate",
    help="AI-powered translation system for Frappe / ERPNext",
    add_completion=False,
)
console = Console()


@app.command()
def main(
    apps: Optional[str] = typer.Option(
        None,
        "--apps",
        help="Comma-separated list of app names",
    ),
    all_apps: bool = typer.Option(
        False,
        "--all-apps",
        help="Process all apps",
    ),
    lang: str = typer.Option(
        ...,
        "--lang",
        help="Target language code (e.g., 'es', 'fr', 'de')",
    ),
    site: Optional[str] = typer.Option(
        None,
        "--site",
        help="Site name (required for Layers B & C)",
    ),
    layers: Optional[str] = typer.Option(
        "A",
        "--layers",
        help="Comma-separated layers to process (A, B, C)",
    ),
    fix_missing: bool = typer.Option(
        False,
        "--fix-missing",
        help="Fix missing translations",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Dry run mode (no writes)",
    ),
    slow_mode: bool = typer.Option(
        False,
        "--slow-mode",
        help="Enable slow mode (rate limiting)",
    ),
    update_existing: bool = typer.Option(
        False,
        "--update-existing",
        help="Update existing translations",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Verbose output",
    ),
    bench_path: Optional[str] = typer.Option(
        None,
        "--bench-path",
        help="Path to bench directory",
    ),
):
    """
    AI-powered translation system for Frappe / ERPNext.

    Requires GROQ_API_KEY environment variable.
    """
    # Initialize output
    output = OutputFilter(verbose=verbose)

    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        output.error("GROQ_API_KEY environment variable is required")
        sys.exit(1)

    # Parse layers
    layer_list = [l.strip().upper() for l in layers.split(",") if l.strip()]
    if not layer_list:
        output.error("At least one layer must be specified")
        sys.exit(1)

    # Validate layers
    valid_layers = {"A", "B", "C"}
    invalid_layers = set(layer_list) - valid_layers
    if invalid_layers:
        output.error(f"Invalid layers: {invalid_layers}")
        sys.exit(1)

    # Check site requirement for Layers B & C
    if ({"B", "C"} & set(layer_list)) and not site:
        output.error("--site is required for Layers B & C")
        sys.exit(1)

    # Initialize bench manager
    bench_manager = BenchManager(bench_path=bench_path, output=output)
    if not bench_manager.bench_path:
        output.error("Could not find bench directory")
        output.info("")
        output.info("Tips:")
        output.info("  1. Use --bench-path to specify the bench directory explicitly")
        output.info("  2. If using Frappe Manager, run: fm bench list")
        output.info("  3. Navigate to the bench directory and run the command from there")
        output.info("")
        output.info("Example:")
        output.info("  ai-translate --bench-path /path/to/bench --apps frappe --lang ar --site site-name")
        sys.exit(1)

    output.info(f"Bench path: {bench_manager.bench_path}")

    # Get apps to process
    app_names = []
    if all_apps:
        app_names = bench_manager.get_apps(all_apps=True)
    elif apps:
        app_names = bench_manager.get_apps(app_names=apps.split(","))
    else:
        output.error("Either --apps or --all-apps must be specified")
        sys.exit(1)

    if not app_names:
        output.error("No apps found to process")
        sys.exit(1)

    output.info(f"Processing {len(app_names)} app(s): {', '.join(app_names)}")

    # Initialize translator
    try:
        translator = Translator(
            api_key=api_key, slow_mode=slow_mode, output=output
        )
    except Exception as e:
        output.error(f"Failed to initialize translator: {e}")
        sys.exit(1)

    # Initialize storage
    storage_path = bench_manager.bench_path / "sites" / (site or "default")
    storage = TranslationStorage(storage_path=storage_path, lang=lang)

    # Process each app
    all_extracted = []
    total_to_translate = 0

    for app_name in app_names:
        app_path = bench_manager.get_app_path(app_name)
        if not app_path:
            output.warning(f"App path not found: {app_name}")
            continue

        output.info(f"Processing app: {app_name}")

        # Layer A: Code & Files
        if "A" in layer_list:
            extractor = LayerAExtractor(app_name=app_name, app_path=app_path)
            extracted = list(extractor.extract_all())
            all_extracted.extend(extracted)
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

    # Filter and translate
    output.info(f"Total extracted: {len(all_extracted)}")

    # Apply policy and filter
    from ai_translate.policy import PolicyEngine

    policy = PolicyEngine()
    to_translate = []

    for extracted in all_extracted:
        decision = policy.decide(extracted.text, extracted.context)
        if decision.value == "translate":
            # Check if already translated
            existing = storage.get(extracted.text, extracted.context)
            if not existing or update_existing:
                to_translate.append(extracted)

    total_to_translate = len(to_translate)
    output.info(f"Strings to translate: {total_to_translate}")

    if total_to_translate == 0:
        output.info("No strings to translate")
        if dry_run:
            output.info("Dry run complete")
        return

    # Translate
    if not dry_run:
        with ProgressTracker(total=total_to_translate, description="Translating") as progress:
            for extracted in to_translate:
                translated, status = translator.translate(
                    extracted.text, lang, source_lang="en"
                )
                if status == "ok" and translated:
                    storage.set(
                        extracted.text,
                        translated,
                        extracted.context,
                        extracted.source_file,
                        extracted.line_number,
                    )
                progress.update()

        # Save storage
        storage.save()
        output.success("Translations saved to CSV")

    # Fix missing if requested
    if fix_missing:
        fixer = TranslationFixer(storage, output)
        missing = fixer.find_missing([e.text for e in all_extracted])
        if missing:
            output.info(f"Found {len(missing)} missing translations")
            if not dry_run:
                # Translate missing
                for text in missing:
                    translated, status = translator.translate(text, lang)
                    if status == "ok" and translated:
                        from ai_translate.policy import TranslationContext
                        context = TranslationContext(layer="A")
                        storage.set(text, translated, context)
                storage.save()

    # Sync to PO/MO
    if site:
        locale_path = bench_manager.get_locale_path(site, lang)
        if locale_path:
            gettext_sync = GettextSync(storage, locale_path, output)
            gettext_sync.sync_csv_to_po(dry_run=dry_run)
            if not dry_run:
                gettext_sync.compile_mo(dry_run=dry_run)

    # Write to database
    if site and not dry_run:
        db_writer = TranslationDBWriter(
            site=site, update_existing=update_existing, output=output
        )
        entries = [
            TranslationEntry(
                source_text=e.text,
                translated_text=storage.get(e.text, e.context) or e.text,
                context=e.context,
            )
            for e in all_extracted
            if storage.get(e.text, e.context)
        ]
        db_writer.write_batch(entries, dry_run=dry_run)
        db_stats = db_writer.get_stats()
        output.info(f"Database writes: {db_stats}")

    # Print statistics
    policy_stats = policy.get_stats()
    trans_stats = translator.get_stats()

    console.print("\n[bold]Translation Statistics:[/bold]")
    console.print(f"  Policy Decisions:")
    console.print(f"    TRANSLATE: {policy_stats.get('TRANSLATE', 0)}")
    console.print(f"    SKIP: {policy_stats.get('SKIP', 0)}")
    console.print(f"    KEEP_ORIGINAL: {policy_stats.get('KEEP_ORIGINAL', 0)}")
    console.print(f"  Translation Results:")
    console.print(f"    Translated: {trans_stats.get('translated', 0)}")
    console.print(f"    Failed: {trans_stats.get('failed', 0)}")
    console.print(f"    Skipped: {trans_stats.get('skipped', 0)}")
    console.print(f"    Rejected: {trans_stats.get('rejected', 0)}")

    if dry_run:
        output.info("Dry run complete - no changes made")


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
                    # Try to find bench directory
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


def cli_entrypoint():
    """CLI entrypoint for console script."""
    app()


# Make app callable for direct execution
if __name__ == "__main__":
    cli_entrypoint()

