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
- Use `ai-translate list-benches` to see all available benches

See [INSTALLATION_FM.md](INSTALLATION_FM.md) for detailed instructions.

## Requirements

- Python >= 3.10
- Frappe / ERPNext bench setup
- `GROQ_API_KEY` environment variable (required)

## Usage

### Basic Usage

Translate a specific app:

```bash
export GROQ_API_KEY="your-api-key-here"
ai-translate --apps frappe --lang es --site your-site-name
```

### Process All Apps

```bash
ai-translate --all-apps --lang fr --site your-site-name
```

### Process Specific Layers

```bash
# Layer A only (Code & Files)
ai-translate --apps frappe --lang de --layers A

# Layers B & C (Database)
ai-translate --apps frappe --lang es --site your-site-name --layers B,C
```

### Dry Run

Preview what would be translated without making changes:

```bash
ai-translate --apps frappe --lang es --site your-site-name --dry-run
```

### Fix Missing Translations

```bash
ai-translate --apps frappe --lang es --site your-site-name --fix-missing
```

### Update Existing Translations

```bash
ai-translate --apps frappe --lang es --site your-site-name --update-existing
```

### Slow Mode (Rate Limiting)

```bash
ai-translate --apps frappe --lang es --site your-site-name --slow-mode
```

### Verbose Output

```bash
ai-translate --apps frappe --lang es --site your-site-name --verbose
```

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

- CSV: `sites/<site>/translations/<lang>.csv`
- PO: `sites/<site>/assets/locale/<lang>/LC_MESSAGES/<lang>.po`
- MO: `sites/<site>/assets/locale/<lang>/LC_MESSAGES/<lang>.mo`

## Database Writes

The tool writes **only** to the Translation DocType. Original records are never modified.

## CLI Options

```
--apps              Comma-separated list of app names
--all-apps          Process all apps
--lang              Target language code (required)
--site              Site name (required for Layers B & C)
--layers            Comma-separated layers (A, B, C) [default: A]
--fix-missing       Fix missing translations
--dry-run           Dry run mode (no writes)
--slow-mode         Enable slow mode (rate limiting)
--update-existing   Update existing translations
--verbose           Verbose output
--bench-path        Path to bench directory
```

## Examples

### Translate ERPNext to Spanish

```bash
ai-translate --all-apps --lang es --site production --layers A,B,C
```

### Preview French Translation

```bash
ai-translate --apps erpnext --lang fr --site production --dry-run --verbose
```

### Fix Missing German Translations

```bash
ai-translate --apps frappe --lang de --site production --fix-missing
```

## Development

### Project Structure

```
ai_translate/
├── cli.py               CLI entrypoint
├── policy.py            Policy Engine
├── extractors.py        Code & JSON extraction
├── translator.py        Groq API integration
├── storage.py           CSV / translation storage
├── manager.py           Frappe app & bench utilities
├── fixers.py            Missing / duplicate repair
├── db_scope.py          Safe DB extraction (Layers B & C)
├── db_write.py          Non-destructive DB write
├── gettext_sync.py      PO/MO sync & compilation
├── output.py            Filtered stdout / logging
└── progress.py          Progress bar + ETA
```

## License

MIT

## Support

For issues and contributions, please visit: https://github.com/Baron-Systems/ft

