from pymongo import MongoClient
from datetime import datetime
from config import config

client = None
db = None
events_collection = None
freeze_log_collection = None
thresholds_collection = None
_in_memory_events = []
_in_memory_freeze_log = []
_in_memory_thresholds = {
    "cluster_size": config.CLUSTER_SIZE_THRESHOLD,
    "similarity": config.SIMILARITY_THRESHOLD,
    "risk_score": config.RISK_SCORE_THRESHOLD
}

def _get_db():
    global client, db, events_collection, freeze_log_collection, thresholds_collection
    if db is None:
        try:
            client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            db = client[config.MONGO_DB]
            events_collection = db["login_events"]
            freeze_log_collection = db["freeze_log"]
            thresholds_collection = db["thresholds"]
        except Exception as e:
            print(f"MongoDB connection failed, using in-memory storage: {e}")
            db = False
    return db is not False

def save_login_event(event_data: dict):
    event_data["created_at"] = datetime.utcnow()
    if _get_db():
        try:
            return events_collection.insert_one(event_data)
        except:
            pass
    _in_memory_events.append(event_data.copy())
    return True

def get_recent_events(limit: int = 50):
    if _get_db():
        try:
            return list(events_collection.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
        except:
            pass
    return _in_memory_events[-limit:]

def get_user_events(user_id: str):
    if _get_db():
        try:
            return list(events_collection.find({"user_id": user_id}, {"_id": 0}))
        except:
            pass
    return [e for e in _in_memory_events if e.get("user_id") == user_id]

def log_freeze_action(user_id: str, reason: str, risk_score: float, cluster_id: str = ""):
    entry = {
        "user_id": user_id,
        "reason": reason,
        "risk_score": risk_score,
        "cluster_id": cluster_id or "",
        "action": "freeze",
        "timestamp": datetime.utcnow()
    }
    if _get_db():
        try:
            return freeze_log_collection.insert_one(entry)
        except:
            pass
    _in_memory_freeze_log.append(entry)
    return True

def log_unfreeze_action(user_id: str):
    entry = {
        "user_id": user_id,
        "action": "unfreeze",
        "timestamp": datetime.utcnow()
    }
    if _get_db():
        try:
            return freeze_log_collection.insert_one(entry)
        except:
            pass
    _in_memory_freeze_log.append(entry)
    return True

def get_freeze_log(limit: int = 50):
    if _get_db():
        try:
            return list(freeze_log_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        except:
            pass
    return _in_memory_freeze_log[-limit:]

def get_thresholds():
    if _get_db():
        try:
            thresholds = thresholds_collection.find_one({"name": "active"})
            if thresholds:
                return {
                    "cluster_size": thresholds.get("cluster_size", config.CLUSTER_SIZE_THRESHOLD),
                    "similarity": thresholds.get("similarity", config.SIMILARITY_THRESHOLD),
                    "risk_score": thresholds.get("risk_score", config.RISK_SCORE_THRESHOLD)
                }
        except:
            pass
    return _in_memory_thresholds.copy()

def update_thresholds(cluster_size: int, similarity: float, risk_score: float):
    _in_memory_thresholds["cluster_size"] = cluster_size
    _in_memory_thresholds["similarity"] = similarity
    _in_memory_thresholds["risk_score"] = risk_score
    if _get_db():
        try:
            return thresholds_collection.update_one(
                {"name": "active"},
                {"$set": {
                    "cluster_size": cluster_size,
                    "similarity": similarity,
                    "risk_score": risk_score
                }},
                upsert=True
            )
        except:
            pass
    return True

def get_flagged_users():
    if _get_db():
        try:
            return list(events_collection.find({"flagged": True}, {"_id": 0}))
        except:
            pass
    return [e for e in _in_memory_events if e.get("flagged")]
