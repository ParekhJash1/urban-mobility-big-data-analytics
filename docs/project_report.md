# Urban Mobility Big Data Analytics

## 1. Abstract

This project presents a distributed analytics platform for NYC Yellow Taxi trip data. Apache Spark processes and cleans large Parquet files, computes demand and revenue insights, and stores compact analytical results in MongoDB. A FastAPI backend exposes the results to an interactive web dashboard.

## 2. Problem statement

Taxi operators need to understand when demand is highest, which areas and routes are most active, and how distance and duration influence revenue. Querying raw trip records directly for every dashboard request is slow and inefficient. This project creates a scalable processing pipeline and a user-facing analytics application.

## 3. Research questions

1. Which hours have the highest taxi demand?
2. Which pickup zones and routes are most popular?
3. What are the average fare, distance, duration, and total revenue?
4. How does distributed processing improve the handling of large trip files?

## 4. System architecture

```text
TLC Parquet files
      ↓
Apache Spark: read → clean → transform → aggregate
      ↓
MongoDB: overview, hourly_demand, top_routes, zone_performance
      ↓
FastAPI REST API
      ↓
HTML/CSS/JavaScript dashboard
```

## 5. Data processing

Invalid distances, fares, missing zones, and unrealistic trip durations are removed. Spark derives pickup hour and duration in minutes. The pipeline then performs distributed `groupBy` aggregations for hourly demand, route popularity, and zone performance.

## 6. Results

Run the project and paste screenshots from the dashboard here. Record the following values from the dashboard:

| Metric | Result |
|---|---|
| Valid trips | |
| Total revenue | |
| Average fare | |
| Average distance | |
| Busiest hour | |
| Busiest pickup zone | |

## 7. Conclusion and future work

The project demonstrates an end-to-end big data workflow from distributed processing to a web-based decision dashboard. Future improvements could include NYC taxi zone names and maps, weather integration, Kafka streaming, and a Spark ML model for fare prediction.
