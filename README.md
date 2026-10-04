# Hybrid E-Commerce Data Pipeline — Final Submission

مشروع مقرر البيانات الضخمة العملي. يحتوي هذا الفرع على المشروع النصفي بالإضافة إلى متطلبات المرحلة النهائية.

## محتويات المشروع

- `src/main.py`: نقطة تشغيل خط البيانات النصفي.
- `src/batch_loader.py`: تحميل Python Batch للملفات الصغيرة.
- `src/spark_loader.py`: تحميل PySpark للملفات الكبيرة.
- `src/quality_rules.py`: قواعد التنظيف والتصنيف.
- `src/final_queries.py`: الاستعلامات والفهارس وExplain.
- `src/final_aggregations.py`: تقارير التجميع الخمسة.
- `src/materialized_views.py`: العرضان الماديان والتحديث التزايدي.
- `src/scheduled_jobs.py`: المهام المجدولة.
- `src/api.py`: الواجهة الموحدة.
- `tests/`: اختبارات المرحلتين.
- `data/orders_sample.csv`: عينة صغيرة للتجربة.
- `docs/architecture.md`: شرح المعمارية.

## 1. المتطلبات

- Python 3.10 أو أحدث.
- MongoDB يعمل محليًا على `mongodb://localhost:27017/`.
- Java 17 أو 21 عند تشغيل Spark.
- Apache Spark 3.5 عند تجربة مسار الملف الكبير.
- MongoDB Spark Connector عند تشغيل PySpark.

## 2. التثبيت

```bash
git clone <repository-url>
cd midterm-data-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

تأكد من تشغيل MongoDB قبل تنفيذ الأوامر التي تتصل بقاعدة البيانات. يمكن نسخ إعدادات البيئة عند الحاجة:

```bash
cp .env.example .env
```

الإعدادات الافتراضية مناسبة للتشغيل المحلي. يمكن تغيير `MONGO_URI` و`DB_NAME` و`BATCH_SIZE` و`SMALL_FILE_THRESHOLD_MB` و`SPARK_MASTER` عبر متغيرات البيئة.

## 3. اختبار المشروع النصفي

شغّل الاختبارات:

```bash
pytest -q
python -m compileall src config tests
```

لتشغيل العينة الصغيرة باستخدام Python Batch:

```bash
python -m src.main data/orders_sample.csv
```

يختار النظام المحرك حسب حجم الملف، ويطبع حجم الملف وسبب الاختيار. بعد التشغيل تُكتب البيانات في:

- `orders_raw`: السجلات كما وصلت قبل التنظيف.
- `orders_validated`: السجلات السليمة والمصححة.
- `orders_quarantine`: السجلات التي لا يمكن تصحيحها بأمان.
- `reports/results.json`: الزمن والعدادات ومعدل المعالجة.

لإنشاء عينة من ملف الدكتور:

```bash
python src/create_small_sample.py \
  --input orders_huge_mixed_quality.csv \
  --output data/orders_sample.csv \
  --rows 100000
```

لتشغيل الملف الكبير باستخدام PySpark:

```bash
spark-submit \
  --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 \
  src/main.py orders_huge_mixed_quality.csv
```

## 4. تشغيل الواجهة الموحدة

```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

تتوفر صفحة Swagger في:

```text
http://127.0.0.1:8000/docs
```

فحص حالة الخدمة:

```bash
curl http://127.0.0.1:8000/health
```

تشغيل خط الإدخال من خلال API:

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"file_path":"data/orders_sample.csv"}'
```

## 5. الاستعلامات والفهارس وExplain

إنشاء الفهارس الثلاثة:

```bash
curl -X POST http://127.0.0.1:8000/indexes
```

الاستعلامات المتوفرة:

- `orders_by_status`
- `customer_orders`
- `orders_in_date_range`
- `high_value_orders`
- `recent_orders`

عرض قائمة الاستعلامات أو تشغيل استعلام:

```bash
curl http://127.0.0.1:8000/queries
curl http://127.0.0.1:8000/queries/orders_by_status
```

تنفيذ `executionStats` قبل وبعد الفهارس:

```bash
curl -X POST http://127.0.0.1:8000/indexes/explain
```

## 6. تقارير Aggregation

التقارير الخمسة هي:

- `sales_by_day`
- `top_products`
- `top_customers`
- `orders_by_status`
- `price_summary`

تشغيلها:

```bash
curl http://127.0.0.1:8000/aggregations/sales_by_day
curl http://127.0.0.1:8000/aggregations/top_products
curl http://127.0.0.1:8000/aggregations/top_customers
curl http://127.0.0.1:8000/aggregations/orders_by_status
curl http://127.0.0.1:8000/aggregations/price_summary
```

## 7. Materialized Views

العرضان الماديان هما:

- `daily_sales_summary`
- `top_products_summary`

تحديث كل عرض:

```bash
curl -X POST http://127.0.0.1:8000/views/daily_sales_summary/run
curl -X POST http://127.0.0.1:8000/views/top_products_summary/run
curl -X POST http://127.0.0.1:8000/refresh-mv
```

قراءة النتائج:

```bash
curl http://127.0.0.1:8000/views/daily_sales_summary
curl http://127.0.0.1:8000/views/top_products_summary
```

يستخدم التحديث سجل `materialized_view_state` وقيمة `updated_at` لمعالجة التغييرات الجديدة فقط في التشغيلات اللاحقة، مع حفظ مساهمة كل `order_id` لمنع تكرار تأثير نفس الطلب.

## 8. المهام المجدولة

المهمتان هما:

- `refresh_daily_sales`: كل 15 دقيقة.
- `refresh_top_products`: كل 30 دقيقة.

عرض المهام أو تشغيلها يدويًا:

```bash
curl http://127.0.0.1:8000/jobs
curl -X POST http://127.0.0.1:8000/jobs/refresh_daily_sales/run
curl -X POST http://127.0.0.1:8000/jobs/refresh_top_products/run
```

لتفعيل الجدولة أثناء تشغيل API:

```bash
ENABLE_SCHEDULER=true uvicorn src.api:app --host 127.0.0.1 --port 8000
```

يسجل كل Job وقت البداية والنهاية وحالة النجاح أو الفشل.

## 9. إعادة التشغيل والاختبار

إعادة تشغيل نفس ملف الإدخال لا تزيد عدد Business Records في `orders_validated` لأن الكتابة تعتمد على `order_id` كـUnique Business Key مع Upsert:

```bash
python -m src.main data/orders_sample.csv
python -m src.main data/orders_sample.csv
```

ثم راجع `reports/results.json` وعدادات `inserted_count` و`updated_count` و`unchanged_count`.

يمكن تنفيذ الفحص الآلي مباشرة:

```bash
python src/idempotency_check.py data/orders_sample.csv
```

يفشل الأمر إذا زاد عدد Business Records بعد إعادة تشغيل نفس الملف.

## 10. اختبارات المرحلة النهائية

```bash
pytest -q
```

يجب أن تنجح اختبارات التنظيف والتصنيف والاستعلامات والتجميعات والعروض المادية وتعريف المهام.
