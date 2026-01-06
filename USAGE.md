# دليل استخدام ai-translate

## التثبيت

```bash
pipx install git+https://github.com/Baron-Systems/ft.git
```

أو من المجلد المحلي:

```bash
pip install -e .
```

## إعداد API Key

```bash
export GROQ_API_KEY="your-api-key-here"
```

## الأوامر الأساسية

### 1. ترجمة تطبيق

الاستخدام الأساسي:

```bash
# ترجمة تطبيق واحد (الاختصار: إذا كتبت اسم التطبيق مباشرة فهو يعادل `translate`)
ai-translate erpnext --lang ar --site mysite

# ترجمة عدة تطبيقات
ai-translate erpnext,frappe --lang ar --site mysite

# مع تحديد bench path
ai-translate erpnext --lang ar --site mysite --bench-path /path/to/bench
```

### 2. خيارات الترجمة

```bash
# وضع verbose للمزيد من المعلومات
ai-translate erpnext --lang ar --site mysite --verbose

# وضع dry-run (لا يكتب أي شيء)
ai-translate erpnext --lang ar --site mysite --dry-run
```

### 3. مراجعة الترجمات

```bash
# مراجعة جميع الترجمات
ai-translate review erpnext --lang ar

# مراجعة مع context للتطبيق
ai-translate review erpnext --lang ar --context "Enterprise Resource Planning System"

# مراجعة مع bench path
ai-translate review erpnext --lang ar --bench-path /path/to/bench

# مراجعة ترجمات تحتاج مراجعة فقط
ai-translate review erpnext --lang ar --status needs_review
```

## أمثلة عملية

### مثال 1: ترجمة تطبيق ERPNext للعربية

```bash
# 1. تأكد من وجود API key
export GROQ_API_KEY="your-key"

# 2. اترجم التطبيق (يضيف الناقص فقط ويحافظ على الموجود)
ai-translate erpnext --lang ar --site mysite

# 3. راجع الترجمات
ai-translate review erpnext --lang ar --context "ERP System"
```

### مثال 2: ترجمة مع database content

```bash
# تمرير --site يجعل الأداة تشمل محتوى قاعدة البيانات تلقائياً (UI + User Content)
ai-translate erpnext --lang ar --site mysite
```

### مثال 3: ترجمة عدة تطبيقات

```bash
# ترجمة frappe و erpnext معاً
ai-translate translate frappe,erpnext --lang ar --site mysite
```

## أين توجد ملفات الترجمة؟

بعد الترجمة، ستجد ملفات CSV في:

```
apps/erpnext/erpnext/translations/ar.csv
apps/frappe/frappe/translations/ar.csv
```

هذه هي الملفات القياسية لـ Frappe ويمكن استخدامها مباشرة.

## استخدام Language Memory

النظام يبني ذاكرة لغوية تلقائياً في:

```
apps/erpnext/erpnext/translations/ar_memory.json
```

هذه الذاكرة تحتوي على:
- **Terminology**: مصطلحات مترجمة
- **Style Profile**: أسلوب الترجمة (formal/informal/neutral)
- **Accepted Translations**: ترجمات معتمدة

## Context-Aware Translation

النظام يستخدم السياق تلقائياً:

- **Layer A**: Code & Files - ترجمة محافظة
- **Layer B**: UI Metadata - ترجمة واجهة المستخدم
- **Layer C**: User Content - ترجمة المحتوى

## Policy Engine

النظام يرفض تلقائياً:
- Identifiers (أسماء متغيرات، دوال، إلخ)
- Code patterns
- URLs و emails
- SQL keywords
- Logic-bearing content

## Review System

```bash
# عرض الترجمات التي تحتاج مراجعة
ai-translate review erpnext --lang ar --status needs_review

# الموافقة على ترجمة (برمجياً)
from ai_translate.review import ReviewManager
from ai_translate.storage import TranslationStorage

storage = TranslationStorage(...)
manager = ReviewManager(storage)
manager.approve("Hello World")
```

## Flags مختصرة

```bash
# -l بدلاً من --lang
ai-translate translate erpnext -l ar -s mysite

# -v بدلاً من --verbose
ai-translate translate erpnext -l ar -v

# -b بدلاً من --bench-path
ai-translate translate erpnext -l ar -b /path/to/bench
```

## Troubleshooting

### مشكلة: Bench path not found

```bash
# أو حدد bench path يدوياً
ai-translate translate erpnext --lang ar --site mysite --bench-path /path/to/bench
```

### مشكلة: API key missing

```bash
export GROQ_API_KEY="your-key"
```

### مشكلة: Model decommissioned

النظام يحاول تلقائياً نماذج بديلة:
- llama-3.3-70b-versatile
- llama-3.1-8b-instant
- mixtral-8x7b-32768

### مشكلة: ترجمات محذوفة

النظام **لا يحذف** الترجمات الموجودة. إذا حدث ذلك، تحقق من:
- أنك تستخدم نفس ملف CSV
- أن `update_existing=False` (الافتراضي)

## Advanced Usage

### استخدام Caching

```python
from ai_translate.cache import TranslationCache
from pathlib import Path

cache = TranslationCache(cache_dir=Path(".cache"), lang="ar")
cached = cache.get_translation("Hello", "ar")
if not cached:
    # Translate...
    cache.set_translation("Hello", "ar", "مرحبا")
```

### استخدام Language Memory

```python
from ai_translate.language_memory import LanguageMemoryManager
from pathlib import Path

manager = LanguageMemoryManager(storage_path=Path("translations"))
memory = manager.get_memory("ar")

# Get terminology
term = memory.get_terminology("Customer")  # Returns "عميل"

# Get examples
examples = memory.get_examples("button")
```

### استخدام Translation Contract

```python
from ai_translate.translation_contract import TranslationContract
from ai_translate.language_memory import LanguageMemoryManager

manager = LanguageMemoryManager(...)
memory = manager.get_memory("ar")
contract = TranslationContract(memory)

prompt = contract.build_prompt(
    "Create Invoice",
    target_lang="ar",
    context_type="button"
)
```

## Best Practices

1. **ابدأ بالترجمة ثم راجعها**:
   ```bash
   ai-translate erpnext --lang ar --site mysite
   ai-translate review erpnext --lang ar --context "ERP System"
   ```

2. **استخدم --dry-run أولاً**:
   ```bash
   ai-translate translate erpnext --lang ar --site mysite --dry-run
   ```

## Support

للمزيد من المساعدة:
- راجع `README.md` للتفاصيل
- راجع `INSTALLATION_FM.md` لمستخدمي Frappe Manager
- راجع `QUICKSTART_AR.md` للبدء السريع

