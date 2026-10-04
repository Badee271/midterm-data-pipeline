from pymongo import ASCENDING, MongoClient
from config.settings import DB_NAME, MONGO_URI, COLLECTION_QUARANTINE, COLLECTION_RAW, COLLECTION_VALIDATED

_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client

def get_db():
    return get_client()[DB_NAME]

def setup_mongo_indexes():
    db = get_db()
    db[COLLECTION_VALIDATED].create_index([("order_id", ASCENDING)], unique=True, name="uq_order_id")
    db[COLLECTION_RAW].create_index([("run_id", ASCENDING)], name="ix_raw_run_id")
    db[COLLECTION_QUARANTINE].create_index([("run_id", ASCENDING)], name="ix_quarantine_run_id")

def close_mongo():
    global _client
    if _client is not None:
        _client.close()
        _client = None
