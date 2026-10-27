import math
import os
import random
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
random.seed(7)


def main() -> None:
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    database = client[os.getenv("MONGODB_DATABASE", "taxi_analytics")]

    overview = {
        "total_trips": 1_842_631,
        "total_revenue": 32_645_812.48,
        "average_fare": 17.72,
        "average_distance": 3.41,
        "average_duration": 18.6,
        "data_start": "2024-01-01 00:00:00",
        "data_end": "2024-01-31 23:59:59",
    }
    hourly = [
        {"hour": hour, "trips": int(38000 + 24000 * math.sin((hour - 6) / 24 * math.pi * 2) ** 2 + random.randint(-1800, 1800)), "revenue": 0}
        for hour in range(24)
    ]
    for row in hourly:
        row["revenue"] = round(row["trips"] * random.uniform(15, 19), 2)
    routes = [
        {"pickup_zone": 132, "pickup_name": "JFK Airport", "dropoff_zone": 138, "dropoff_name": "LaGuardia Airport", "trips": 18742, "average_fare": 52.18},
        {"pickup_zone": 138, "pickup_name": "LaGuardia Airport", "dropoff_zone": 132, "dropoff_name": "JFK Airport", "trips": 16381, "average_fare": 49.83},
        {"pickup_zone": 161, "pickup_name": "Midtown Center", "dropoff_zone": 237, "dropoff_name": "Upper East Side South", "trips": 12406, "average_fare": 18.42},
        {"pickup_zone": 237, "pickup_name": "Upper East Side South", "dropoff_zone": 161, "dropoff_name": "Midtown Center", "trips": 11880, "average_fare": 17.96},
        {"pickup_zone": 170, "pickup_name": "Murray Hill", "dropoff_zone": 234, "dropoff_name": "Union Sq", "trips": 10977, "average_fare": 16.31},
        {"pickup_zone": 234, "pickup_name": "Union Sq", "dropoff_zone": 170, "dropoff_name": "Murray Hill", "trips": 10381, "average_fare": 15.88},
    ]
    zones = [
        {"pickup_zone": zone, "zone_name": name, "borough": borough, "trips": trips, "revenue": round(trips * random.uniform(16, 20), 2), "average_distance": round(random.uniform(2.1, 5.8), 2)}
        for zone, name, borough, trips in [(132, "JFK Airport", "Queens", 94231), (138, "LaGuardia Airport", "Queens", 88104), (161, "Midtown Center", "Manhattan", 76324), (237, "Upper East Side South", "Manhattan", 70181), (170, "Murray Hill", "Manhattan", 65210), (234, "Union Sq", "Manhattan", 61904), (48, "Clinton East", "Manhattan", 57402), (79, "East Village", "Manhattan", 52881), (230, "Times Sq/Theatre District", "Manhattan", 50122), (164, "Midtown South", "Manhattan", 49211)]
    ]
    ml_results = [{
        "model": "Spark ML Linear Regression",
        "target": "fare_amount",
        "features": ["trip_distance", "duration_minutes", "pickup_hour", "passenger_count", "pickup_zone", "dropoff_zone"],
        "training_records": 120000,
        "testing_records": 30000,
        "rmse": 4.82,
        "mae": 2.71,
        "r2": 0.76,
        "predictions": [
            {"actual_fare": 18.50, "predicted_fare": 17.92, "distance": 3.20, "duration": 16.4},
            {"actual_fare": 42.00, "predicted_fare": 39.88, "distance": 12.10, "duration": 38.2},
            {"actual_fare": 9.50, "predicted_fare": 10.42, "distance": 1.40, "duration": 8.1},
        ],
    }]
    collections = {
        "overview": [overview],
        "hourly_demand": hourly,
        "top_routes": routes,
        "zone_performance": zones,
        "ml_results": ml_results,
        "metadata": [{
            "source": "Demo data modeled on NYC TLC Yellow Taxi Trip Records",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input": "scripts/seed_demo.py",
            "cleaned_records": overview["total_trips"],
            "engine": "Demo seed; replace with Apache Spark output",
        }],
    }
    for name, documents in collections.items():
        database[name].delete_many({})
        database[name].insert_many(documents)
    client.close()
    print("Demo analytics loaded into MongoDB")


if __name__ == "__main__":
    main()
