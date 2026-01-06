# دليل البدء السريع - العربية

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

## 4. مثال كامل

```bash
# 1. ابحث عن benches
ai-translate list-benches

# 2. اترجم التطبيق
ai-translate translate erpnext --lang ar --site mysite

# 3. راجع الترجمات
ai-translate review erpnext --lang ar --context "نظام ERP"

# 4. تحقق من النتائج
ai-translate audit erpnext --lang ar
```

## 5. مع database content

```bash
ai-translate translate erpnext --lang ar --site mysite --db-scope
```

## 6. أين توجد الترجمات؟

```
apps/erpnext/erpnext/translations/ar.csv
```

---

**للمزيد من التفاصيل، راجع [USAGE.md](USAGE.md)**
