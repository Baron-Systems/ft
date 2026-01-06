# دليل البدء السريع

## 1. التثبيت

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

## 2. إعداد API Key

```bash
export GROQ_API_KEY="your-api-key-here"
```

## 3. الاستخدام الأساسي

### ترجمة تطبيق

```bash
ai-translate erpnext --lang ar --site mysite
```

### مراجعة الترجمات

```bash
ai-translate review erpnext --lang ar --context "ERP System"
```

## 4. أمثلة سريعة

### مثال كامل

```bash
# 1. اترجم التطبيق (يضيف الناقص فقط ويحافظ على الموجود)
ai-translate erpnext --lang ar --site mysite

# 2. راجع الترجمات مع وصف للتطبيق لتحسين المعنى
ai-translate review erpnext --lang ar --context "ERP System"
```

### مع database content

```bash
ai-translate erpnext --lang ar --site mysite
```

## 5. أين توجد الترجمات؟

```
apps/erpnext/erpnext/translations/ar.csv
```

## 6. Flags مختصرة

```bash
# -l بدلاً من --lang
ai-translate translate erpnext -l ar -s mysite

# -v بدلاً من --verbose
ai-translate translate erpnext -l ar -v

# -b بدلاً من --bench-path
ai-translate translate erpnext -l ar -b /path/to/bench
```

## 7. المساعدة

```bash
ai-translate --help
ai-translate translate --help
ai-translate review --help
```

---

**للمزيد من التفاصيل، راجع [USAGE.md](USAGE.md)**

