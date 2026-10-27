import argparse
import glob
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pyspark.sql import SparkSession, functions as F

load_dotenv()


def replace_collection(database, name: str, documents: list[dict]) -> None:
    collection = database[name]
    collection.delete_many({})
    if documents:
        collection.insert_many(documents)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run distributed taxi analytics with Apache Spark")
    parser.add_argument("--input", required=True, help="Parquet file, directory, or glob")
    args = parser.parse_args()

    input_path = args.input
    if any(character in input_path for character in "*?[]"):
        matches = glob.glob(input_path)
        if not matches:
            raise FileNotFoundError(f"No files matched: {input_path}")
        input_path = matches
    elif not os.path.exists(input_path):
        raise FileNotFoundError(f"Input does not exist: {input_path}")

    spark = (
        SparkSession.builder
        .appName("UrbanMobilityTaxiAnalytics")
        .master("local[*]")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        raw = spark.read.parquet(input_path)
        trips = (
            raw.select(
                F.col("tpep_pickup_datetime").alias("pickup_time"),
                F.col("tpep_dropoff_datetime").alias("dropoff_time"),
                F.col("passenger_count").cast("double"),
                F.col("trip_distance").cast("double"),
                F.col("fare_amount").cast("double"),
                F.col("total_amount").cast("double"),
                F.col("PULocationID").cast("int").alias("pickup_zone"),
                F.col("DOLocationID").cast("int").alias("dropoff_zone"),
            )
            .withColumn(
                "duration_minutes",
                (F.unix_timestamp("dropoff_time") - F.unix_timestamp("pickup_time")) / 60,
            )
            .withColumn("pickup_hour", F.hour("pickup_time"))
            .filter(
                (F.col("trip_distance") > 0)
                & (F.col("trip_distance") < 200)
                & (F.col("fare_amount") >= 0)
                & (F.col("total_amount") >= 0)
                & F.col("pickup_zone").isNotNull()
                & F.col("dropoff_zone").isNotNull()
                & F.year("pickup_time").between(2020, 2030)
                & (F.col("duration_minutes") > 0)
                & (F.col("duration_minutes") <= 300)
            )
            .cache()
        )

        total_trips = trips.count()
        if total_trips == 0:
            raise ValueError("No valid trips remained after cleaning")

        overview_row = trips.agg(
            F.sum("total_amount").alias("total_revenue"),
            F.avg("fare_amount").alias("average_fare"),
            F.avg("trip_distance").alias("average_distance"),
            F.avg("duration_minutes").alias("average_duration"),
            F.min("pickup_time").alias("data_start"),
            F.max("pickup_time").alias("data_end"),
        ).first().asDict()
        overview = {
            "total_trips": total_trips,
            "total_revenue": round(float(overview_row["total_revenue"] or 0), 2),
            "average_fare": round(float(overview_row["average_fare"] or 0), 2),
            "average_distance": round(float(overview_row["average_distance"] or 0), 2),
            "average_duration": round(float(overview_row["average_duration"] or 0), 2),
            "data_start": str(overview_row["data_start"]),
            "data_end": str(overview_row["data_end"]),
        }

        hourly = [
            {"hour": int(row["pickup_hour"]), "trips": int(row["trips"]), "revenue": round(float(row["revenue"]), 2)}
            for row in trips.groupBy("pickup_hour")
            .agg(F.count("*").alias("trips"), F.sum("total_amount").alias("revenue"))
            .orderBy("pickup_hour")
            .collect()
        ]
        routes = [
            {
                "pickup_zone": int(row["pickup_zone"]),
                "dropoff_zone": int(row["dropoff_zone"]),
                "trips": int(row["trips"]),
                "average_fare": round(float(row["average_fare"]), 2),
            }
            for row in trips.groupBy("pickup_zone", "dropoff_zone")
            .agg(F.count("*").alias("trips"), F.avg("fare_amount").alias("average_fare"))
            .orderBy(F.desc("trips"))
            .limit(10)
            .collect()
        ]
        zones = [
            {
                "pickup_zone": int(row["pickup_zone"]),
                "trips": int(row["trips"]),
                "revenue": round(float(row["revenue"]), 2),
                "average_distance": round(float(row["average_distance"]), 2),
            }
            for row in trips.groupBy("pickup_zone")
            .agg(
                F.count("*").alias("trips"),
                F.sum("total_amount").alias("revenue"),
                F.avg("trip_distance").alias("average_distance"),
            )
            .orderBy(F.desc("trips"))
            .limit(15)
            .collect()
        ]

        client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
        database = client[os.getenv("MONGODB_DATABASE", "taxi_analytics")]
        replace_collection(database, "overview", [overview])
        replace_collection(database, "hourly_demand", hourly)
        replace_collection(database, "top_routes", routes)
        replace_collection(database, "zone_performance", zones)
        replace_collection(database, "metadata", [{
            "source": "NYC TLC Yellow Taxi Trip Records",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input": str(args.input),
            "cleaned_records": total_trips,
            "engine": "Apache Spark / PySpark",
        }])
        client.close()
        print(f"Loaded analytics for {total_trips:,} valid trips into MongoDB")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
