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
ai-translate erpnext --lang ar --site mysite
```

### مراجعة الترجمات

```bash
ai-translate review erpnext --lang ar --context "نظام ERP"
```

## 4. مثال كامل

```bash
# 1. اترجم التطبيق (يضيف الناقص فقط ويحافظ على الموجود)
ai-translate erpnext --lang ar --site mysite

# 2. راجع الترجمات مع وصف للتطبيق لتحسين المعنى
ai-translate review erpnext --lang ar --context "نظام ERP"
```

## 5. مع database content

```bash
ai-translate erpnext --lang ar --site mysite
```

## 6. أين توجد الترجمات؟

```
apps/erpnext/erpnext/translations/ar.csv
```

---

**للمزيد من التفاصيل، راجع [USAGE.md](USAGE.md)**
