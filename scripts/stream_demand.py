"""Spark Structured Streaming job for live taxi demand events.

The default ``rate`` source is portable on Windows and requires no Kafka or
Hadoop native binaries. A JSON-directory source is also available for Linux
or Windows installations configured with winutils.exe.
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pyspark.sql import SparkSession, functions as F, types as T

load_dotenv()


EVENT_SCHEMA = T.StructType([
    T.StructField("event_id", T.StringType()),
    T.StructField("pickup_time", T.StringType()),
    T.StructField("pickup_zone", T.IntegerType()),
    T.StructField("dropoff_zone", T.IntegerType()),
    T.StructField("total_amount", T.DoubleType()),
])


def process_batch(batch_df, batch_id: int) -> None:
    if batch_df.isEmpty():
        return
    database = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))[os.getenv("MONGODB_DATABASE", "taxi_analytics")]
    records = batch_df.count()
    hourly = batch_df.groupBy(F.hour("pickup_timestamp").alias("hour")).agg(
        F.count("*").alias("trips"),
        F.sum("total_amount").alias("revenue"),
    ).collect()
    for row in hourly:
        database["streaming_demand"].update_one(
            {"hour": int(row["hour"])},
            {"$inc": {"trips": int(row["trips"]), "revenue": float(row["revenue"] or 0)}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    database["stream_status"].update_one(
        {"_id": "current"},
        {"$set": {"last_batch_id": int(batch_id), "last_batch_records": records, "updated_at": datetime.now(timezone.utc), "source": "Spark Structured Streaming"}, "$inc": {"events_processed": records}},
        upsert=True,
    )
    database.client.close()
    print(json.dumps({"batch_id": batch_id, "records": records}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Process live taxi events with Spark Structured Streaming")
    parser.add_argument("--source", choices=("rate", "file"), default="rate")
    parser.add_argument("--input-dir", default="data/stream/incoming")
    parser.add_argument("--checkpoint", default="data/stream/checkpoint")
    parser.add_argument("--trigger-seconds", type=int, default=5)
    parser.add_argument("--rows-per-second", type=int, default=2)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    local_hadoop = project_root / "hadoop-local"
    if os.name == "nt" and (local_hadoop / "bin" / "winutils.exe").exists() and not os.getenv("HADOOP_HOME"):
        os.environ["HADOOP_HOME"] = str(local_hadoop)
        os.environ["hadoop.home.dir"] = str(local_hadoop)
        os.environ["PATH"] = str(local_hadoop / "bin") + os.pathsep + os.environ.get("PATH", "")

    os.makedirs(args.input_dir, exist_ok=True)
    spark = SparkSession.builder.appName("UrbanMobilityStreamingDemand").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    if args.source == "file":
        events = spark.readStream.schema(EVENT_SCHEMA).json(args.input_dir)
    else:
        rate = spark.readStream.format("rate").option("rowsPerSecond", args.rows_per_second).load()
        events = rate.select(
            F.col("value").cast("string").alias("event_id"),
            F.col("timestamp").cast("string").alias("pickup_time"),
            ((F.col("value") % 9) + 1).cast("int").alias("pickup_zone"),
            (((F.col("value") * 7) % 9) + 1).cast("int").alias("dropoff_zone"),
            (F.lit(12.0) + (F.col("value") % 45)).cast("double").alias("total_amount"),
        )
    events = (
        events.withColumn("pickup_timestamp", F.to_timestamp("pickup_time"))
        .filter(F.col("pickup_timestamp").isNotNull() & F.col("pickup_zone").isNotNull())
    )
    query = (
        events.writeStream.foreachBatch(process_batch)
        .option("checkpointLocation", args.checkpoint)
        .trigger(processingTime=f"{args.trigger_seconds} seconds")
        .start()
    )
    source_description = "Spark rate source" if args.source == "rate" else f"JSON files in {args.input_dir}"
    print(f"Streaming taxi events from {source_description}; press Ctrl+C to stop")
    try:
        query.awaitTermination()
    finally:
        query.stop()
        spark.stop()


if __name__ == "__main__":
    main()
