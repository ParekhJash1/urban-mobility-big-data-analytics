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
    parser.add_argument("--zone-lookup", default="data/zones/taxi_zone_lookup.csv", help="Official TLC zone lookup CSV")
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

        zone_lookup_available = os.path.exists(args.zone_lookup)
        if zone_lookup_available:
            zone_lookup = (
                spark.read.option("header", "true").option("inferSchema", "true").csv(args.zone_lookup)
                .select(
                    F.col("LocationID").cast("int").alias("zone_id"),
                    F.col("Borough").alias("borough"),
                    F.col("Zone").alias("zone_name"),
                )
                .dropDuplicates(["zone_id"])
            )
        else:
            zone_lookup = None

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
        route_aggregate = trips.groupBy("pickup_zone", "dropoff_zone").agg(
            F.count("*").alias("trips"), F.avg("fare_amount").alias("average_fare")
        )
        zone_aggregate = trips.groupBy("pickup_zone").agg(
            F.count("*").alias("trips"),
            F.sum("total_amount").alias("revenue"),
            F.avg("trip_distance").alias("average_distance"),
        )
        if zone_lookup is not None:
            pickup_lookup = zone_lookup.select(
                F.col("zone_id").alias("pickup_zone"),
                F.col("zone_name").alias("pickup_name"),
                F.col("borough").alias("pickup_borough"),
            )
            dropoff_lookup = zone_lookup.select(
                F.col("zone_id").alias("dropoff_zone"),
                F.col("zone_name").alias("dropoff_name"),
                F.col("borough").alias("dropoff_borough"),
            )
            route_aggregate = route_aggregate.join(pickup_lookup, "pickup_zone", "left").join(dropoff_lookup, "dropoff_zone", "left")
            zone_aggregate = zone_aggregate.join(
                zone_lookup.select(
                    F.col("zone_id").alias("pickup_zone"),
                    F.col("zone_name"),
                    F.col("borough"),
                ),
                "pickup_zone",
                "left",
            )

        routes = [
            {
                "pickup_zone": int(row["pickup_zone"]),
                "dropoff_zone": int(row["dropoff_zone"]),
                "pickup_name": row["pickup_name"] if zone_lookup is not None and row["pickup_name"] else f"Zone {int(row['pickup_zone'])}",
                "dropoff_name": row["dropoff_name"] if zone_lookup is not None and row["dropoff_name"] else f"Zone {int(row['dropoff_zone'])}",
                "pickup_borough": row["pickup_borough"] if zone_lookup is not None and row["pickup_borough"] else "Unknown",
                "dropoff_borough": row["dropoff_borough"] if zone_lookup is not None and row["dropoff_borough"] else "Unknown",
                "trips": int(row["trips"]),
                "average_fare": round(float(row["average_fare"]), 2),
            }
            for row in route_aggregate
            .orderBy(F.desc("trips"))
            .limit(10)
            .collect()
        ]
        zones = [
            {
                "pickup_zone": int(row["pickup_zone"]),
                "zone_name": row["zone_name"] if zone_lookup is not None and row["zone_name"] else f"Zone {int(row['pickup_zone'])}",
                "borough": row["borough"] if zone_lookup is not None and row["borough"] else "Unknown",
                "trips": int(row["trips"]),
                "revenue": round(float(row["revenue"]), 2),
                "average_distance": round(float(row["average_distance"]), 2),
            }
            for row in zone_aggregate
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
            "zone_lookup": zone_lookup_available,
        }])
        client.close()
        print(f"Loaded analytics for {total_trips:,} valid trips into MongoDB")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
