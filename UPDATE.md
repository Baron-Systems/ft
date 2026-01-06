# كيفية التحديث

## إعادة التثبيت بعد التحديث

⚠️ **ملاحظة:** `pipx reinstall` لا يعمل مع URL مباشرة. استخدم أحد الحلول التالية:

### الحل 1: استخدام install مع --force (الأسهل)

```bash
pipx install --force git+https://github.com/Baron-Systems/ft.git
```

### الحل 2: حذف ثم إعادة التثبيت

```bash
# 1. حذف التثبيت القديم
pipx uninstall ai-translate

# 2. إعادة التثبيت
pipx install git+https://github.com/Baron-Systems/ft.git
```

### الحل 3: استخدام upgrade (إذا كان متاحاً)

```bash
pipx upgrade ai-translate
```

## التحقق من التحديث

بعد إعادة التثبيت، تحقق من:

```bash
# 1. التحقق من الإصدار
ai-translate --version

# 2. التحقق من الأوامر المتاحة
ai-translate --help

# 3. التحقق من أمر translate
ai-translate translate --help
```

## ما الجديد في هذا التحديث؟

### ✨ ميزات جديدة

1. **CLI محسّن** - استخدام click بدلاً من typer
2. **Batch Translation** - ترجمة مجمعة أسرع
3. **Language Memory System** - ذاكرة لغوية تلقائية
4. **Context-Aware Translation** - ترجمة حسب السياق
5. **Enhanced Policy Engine** - محرك قرارات محسّن
6. **Audit System** - نظام مراجعة شامل
7. **Review System** - نظام موافقة/رفض
8. **AST-based Extraction** - استخراج أدق
9. **Caching System** - نظام تخزين مؤقت
10. **Enhanced Gettext** - دعم polib للـ PO files

### 🔄 تغييرات في الأوامر

**قبل التحديث:**
```bash
ai-translate erpnext --lang ar --site mysite
```

**بعد التحديث:**
```bash
ai-translate translate erpnext --lang ar --site mysite
```

### 📝 أوامر جديدة

```bash
# Audit الترجمات (جديد)
ai-translate audit erpnext --lang ar

# Review مع context (محسّن)
ai-translate review erpnext --lang ar --context "ERP System"
```

## خطوات التحديث الكاملة

```bash
# 1. إعادة التثبيت (استخدم --force)
pipx install --force git+https://github.com/Baron-Systems/ft.git

# 2. التحقق من التثبيت
ai-translate --help

# 3. اختبار الأمر الجديد
ai-translate translate erpnext --lang ar --site mysite --dry-run

# 4. إذا كان كل شيء يعمل، ابدأ الاستخدام
ai-translate translate erpnext --lang ar --site mysite
```

## ملاحظات

- ✅ لا حاجة لحذف التثبيت القديم - `--force` سيحدثه تلقائياً
- ✅ الإعدادات والـ API key تبقى كما هي
- ✅ الترجمات الموجودة محفوظة (لا يتم حذفها)
- ⚠️ تذكر استخدام `translate` كـ subcommand الآن

## إذا واجهت مشاكل

```bash
# 1. حذف التثبيت القديم
pipx uninstall ai-translate

# 2. إعادة التثبيت من جديد
pipx install git+https://github.com/Baron-Systems/ft.git

# 3. التحقق من المسار
which ai-translate

# 4. التحقق من الإصدار
ai-translate --version
```

## الملفات الجديدة

بعد التحديث، ستجد ملفات جديدة:

- `apps/<app>/<app>/translations/<lang>_memory.json` - Language Memory
- `.cache/translations/` - Cache files (اختياري)

---

**راجع [COMMANDS.md](COMMANDS.md) للأوامر الجديدة**
