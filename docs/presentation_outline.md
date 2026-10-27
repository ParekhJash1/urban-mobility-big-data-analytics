# Professor Demonstration Outline

1. **Motivation** — Show why demand and route analysis matters for urban transport.
2. **Data** — Explain the NYC TLC Yellow Taxi Parquet records and their scale.
3. **Architecture** — Walk through Spark → MongoDB → FastAPI → dashboard.
4. **Spark code** — Show the cleaning rules and distributed aggregations in `scripts/spark_analyze.py`.
5. **Map** — Click a named taxi zone and explain the geographic demand view.
6. **Streaming** — Run `scripts/stream_demand.py` and show live events in MongoDB and the dashboard.
7. **Database/API** — Open `/docs` and demonstrate the REST endpoints.
8. **Conclusion** — State the main demand pattern and discuss Spark ML/Kafka extensions.
