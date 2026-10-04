import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import array, col, current_timestamp, lit, map_from_arrays, monotonically_increasing_id
from pyspark.sql.types import StringType, StructField, StructType
from config.settings import DB_NAME, MONGO_URI, COLLECTION_RAW, SPARK_APP_NAME, SPARK_MASTER

def load_with_pyspark(file_path, run_id):
    spark = SparkSession.builder.master(SPARK_MASTER).appName(SPARK_APP_NAME).getOrCreate()
    started = time.perf_counter()
    try:
        header = _read_header(file_path)
        schema = StructType([StructField(name, StringType(), True) for name in header])
        df = spark.read.option("header", "true").option("mode", "PERMISSIVE").schema(schema).csv(file_path)
        source_row = monotonically_increasing_id()
        keys = array(*[lit(name) for name in header])
        values = array(*[col(name) for name in header])
        raw_df = df.select(lit(run_id).alias("run_id"), lit(file_path).alias("source_file"),
                           source_row.alias("source_row_number"), current_timestamp().alias("ingested_at"),
                           lit("pyspark").alias("engine_used"),
                           map_from_arrays(keys, values).alias("raw_record"))
        partitions = raw_df.rdd.getNumPartitions()
        total = raw_df.count()
        raw_df.write.format("mongodb").mode("append").option(
            "spark.mongodb.write.connection.uri", f"{MONGO_URI}{DB_NAME}.{COLLECTION_RAW}").save()
        elapsed = time.perf_counter() - started
        print(f"[PySpark] rows={total} partitions={partitions} elapsed={elapsed:.3f}s throughput={total/elapsed if elapsed else 0:.2f} rows/s")
        return {"rows": total, "partitions": partitions, "elapsed_seconds": round(elapsed, 4),
                "throughput": round(total / elapsed if elapsed else 0, 2)}
    finally:
        spark.stop()

def _read_header(file_path):
    import csv
    with open(file_path, "r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        return next(csv.reader(stream))
