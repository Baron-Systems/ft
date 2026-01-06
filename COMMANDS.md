# أوامر الأداة (مختصرة ونظيفة)

هدف الأداة: **ترجمة الناقص فقط** في ملف `apps/<app>/<app>/translations/<lang>.csv` بدون حذف الموجود.

## 1) الترجمة (Translate)

> يمكنك كتابة اسم التطبيق مباشرة بعد `ai-translate` وسيُعتبر تلقائياً أمر `translate`.

```bash
ai-translate erpnext --lang ar --site mysite
```

مع وصف للتطبيق لتحسين الترجمة حسب المعنى:

```bash
ai-translate erpnext --lang ar --site mysite --context "نظام ERP لإدارة الموارد"
```

إن لم يتم اكتشاف الـ bench تلقائياً:

```bash
ai-translate erpnext --lang ar --site mysite --bench-path /path/to/bench
```

## 2) المراجعة (Review)

```bash
ai-translate review erpnext --lang ar --context "نظام ERP"
```

## المساعدة

```bash
ai-translate --help
ai-translate translate --help
ai-translate review --help
```

