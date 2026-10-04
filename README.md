# Hybrid Data Pipeline — Midterm Submission

مشروع فردي لمقرر البيانات الضخمة العملي. ينفذ خط ELT لمعالجة بيانات الطلبات باستخدام Python Batch للملفات الصغيرة وApache Spark للملفات الكبيرة، مع MongoDB وتنظيف البيانات والعزل وإعادة التشغيل الآمنة.

## المتطلبات

- Python 3.10 أو أحدث.
- MongoDB يعمل على `mongodb://localhost:27017/`.
- Java 17 أو 21 عند تشغيل Spark.
- Apache Spark 3.5 عند تشغيل الملف الكبير.
- MongoDB Spark Connector عند تشغيل PySpark.

## التثبيت

```bash
git clone <repository-url>
cd midterm-data-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

تأكد من تشغيل MongoDB قبل تشغيل خط البيانات. الإعدادات المهمة هي `MONGO_URI` و`DB_NAME` و`SMALL_FILE_THRESHOLD_MB` و`BATCH_SIZE` و`SPARK_MASTER`، ويمكن ضبطها مباشرة كمتغيرات بيئة عند الحاجة.

## إنشاء عينة قابلة لإعادة الإنتاج

```bash
python src/create_small_sample.py \
  --input orders_huge_mixed_quality.csv \
  --output data/orders_sample.csv \
  --rows 100000
```

العينة الموجودة في `data/orders_sample.csv` جاهزة للتجربة.

## تشغيل مسار Python Batch

```bash
python -m src.main data/orders_sample.csv
```

يفحص البرنامج حجم الملف ويختار `python_batch` للملف الصغير. يطبع رقم كل دفعة وزمن الإدخال ومعدل المعالجة. بعد التشغيل تظهر البيانات في:

- `orders_raw`: جميع السجلات كما وصلت قبل التنظيف.
- `orders_validated`: السجلات السليمة والمصححة.
- `orders_quarantine`: السجلات التي لا يمكن تصحيحها مع أسباب العزل.
- `reports/results.json`: العدادات والزمن ومعدل المعالجة.

## تشغيل مسار PySpark

```bash
spark-submit \
  --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 \
  src/main.py orders_huge_mixed_quality.csv
```

يستخدم هذا المسار Schema ثابتة ويقرأ الحقول كسلاسل نصية في Raw للمحافظة على القيم غير النظيفة. لا يستخدم Pandas.

## قواعد الجودة

يطبق الخط قواعد الأرقام العربية والعملة وفواصل الآلاف والأسعار بالكلمات المعروفة وتنظيف الهاتف وإصلاح رموز البريد وتوحيد التاريخ وتطبيع الحالة وتحليل JSON للعناصر. يحتفظ كل تصحيح بـ`field` و`original_value` و`corrected_value` و`rule_code`، بينما يحتوي Quarantine على `error_codes` و`error_details` و`raw_record`.

يتعرف المنظف على أسماء أعمدة شائعة بالإنجليزية والعربية مثل `order_id` و`OrderID` و`Order Number` و`رقم الطلب`، مع بدائل السعر والعميل والتاريخ والمنتجات.

## اختبار Idempotency وUpsert

```bash
python -m src.main data/orders_sample.csv
python -m src.main data/orders_sample.csv
```

قد يحتفظ `orders_raw` بتشغيل جديد لأغراض التتبع، لكن عدد Business Records في `orders_validated` حسب `order_id` لا يزيد. راجع `inserted_count` و`updated_count` و`unchanged_count` في `reports/results.json`.

ولتنفيذ الفحص الآلي لنفس الملف مرتين:

```bash
python src/idempotency_check.py data/orders_sample.csv
```

يُظهر الأمر عدد Business Records بعد التشغيل الأول والثاني، ويفشل إذا زاد العدد بعد إعادة التشغيل.

## الاختبارات

```bash
pytest -q
python -m compileall src config tests
```

الاختبارات تغطي التنظيف والتصنيف والتاريخ وJSON والسجلات الناقصة وأسماء الأعمدة البديلة وموجّه الملفات.

## بنية المشروع

```text
config/       الإعدادات
src/          كود خط البيانات
tests/        الاختبارات
data/         العينة الصغيرة
reports/      النتائج
```

هذه النسخة خاصة بمتطلبات المشروع النصفي. إضافات المرحلة النهائية موجودة في فرع `final`.
