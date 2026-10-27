from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.database import collection_documents, get_database, mongo_is_available

app = FastAPI(
    title="Urban Mobility Big Data Analytics API",
    description="Dashboard API backed by MongoDB results produced by Apache Spark.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    available = mongo_is_available()
    return {"status": "ok" if available else "degraded", "mongodb": available}


@app.get("/api/overview")
def overview() -> dict:
    documents = collection_documents("overview")
    if not documents:
        raise HTTPException(status_code=404, detail="No analytics found. Run seed_demo.py or spark_analyze.py.")
    return documents[0]


@app.get("/api/hourly-demand")
def hourly_demand() -> list[dict]:
    return collection_documents("hourly_demand")


@app.get("/api/top-routes")
def top_routes() -> list[dict]:
    return collection_documents("top_routes")


@app.get("/api/zone-performance")
def zone_performance() -> list[dict]:
    return collection_documents("zone_performance")


@app.get("/api/zone-map")
def zone_map() -> list[dict]:
    """Return named zone metrics used by the geographic map."""
    return collection_documents("zone_performance")


@app.get("/api/streaming-demand")
def streaming_demand() -> list[dict]:
    return collection_documents("streaming_demand")


@app.get("/api/streaming-status")
def streaming_status() -> dict:
    documents = collection_documents("stream_status")
    return documents[0] if documents else {"status": "waiting", "events_processed": 0}


@app.get("/api/ml-results")
def ml_results() -> dict:
    documents = collection_documents("ml_results")
    return documents[0] if documents else {"status": "not-trained", "message": "Run spark_analyze.py to train the model."}


@app.get("/api/metadata")
def metadata() -> dict:
    documents = collection_documents("metadata")
    return documents[0] if documents else {"source": "Not processed yet"}


@app.on_event("shutdown")
def close_mongodb() -> None:
    get_database().client.close()
