# دليل البدء السريع - Quick Start Guide (Arabic)

## التثبيت السريع / Quick Installation

```bash
# 1. تثبيت الأداة (في أي مكان)
pipx install git+https://github.com/Baron-Systems/ft.git

# 2. إعداد مفتاح API
export GROQ_API_KEY="your-api-key-here"

# 3. استخدام الأداة
# مع Frappe Manager (لا حاجة لـ --bench-path):
ai-translate --apps frappe --lang ar --site site-name

# أو بدون Frappe Manager:
ai-translate --bench-path /path/to/bench --apps frappe --lang ar --site site-name
```

## مثال كامل / Full Example

```bash
# تثبيت
pipx install git+https://github.com/Baron-Systems/ft.git

# إعداد API Key
export GROQ_API_KEY="gsk_xxxxxxxxxxxxx"

# العثور على bench (إذا كنت تستخدم Frappe Manager)
# الأداة تدعم Frappe Manager تلقائياً!
ai-translate list-benches
# أو
fm list

# تشغيل الترجمة (مع Frappe Manager - لا حاجة لـ --bench-path)
ai-translate \
  --all-apps \
  --lang ar \
  --site your-site.localhost \
  --layers A,B,C \
  --verbose

# أو تحديد bench يدوياً
ai-translate \
  --bench-path /home/frappe/frappe-bench \
  --all-apps \
  --lang ar \
  --site your-site.localhost \
  --layers A,B,C \
  --verbose
```

## دعم Frappe Manager / Frappe Manager Support

الأداة تدعم **Frappe Manager (fm)** تلقائياً:

- ✅ اكتشاف تلقائي لـ benches من `fm list`
- ✅ لا حاجة لتحديد `--bench-path` عند استخدام Frappe Manager
- ✅ استخدم `ai-translate list-benches` لعرض جميع benches المتاحة

**⚠️ مهم:** استخدم `ai-translate` **خارج** `fm shell` لأن PATH داخل `fm shell` قد لا يحتوي على pipx binaries.

إذا كنت داخل `fm shell`:
```bash
exit  # اخرج من fm shell
ai-translate --apps frappe --lang ar --site site-name
```

## ملاحظات مهمة / Important Notes

1. **لا تحتاج تثبيت المشروع داخل bench** - يمكن تثبيته في أي مكان
2. **مع Frappe Manager**: لا حاجة لـ `--bench-path` - الأداة تكتشف تلقائياً
3. **بدون Frappe Manager**: استخدم `--bench-path` لتحديد موقع bench
4. **الترجمة للطبقة A فقط** لا تحتاج `--site`
5. **الترجمة للطبقات B و C** تحتاج `--site`

## الخيارات الأساسية / Basic Options

```bash
--apps              # قائمة التطبيقات (مثال: frappe,erpnext)
--all-apps          # جميع التطبيقات
--lang              # اللغة المستهدفة (ar, en, es, fr, ...)
--site              # اسم الموقع (مطلوب للطبقات B و C)
--layers            # الطبقات (A, B, C) - افتراضي: A
--bench-path        # مسار bench (مثال: /home/frappe/frappe-bench)
--dry-run           # تجربة بدون كتابة
--verbose           # عرض تفاصيل أكثر
```

## أمثلة / Examples

### ترجمة تطبيق واحد
```bash
ai-translate --bench-path /home/frappe/frappe-bench --apps frappe --lang ar
```

### ترجمة جميع التطبيقات
```bash
ai-translate --bench-path /home/frappe/frappe-bench --all-apps --lang ar --site site-name
```

### تجربة بدون تغييرات (Dry Run)
```bash
ai-translate --bench-path /home/frappe/frappe-bench --apps frappe --lang ar --site site-name --dry-run --verbose
```

### إصلاح الترجمات الناقصة
```bash
ai-translate --bench-path /home/frappe/frappe-bench --apps frappe --lang ar --site site-name --fix-missing
```

## المساعدة / Help

```bash
ai-translate --help
```

## الدعم / Support

للمزيد من التفاصيل، راجع:
- [INSTALLATION_FM.md](INSTALLATION_FM.md) - دليل التثبيت لـ Frappe Manager
- [README.md](README.md) - الوثائق الكاملة

