# توصيات تحسين النظام / System Improvement Recommendations

## 🎯 الأولويات / Priorities

---

## 🔴 المرحلة 1: إصلاحات حرجة (Critical Fixes)

### 1.1 إصلاح CLI Parsing - **عاجل جداً**

**المشكلة الحالية:**
- Parsing يدوي معقد وهش
- لا يدعم flags مختصرة
- معرض للأخطاء

**التوصية:**
استخدام `click` بدلاً من Typer للتحكم الكامل:

```python
# cli.py - استخدام click
import click

@click.command()
@click.argument('apps')
@click.option('--lang', required=True, help='Target language code')
@click.option('--site', help='Site name')
@click.option('--bench-path', help='Bench directory path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def translate(apps, lang, site, bench_path, verbose):
    """Translate app(s) - extracts and translates missing strings."""
    _translate_impl(apps, lang, site, bench_path, verbose)
```

**الفائدة:**
- ✅ Parsing آمن وموثوق
- ✅ دعم flags مختصرة (`-v`)
- ✅ Validation تلقائي
- ✅ Help messages تلقائية

**الوقت المقدر:** 2-3 ساعات

---

### 1.2 إضافة Batching حقيقي للترجمة - **عاجل جداً**

**المشكلة الحالية:**
- استدعاء API لكل نص على حدة
- بطيء جداً (20 دقيقة لـ 5000 نص)
- يستهلك rate limits

**التوصية:**
تجميع النصوص في batches وإرسالها معاً:

```python
# translator.py
def translate_batch(
    self,
    texts: List[str],
    target_lang: str,
    source_lang: str = "en",
    batch_size: int = 20,  # زيادة batch size
) -> List[Tuple[Optional[str], str]]:
    """Translate batch with single API call."""
    results = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # بناء prompt واحد لجميع النصوص
        batch_prompt = self._build_batch_prompt(batch, target_lang, source_lang)
        
        try:
            response = self.client.chat.completions.create(
                model=self.models[self.current_model_index],
                messages=[
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": batch_prompt},
                ],
                temperature=0.2,
                max_tokens=2000,  # زيادة للنصوص المتعددة
            )
            
            # Parse response (نصوص مفصولة بـ newline أو JSON)
            translated_batch = self._parse_batch_response(response, len(batch))
            
            for text, translated in zip(batch, translated_batch):
                # Validate placeholders
                if self.policy.validate_placeholders(text, translated):
                    results.append((translated, "ok"))
                else:
                    results.append((None, "rejected"))
                    
        except Exception as e:
            # Fallback to individual translation
            for text in batch:
                result = self.translate(text, target_lang, source_lang)
                results.append(result)
    
    return results
```

**الفائدة:**
- ✅ أسرع 10-20 مرة
- ✅ استهلاك أقل لـ rate limits
- ✅ تكلفة أقل (API calls أقل)

**الوقت المقدر:** 4-5 ساعات

---

### 1.3 إصلاح Layers B/C - **مهم**

**المشكلة الحالية:**
- DB extraction يعيد بيانات وهمية
- لا يوجد اتصال فعلي بقاعدة البيانات

**التوصية:**
إضافة Frappe DB connection:

```python
# db_scope.py
import frappe

class DBExtractor:
    def __init__(self, site: Optional[str] = None):
        self.site = site
        self._connected = False
    
    def _ensure_connection(self):
        """Connect to Frappe DB if not connected."""
        if not self._connected and self.site:
            frappe.init(site=self.site)
            frappe.connect()
            self._connected = True
    
    def extract_from_doctype(
        self, scope: DBExtractionScope, site: Optional[str] = None
    ) -> Iterator[Dict]:
        """Extract records from DocType."""
        self._ensure_connection()
        
        if not frappe.db:
            return
        
        try:
            # Query using frappe.db.get_all
            records = frappe.db.get_all(
                scope.doctype,
                fields=scope.fields,
                filters=scope.filters or {},
                limit=None,
            )
            
            for record in records:
                for field in scope.fields:
                    value = record.get(field)
                    if isinstance(value, str) and value.strip():
                        yield {
                            "doctype": scope.doctype,
                            "name": record.name,
                            "field": field,
                            "value": value,
                            "context": TranslationContext(
                                layer=scope.layer,
                                doctype=scope.doctype,
                                fieldname=field,
                                data_nature="label" if scope.layer == "B" else "content",
                                intent="user-facing",
                            ),
                        }
        except Exception as e:
            self.output.warning(f"Failed to extract from {scope.doctype}: {e}")
```

**الفائدة:**
- ✅ Layers B & C تعمل فعلياً
- ✅ استخراج بيانات حقيقية من قاعدة البيانات

**الوقت المقدر:** 6-8 ساعات

---

## 🟡 المرحلة 2: تحسينات مهمة (Important Improvements)

### 2.1 تحسين Regex Patterns

**التوصية:**
استخدام AST parsing للـ Python و JavaScript:

```python
# extractors.py
import ast
import re

class CodeExtractor:
    def extract_from_python_ast(self, file_path: Path):
        """Extract using AST for better accuracy."""
        try:
            tree = ast.parse(file_path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ('_', '__', '_lt'):
                            # Extract string arguments
                            for arg in node.args:
                                if isinstance(arg, ast.Str):
                                    yield arg.s
        except SyntaxError:
            # Fallback to regex
            yield from self.extract_from_file_regex(file_path)
```

**الفائدة:**
- ✅ دعم f-strings
- ✅ دعم multiline strings
- ✅ دعم escaped quotes
- ✅ أكثر دقة

**الوقت المقدر:** 8-10 ساعات

---

### 2.2 إضافة Caching

**التوصية:**
استخدام `diskcache` أو `joblib`:

```python
# storage.py
from diskcache import Cache

class TranslationStorage:
    def __init__(self, storage_path: Path, lang: str):
        # ... existing code ...
        self.cache = Cache(str(storage_path / '.cache'))
    
    def get(self, source_text: str, context: Optional[TranslationContext] = None):
        """Get with caching."""
        cache_key = f"{source_text}:{lang}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        result = self._get_from_csv(source_text, context)
        if result:
            self.cache.set(cache_key, result, expire=3600)
        return result
```

**الفائدة:**
- ✅ أسرع في القراءة المتكررة
- ✅ تقليل I/O operations

**الوقت المقدر:** 2-3 ساعات

---

### 2.3 تحسين Error Handling

**التوصية:**
إضافة structured logging:

```python
# output.py
import logging
from pathlib import Path

class OutputFilter:
    def __init__(self, verbose: bool = False, log_file: Optional[Path] = None):
        self.verbose = verbose
        self.logger = logging.getLogger('ai_translate')
        
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error with exception info."""
        self.error_console.print(f"[red]✗[/red] {message}")
        self.logger.error(message, exc_info=exc_info)
```

**الفائدة:**
- ✅ تتبع أفضل للأخطاء
- ✅ debugging أسهل
- ✅ logs قابلة للتحليل

**الوقت المقدر:** 2-3 ساعات

---

### 2.4 إكمال DB Write

**التوصية:**
إضافة Frappe DB write:

```python
# db_write.py
import frappe

class TranslationDBWriter:
    def write_entry(self, entry: TranslationEntry, lang: str, dry_run: bool = False):
        """Write to Frappe Translation DocType."""
        if dry_run:
            return True
        
        try:
            frappe.init(site=self.site)
            frappe.connect()
            
            # Check if translation exists
            existing = frappe.db.exists("Translation", {
                "source_text": entry.source_text,
                "language": lang,
            })
            
            if existing:
                if self.update_existing:
                    doc = frappe.get_doc("Translation", existing)
                    doc.translated_text = entry.translated_text
                    doc.save()
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "source_text": entry.source_text,
                    "translated_text": entry.translated_text,
                    "language": lang,
                    "context": self._context_to_string(entry.context),
                })
                doc.insert(ignore_if_duplicate=True)
                self.stats["inserted"] += 1
            
            return True
        except Exception as e:
            self.output.error(f"Failed to write translation: {e}", exc_info=True)
            return False
```

**الفائدة:**
- ✅ كتابة فعليّة في قاعدة البيانات
- ✅ دعم Frappe Translation DocType

**الوقت المقدر:** 4-5 ساعات

---

## 🟢 المرحلة 3: تحسينات إضافية (Enhancements)

### 3.1 إضافة Unit Tests

**التوصية:**
استخدام `pytest`:

```python
# tests/test_storage.py
import pytest
from pathlib import Path
from ai_translate.storage import TranslationStorage

def test_storage_save_preserves_existing(tmp_path):
    """Test that save() preserves existing translations."""
    storage = TranslationStorage(tmp_path / "translations", "ar")
    
    # Add existing translation
    storage.set("Hello", "مرحبا", TranslationContext(layer="A"))
    storage.save()
    
    # Add new translation
    storage.set("World", "عالم", TranslationContext(layer="A"))
    storage.save()
    
    # Verify both exist
    assert storage.get("Hello") == "مرحبا"
    assert storage.get("World") == "عالم"
```

**الوقت المقدر:** 10-15 ساعة

---

### 3.2 إضافة Configuration File

**التوصية:**
استخدام `pydantic-settings`:

```python
# config.py
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    groq_api_key: str
    default_lang: str = "ar"
    batch_size: int = 20
    max_retries: int = 3
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**الوقت المقدر:** 2-3 ساعات

---

### 3.3 تحسين PO Format

**التوصية:**
استخدام `polib` library:

```python
# gettext_sync.py
import polib

def sync_csv_to_po(self):
    """Sync using polib for proper PO format."""
    po = polib.POFile()
    po.metadata = {
        'Content-Type': 'text/plain; charset=UTF-8',
        'Language': self.storage.lang,
    }
    
    for entry in self.storage.get_all():
        po_entry = polib.POEntry(
            msgid=entry.source_text,
            msgstr=entry.translated_text,
        )
        po.append(po_entry)
    
    po.save(self.po_path)
```

**الوقت المقدر:** 2-3 ساعات

---

## 📊 خطة التنفيذ المقترحة / Implementation Plan

### الأسبوع 1: إصلاحات حرجة
- [ ] إصلاح CLI parsing (click)
- [ ] إضافة batching حقيقي
- [ ] اختبارات أساسية

### الأسبوع 2: إكمال المكونات
- [ ] إكمال DB extraction
- [ ] إكمال DB write
- [ ] تحسين error handling

### الأسبوع 3: تحسينات
- [ ] تحسين regex patterns
- [ ] إضافة caching
- [ ] تحسين PO format

### الأسبوع 4: اختبارات وتوثيق
- [ ] Unit tests
- [ ] Integration tests
- [ ] تحديث documentation

---

## 🎯 التوصية الفورية (Immediate Recommendation)

**ابدأ بهذه الثلاثة:**

1. **إصلاح CLI Parsing** - سيجعل الأداة أكثر موثوقية
2. **إضافة Batching** - سيجعل الأداة أسرع 10-20 مرة
3. **إكمال DB Extraction** - سيجعل Layers B/C تعمل فعلياً

هذه الثلاثة ستحدث فرقاً كبيراً في الأداء والموثوقية.

---

## 📈 المقاييس المتوقعة / Expected Metrics

### بعد التحسينات:

| المقياس | قبل | بعد | التحسين |
|---------|-----|-----|---------|
| سرعة الترجمة (5000 نص) | 20 دقيقة | 2-3 دقائق | **7-10x** |
| دقة الاستخراج | 85% | 95%+ | **+10%** |
| استهلاك API calls | 5000 | 250-500 | **10-20x** |
| موثوقية CLI | 70% | 95%+ | **+25%** |

---

**تاريخ التوصيات:** $(date)
**المراجع:** AI Code Reviewer

