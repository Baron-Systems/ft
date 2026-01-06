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
ai-translate translate erpnext --lang ar --site mysite
```

### عرض Benches المتاحة

```bash
ai-translate list-benches
```

### مراجعة الترجمات

```bash
ai-translate review erpnext --lang ar
```

### Audit الترجمات

```bash
ai-translate audit erpnext --lang ar
```

## 4. أمثلة سريعة

### مثال كامل

```bash
# 1. ابحث عن benches
ai-translate list-benches

# 2. اترجم التطبيق
ai-translate translate erpnext --lang ar --site mysite

# 3. راجع الترجمات
ai-translate review erpnext --lang ar --context "ERP System"

# 4. تحقق من النتائج
ai-translate audit erpnext --lang ar
```

### مع database content

```bash
ai-translate translate erpnext --lang ar --site mysite --db-scope
```

### DocTypes محددة

```bash
ai-translate translate erpnext --lang ar --site mysite \
  --db-scope --db-doc-types "Workspace,Report"
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
ai-translate audit --help
```

---

**للمزيد من التفاصيل، راجع [USAGE.md](USAGE.md)**

