# AI Translate

AI-powered translation system for Frappe / ERPNext.

## Installation

**Note:** The tool does NOT need to be installed inside your bench directory. Install it globally, then use `--bench-path` to point to your bench.

### Install via pipx (Recommended):

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

### Install from source:

```bash
git clone https://github.com/Baron-Systems/ft.git
cd ft
pip install -e .
```

### For Frappe Manager Users:

The tool now has **built-in support for Frappe Manager (fm)**:

- Automatically detects benches via `fm bench list`
- No need to specify `--bench-path` if using Frappe Manager
- If auto-detection fails, pass `--bench-path /path/to/bench`

See [INSTALLATION_FM.md](INSTALLATION_FM.md) for detailed instructions.

## Requirements

- Python >= 3.10
- Frappe / ERPNext bench setup
- `GROQ_API_KEY` environment variable (required)

## Usage

**See [USAGE.md](USAGE.md) for comprehensive usage guide.**

### Quick Start

```bash
# 1. Set API key
export GROQ_API_KEY="your-api-key-here"

# 2. Translate (adds missing only, preserves existing ar.csv)
ai-translate erpnext --lang ar --site your-site-name

# 3. Review translations with app context (meaning-based, not literal)
ai-translate review erpnext --lang ar --context "Enterprise Resource Planning (ERP) System"
```

### Basic Commands

#### Translate

```bash
# Basic translation (shorthand defaults to `translate`)
ai-translate erpnext --lang ar --site mysite

# With app context (improves meaning-based translations)
ai-translate erpnext --lang ar --site mysite --context "ERP System"
```

#### Review

```bash
# Review all translations
ai-translate review erpnext --lang ar

# Review with context
ai-translate review erpnext --lang ar --context "ERP System"
```

### Options

- `--lang, -l`: Target language code (required)
- `--site, -s`: Site name (required for database layers)
- `--context, -c`: App description/context for better translations
- `--bench-path, -b`: Path to bench directory
- `--verbose, -v`: Verbose output
- `--dry-run`: Preview without making changes

## Architecture

### Layers

- **Layer A**: Code & Files
  - Python: `__()`, `_()`, `_lt()`
  - JavaScript: `frappe._()`, `__()`
  - Jinja/HTML: `{{ _("...") }}`
  - Vue templates
  - JSON fixtures (DocTypes, Workspaces, Reports, etc.)

- **Layer B**: UI Metadata (Database)
  - Workspace
  - Report
  - Dashboard
  - Dashboard Chart
  - Number Card

- **Layer C**: User Content (Database)
  - Web Page
  - Blog Post
  - Email Template
  - Print Format
  - Notification

### Policy Engine

The policy engine makes context-aware decisions:

- **TRANSLATE**: User-facing text that should be translated
- **SKIP**: Empty, numbers-only, or constants
- **KEEP_ORIGINAL**: URLs, emails, code identifiers, SQL keywords

### Safety Rules

- URLs and emails are never translated
- Code-like strings are preserved
- SQL keywords are kept original
- Identifiers (route, api_key, name) are preserved
- Placeholders are validated and preserved

## Translation Storage

Translations are stored in:

- **CSV**: `apps/<app>/<app>/translations/<lang>.csv` (Frappe standard)
- **Language Memory**: `apps/<app>/<app>/translations/<lang>_memory.json`
- **PO**: `sites/<site>/assets/locale/<lang>/LC_MESSAGES/<lang>.po` (optional)
- **MO**: `sites/<site>/assets/locale/<lang>/LC_MESSAGES/<lang>.mo` (optional)

## Database Writes

The tool writes **only** to the Translation DocType. Original records are never modified.

## Features

### Language Memory System
- Automatic terminology extraction
- Style profile detection
- Context-aware translation
- Accumulative memory per language

### Context-Aware Translation
- Layer A: Code & Files (conservative)
- Layer B: UI Metadata (user-facing)
- Layer C: User Content (full translation)

### Safety Features
- Policy Engine with rejection reasons
- Placeholder validation
- Identifier detection
- Logic-bearing content protection

### Performance
- Batch translation (20-50 texts per batch)
- Caching system (disk-based)
- AST-based extraction (faster, more accurate)
- Fallback mechanisms

### Audit & Review
- Review system with approval/rejection
- Confidence tracking
- Needs review flagging

## Examples

### Translate ERPNext to Arabic

```bash
ai-translate erpnext --lang ar --site production
```

### Review Translations

```bash
ai-translate review erpnext --lang ar --context "ERP System"
```

## Development

### Project Structure

```
ai_translate/
├── cli.py                  CLI entrypoint (click-based)
├── policy.py               Policy Engine with rejection reasons
├── extractors.py           AST-based code & JSON extraction
├── translator.py           Groq API integration with batching
├── storage.py              CSV / translation storage
├── manager.py              Frappe app & bench utilities
├── fixers.py               Missing / duplicate repair
├── db_scope.py             Safe DB extraction (Layers B & C)
├── db_write.py             Non-destructive DB write
├── gettext_sync.py         PO/MO sync & compilation (polib-based)
├── output.py               Filtered stdout / logging
├── progress.py             Progress bar + ETA
├── language_memory.py      Language Memory System
├── context_profile.py      Context Profile Builder
├── translation_contract.py Translation Contract Builder
├── audit.py                Translation Auditor
├── review.py               Review Manager
└── cache.py                Caching System
```

## License

MIT

## Support

For issues and contributions, please visit: https://github.com/Baron-Systems/ft

