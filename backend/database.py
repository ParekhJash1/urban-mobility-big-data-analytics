import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "taxi_analytics")


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)


def get_database():
    return get_client()[MONGODB_DATABASE]


def mongo_is_available() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False


def collection_documents(collection_name: str) -> list[dict]:
    return list(get_database()[collection_name].find({}, {"_id": 0}))
