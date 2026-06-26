import os
from pymongo import MongoClient, ASCENDING, DESCENDING

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        _db = _client["stocksawy"]
        _ensure_indexes()
    return _db


def _ensure_indexes():
    _db["articles"].create_index("timestamp", expireAfterSeconds=7 * 24 * 3600)
    _db["articles"].create_index([("timestamp", DESCENDING)])
    _db["signals"].create_index("signal_key", unique=True)
    _db["signals"].create_index([("timestamp", DESCENDING)])


def articles():
    return get_db()["articles"]


def signals():
    return get_db()["signals"]


def db():
    return get_db()
