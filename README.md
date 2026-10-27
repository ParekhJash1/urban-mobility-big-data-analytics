# Urban Mobility Big Data Analytics Dashboard

A university project demonstrating an end-to-end big data analytics system:

```text
NYC Taxi Parquet data -> Apache Spark ETL/analytics -> MongoDB -> FastAPI -> Web dashboard
```

The project analyzes taxi demand, trip distance, fares, and popular pickup/drop-off routes. It is designed to be easy to demonstrate locally while still using a genuinely large dataset and distributed processing.

## Technologies

- Apache Spark 3.5 / PySpark
- MongoDB
- FastAPI and Uvicorn
- Vanilla HTML/CSS/JavaScript
- Chart.js for dashboard visualizations
- Docker Compose for MongoDB

## Project structure

```text
big-data-taxi-analytics/
├── backend/
│   ├── main.py              # FastAPI application and REST endpoints
│   ├── database.py          # MongoDB connection and collection helpers
│   └── static/               # Frontend dashboard
├── data/raw/                 # Downloaded Parquet files (ignored by git)
├── scripts/
│   ├── download_data.py      # Downloads a public TLC data month
│   ├── seed_demo.py          # Creates immediate demo data in MongoDB
│   └── spark_analyze.py      # Spark ETL, aggregations, and MongoDB loading
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quick demo

Prerequisites: Python 3.10+ and Java 17+ for Spark. You can use Docker Desktop for MongoDB, or install MongoDB Community Server locally.

### 1. Start MongoDB

```bash
docker compose up -d mongodb
```

### 2. Create a Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Seed demo data

This makes the dashboard usable immediately, even before downloading the large dataset:

```bash
python scripts/seed_demo.py
```

### 4. Start the backend and frontend

```bash
uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000> in a browser. API documentation is available at <http://127.0.0.1:8000/docs>.

## Run the real Spark pipeline

Download one public TLC Yellow Taxi Parquet file:

```bash
python scripts/download_data.py --year 2024 --month 1
```

Run Spark locally:

```bash
python scripts/spark_analyze.py --input data/raw/yellow_tripdata_2024-01.parquet
```

The pipeline filters invalid records, derives trip duration and pickup hour, computes distributed aggregations, and loads compact dashboard-ready results into MongoDB. You can process more than one month by passing a directory or a glob of Parquet files:

```bash
python scripts/spark_analyze.py --input "data/raw/*.parquet"
```

For a larger demonstration, download several months and compare the Spark execution time and record counts.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service and MongoDB status |
| GET | `/api/overview` | KPI cards and processing metadata |
| GET | `/api/hourly-demand` | Trips by pickup hour |
| GET | `/api/top-routes` | Most frequent pickup/drop-off routes |
| GET | `/api/zone-performance` | Zone-level trip and revenue metrics |

## Suggested presentation storyline

1. **Problem:** Transport operators need to understand demand patterns and revenue by time and location.
2. **Data:** NYC TLC Yellow Taxi trip records, containing millions of trip observations.
3. **Architecture:** Spark distributes cleaning and aggregation; MongoDB stores query-friendly results; FastAPI exposes them to the dashboard.
4. **Analytics:** Peak hours, busiest routes, average fare, distance, duration, and revenue.
5. **Result:** An interactive dashboard that turns large raw files into decisions a transport manager can use.
6. **Future work:** Add weather data, a Spark ML fare prediction model, Kafka streaming, and a map visualization.

## Important notes

- The dashboard uses aggregated data in MongoDB rather than querying raw trips for every page request.
- The data download script uses the public NYC TLC data portal. Check the portal's current terms before publishing the project.
- Do not commit downloaded Parquet files or MongoDB credentials.
