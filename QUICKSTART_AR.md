# دليل البدء السريع (Arabic)

## 1) التثبيت

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

## 2) إعداد API Key

```bash
export GROQ_API_KEY="your-api-key-here"
```

## 3) ترجمة (يضيف الناقص فقط ويحافظ على الموجود)

> ملاحظة: إذا كتبت اسم التطبيق مباشرة بعد `ai-translate` فالأداة تعتبره أمر `translate` تلقائياً.

```bash
ai-translate erpnext --lang ar --site site-name
```

إذا لم يتم اكتشاف الـ bench تلقائياً:

```bash
ai-translate erpnext --lang ar --site site-name --bench-path /path/to/bench
```

## 4) مراجعة (تحسين المعنى باستخدام وصف التطبيق)

```bash
ai-translate review erpnext --lang ar --context "نظام ERP لإدارة الموارد"
```

## المساعدة

```bash
ai-translate --help
ai-translate translate --help
ai-translate review --help
```

## الدعم

- راجع `INSTALLATION_FM.md` لمستخدمي Frappe Manager
- راجع `README.md` و `USAGE.md` للتفاصيل

