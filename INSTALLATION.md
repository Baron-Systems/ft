# Installation Guide

## Prerequisites

- Python >= 3.10
- pipx (recommended) or pip
- Frappe / ERPNext bench setup
- Groq API key

## Installation via pipx (Recommended)

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

This will:
- Create an isolated virtual environment
- Install the `ai-translate` command globally
- Make it available in your PATH

## Installation from Source

```bash
git clone https://github.com/Baron-Systems/ft.git
cd ft
pip install -e .
```

## Verify Installation

```bash
ai-translate --help
```

You should see the help output with all available options.

## Setup

1. **Set your Groq API key:**

```bash
export GROQ_API_KEY="your-api-key-here"
```

Or add it to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
echo 'export GROQ_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

2. **Navigate to your Frappe bench directory** (or use `--bench-path`):

```bash
cd /path/to/your/bench
```

## Usage Example

```bash
# Translate frappe app to Spanish
ai-translate --apps frappe --lang es --site your-site-name

# Dry run to preview
ai-translate --apps frappe --lang es --site your-site-name --dry-run --verbose

# Process all apps
ai-translate --all-apps --lang fr --site your-site-name
```

## Troubleshooting

### Command not found

If `ai-translate` is not found after installation:

1. Ensure pipx bin directory is in your PATH:
   ```bash
   echo $PATH | grep -q "$HOME/.local/bin" || export PATH="$HOME/.local/bin:$PATH"
   ```

2. Or use pipx's run command:
   ```bash
   pipx run ai-translate --help
   ```

### API Key Issues

Ensure `GROQ_API_KEY` is set:
```bash
echo $GROQ_API_KEY
```

If empty, set it as described above.

### Bench Directory Not Found

Use `--bench-path` to specify the bench directory:
```bash
ai-translate --bench-path /path/to/bench --apps frappe --lang es --site your-site-name
```

