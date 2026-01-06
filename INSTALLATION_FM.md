# دليل التثبيت لـ Frappe Manager / Installation Guide for Frappe Manager

## بالعربية / In Arabic

### أين يجب تثبيت المشروع؟

**المشروع لا يحتاج أن يكون داخل مجلد bench!** يمكن تثبيته في أي مكان باستخدام `pipx`.

### خطوات التثبيت:

#### 1. تثبيت الأداة (في أي مكان):

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

أو من المصدر:

```bash
git clone https://github.com/Baron-Systems/ft.git
cd ft
pip install -e .
```

#### 2. إعداد مفتاح API:

```bash
export GROQ_API_KEY="your-api-key-here"
```

أو إضافته إلى ملف `~/.bashrc`:

```bash
echo 'export GROQ_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### 3. العثور على مسار Bench في Frappe Manager:

**الأداة تدعم Frappe Manager تلقائياً!** لا تحتاج لتحديد `--bench-path` إذا كنت تستخدم Frappe Manager.

```bash
# عرض جميع benches المتاحة (بما في ذلك Frappe Manager)
ai-translate list-benches

# أو استخدام fm مباشرة
fm bench list
```

#### 4. استخدام الأداة:

**⚠️ مهم:** استخدم `ai-translate` **خارج** `fm shell` لأن PATH داخل `fm shell` قد لا يحتوي على pipx binaries.

```bash
# الطريقة الأولى: استخدام Frappe Manager تلقائياً (موصى بها)
# الأداة ستكتشف bench تلقائياً من fm list
ai-translate \
  --apps frappe \
  --lang ar \
  --site your-site-name

# الطريقة الثانية: تحديد مسار bench يدوياً
ai-translate \
  --bench-path /home/frappe/frappe-bench \
  --apps frappe \
  --lang ar \
  --site your-site-name

# الطريقة الثالثة: الانتقال إلى مجلد bench أولاً
cd /home/frappe/frappe-bench
ai-translate --apps frappe --lang ar --site your-site-name
```

**ملاحظة:** إذا كنت داخل `fm shell` و `ai-translate` غير متاح:
1. اخرج من `fm shell` (اكتب `exit`)
2. استخدم `ai-translate` من shell العادي
3. أو أضف pipx bin directory إلى PATH داخل `fm shell`:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

---

## English

### Where Should the Project Be Installed?

**The project does NOT need to be inside the bench directory!** It can be installed anywhere using `pipx`.

### Installation Steps:

#### 1. Install the Tool (Anywhere):

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

Or from source:

```bash
git clone https://github.com/Baron-Systems/ft.git
cd ft
pip install -e .
```

#### 2. Setup API Key:

```bash
export GROQ_API_KEY="your-api-key-here"
```

Or add it to your `~/.bashrc`:

```bash
echo 'export GROQ_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### 3. Find Bench Path in Frappe Manager:

**The tool now has built-in Frappe Manager support!** You don't need to specify `--bench-path` if using Frappe Manager.

```bash
# List all available benches (including Frappe Manager benches)
ai-translate list-benches

# Or use fm directly
fm bench list
```

#### 4. Use the Tool:

**⚠️ Important:** Use `ai-translate` **outside** `fm shell` because PATH inside `fm shell` may not include pipx binaries.

```bash
# Method 1: Use Frappe Manager automatically (recommended)
# The tool will auto-detect bench from fm list
ai-translate \
  --apps frappe \
  --lang ar \
  --site your-site-name

# Method 2: Specify bench path manually
ai-translate \
  --bench-path /home/frappe/frappe-bench \
  --apps frappe \
  --lang ar \
  --site your-site-name

# Method 3: Navigate to bench directory first
cd /home/frappe/frappe-bench
ai-translate --apps frappe --lang ar --site your-site-name
```

**Note:** If you're inside `fm shell` and `ai-translate` is not found:
1. Exit `fm shell` (type `exit`)
2. Use `ai-translate` from regular shell
3. Or add pipx bin directory to PATH inside `fm shell`:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

## Common Frappe Manager Bench Locations

- `/home/frappe/frappe-bench`
- `/home/frappe/bench-name`
- `/opt/frappe/frappe-bench`
- `~/frappe-bench`

## Example: Full Workflow with Frappe Manager

```bash
# 1. Install tool (anywhere)
pipx install git+https://github.com/Baron-Systems/ft.git

# 2. Set API key
export GROQ_API_KEY="your-key"

# 3. Find your bench path
fm bench list
# Output: frappe-bench-1 -> /home/frappe/frappe-bench-1

# 4. Run translation
ai-translate \
  --bench-path /home/frappe/frappe-bench-1 \
  --all-apps \
  --lang ar \
  --site your-site.localhost \
  --layers A,B,C \
  --verbose
```

## Troubleshooting

### Cannot Find Bench Directory

Use `--bench-path` explicitly:

```bash
ai-translate --bench-path /path/to/your/bench --apps frappe --lang ar --site site-name
```

To find your bench path from Frappe Manager:

```bash
# List sites and extract bench path
fm list
# Look for Path column - bench is usually parent of sites directory
# Example: /home/baron/frappe/sites/site-name -> bench is /home/baron/frappe-bench
```

### Verify Bench Path

Check if the path contains `sites` and `apps` directories:

```bash
ls /path/to/bench/sites
ls /path/to/bench/apps
```

If both directories exist, the path is correct.

### Command Not Found Inside fm shell

If `ai-translate` is not found inside `fm shell`:

1. **Exit fm shell and use regular shell** (recommended):
   ```bash
   exit  # Exit fm shell
   ai-translate --apps frappe --lang ar --site site-name
   ```

2. **Or add pipx to PATH inside fm shell**:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ai-translate --apps frappe --lang ar --site site-name
   ```

