# Professor Demonstration Outline

1. **Motivation** — Show why demand and route analysis matters for urban transport.
2. **Data** — Explain the NYC TLC Yellow Taxi Parquet records and their scale.
3. **Architecture** — Walk through Spark → MongoDB → FastAPI → dashboard.
4. **Spark code** — Show the cleaning rules and distributed aggregations in `scripts/spark_analyze.py`.
5. **Live dashboard** — Explain the KPI cards, hourly chart, zone chart, and route table.
6. **Database/API** — Open `/docs` and demonstrate the REST endpoints.
7. **Conclusion** — State the main demand pattern and propose streaming/weather/ML extensions.
