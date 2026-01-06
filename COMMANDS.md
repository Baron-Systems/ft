# الأوامر بعد التحديث

## ⚠️ تغيير مهم: الأوامر الجديدة

بعد التحديث، تم تغيير بنية الأوامر. الآن يجب استخدام **subcommands** بدلاً من flags مباشرة.

## الأوامر الجديدة

### 1. ترجمة تطبيق

**قبل التحديث (لا يعمل الآن):**
```bash
ai-translate erpnext --lang ar --site mysite
```

**بعد التحديث (الصحيح):**
```bash
ai-translate translate erpnext --lang ar --site mysite
```

### 2. عرض Benches

**قبل التحديث:**
```bash
ai-translate list-benches
```

**بعد التحديث (نفس الأمر):**
```bash
ai-translate list-benches
```

### 3. مراجعة الترجمات

**قبل التحديث:**
```bash
ai-translate review erpnext --lang ar
```

**بعد التحديث (نفس الأمر):**
```bash
ai-translate review erpnext --lang ar
```

### 4. Audit الترجمات

**قبل التحديث (غير موجود):**
```bash
# لم يكن موجوداً
```

**بعد التحديث (جديد):**
```bash
ai-translate audit erpnext --lang ar
```

## ملخص الأوامر

### ترجمة (translate)

```bash
# الأساسي
ai-translate translate erpnext --lang ar --site mysite

# مع database content
ai-translate translate erpnext --lang ar --site mysite --db-scope

# database content فقط
ai-translate translate erpnext --lang ar --site mysite --db-scope-only

# DocTypes محددة
ai-translate translate erpnext --lang ar --site mysite \
  --db-scope --db-doc-types "Workspace,Report"

# مع flags مختصرة
ai-translate translate erpnext -l ar -s mysite -v

# dry-run
ai-translate translate erpnext --lang ar --site mysite --dry-run
```

### عرض Benches (list-benches)

```bash
ai-translate list-benches
ai-translate list-benches --verbose
ai-translate list-benches -v
```

### مراجعة (review)

```bash
# مراجعة جميع الترجمات
ai-translate review erpnext --lang ar

# مع context
ai-translate review erpnext --lang ar --context "ERP System"

# ترجمات تحتاج مراجعة فقط
ai-translate review erpnext --lang ar --status needs_review
```

### Audit (audit)

```bash
# Audit شامل
ai-translate audit erpnext --lang ar

# مع verbose
ai-translate audit erpnext --lang ar --verbose
```

## مقارنة سريعة

| المهمة | قبل التحديث | بعد التحديث |
|--------|-------------|-------------|
| ترجمة | `ai-translate erpnext --lang ar` | `ai-translate translate erpnext --lang ar` |
| عرض benches | `ai-translate list-benches` | `ai-translate list-benches` ✅ |
| مراجعة | `ai-translate review erpnext --lang ar` | `ai-translate review erpnext --lang ar` ✅ |
| Audit | ❌ غير موجود | `ai-translate audit erpnext --lang ar` ✨ |

## أمثلة عملية

### مثال 1: ترجمة بسيطة

```bash
# 1. ابحث عن benches
ai-translate list-benches

# 2. اترجم
ai-translate translate erpnext --lang ar --site mysite

# 3. راجع
ai-translate review erpnext --lang ar

# 4. تحقق
ai-translate audit erpnext --lang ar
```

### مثال 2: ترجمة مع database

```bash
ai-translate translate erpnext --lang ar --site mysite --db-scope
```

### مثال 3: ترجمة DocTypes محددة

```bash
ai-translate translate erpnext --lang ar --site mysite \
  --db-scope --db-doc-types "Workspace,Report,Dashboard"
```

## المساعدة

```bash
# المساعدة العامة
ai-translate --help

# مساعدة أمر محدد
ai-translate translate --help
ai-translate review --help
ai-translate audit --help
ai-translate list-benches --help
```

## ملاحظات مهمة

1. **يجب استخدام `translate` كـ subcommand** - لا يمكن استخدام الأمر مباشرة
2. **Flags مختصرة متاحة**: `-l` بدلاً من `--lang`، `-s` بدلاً من `--site`
3. **الأوامر الأخرى لم تتغير**: `list-benches` و `review` كما هي
4. **أمر جديد**: `audit` متاح الآن

## إذا نسيت الأمر

```bash
# اعرض جميع الأوامر المتاحة
ai-translate --help
```

ستحصل على:
```
Usage: ai-translate [OPTIONS] COMMAND [ARGS]...

Commands:
  audit         Audit translations - show statistics and...
  list-benches  List available benches (including Frappe...
  review        Review and improve translations with AI...
  translate     Translate app(s) - extracts all...
```

