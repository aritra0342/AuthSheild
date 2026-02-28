from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from config import config

client = None
db = None
events_collection = None
freeze_log_collection = None
thresholds_collection = None
frozen_users_collection = None
users_collection = None

_in_memory_events = []
_in_memory_freeze_log = []
_in_memory_frozen_users = {}
_in_memory_users = {}
_in_memory_thresholds = {
    "cluster_size": config.CLUSTER_SIZE_THRESHOLD,
    "similarity": config.SIMILARITY_THRESHOLD,
    "risk_score": config.RISK_SCORE_THRESHOLD
}

import hashlib
import bcrypt

def _pre_hash(plain: str) -> bytes:
    """SHA-256 pre-hash → 32-byte digest, safely within bcrypt's 72-byte limit."""
    return hashlib.sha256(plain.encode('utf-8')).digest()


def _get_db():
    global client, db, events_collection, freeze_log_collection, thresholds_collection, frozen_users_collection, users_collection
    if db is None:
        try:
            client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            db = client[config.MONGO_DB]
            events_collection     = db["login_events"]
            freeze_log_collection = db["freeze_log"]
            thresholds_collection = db["thresholds"]
            frozen_users_collection = db["frozen_users"]
            users_collection      = db["users"]
            # Unique index on username/email
            try:
                users_collection.create_index([("username", ASCENDING)], unique=True)
                users_collection.create_index([("email", ASCENDING)], unique=True)
            except:
                pass
            print("✔ MongoDB Atlas connected")
        except Exception as e:
            print(f"MongoDB connection failed, using in-memory storage: {e}")
            db = False
    return db is not False

# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_pre_hash(plain), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pre_hash(plain), hashed.encode('utf-8'))
    except Exception:
        return False


# ── Users collection ──────────────────────────────────────────────────────────
def create_user(username: str, email: str, full_name: str, password: str, role: str = "analyst") -> dict:
    """Create a new user. Returns user dict or raises ValueError on duplicate."""
    hashed = hash_password(password)
    user = {
        "username":   username.lower().strip(),
        "email":      email.lower().strip(),
        "full_name":  full_name.strip(),
        "role":       role,           # admin | analyst | viewer
        "password":   hashed,
        "created_at": datetime.utcnow(),
        "last_login": None,
        "active":     True,
    }
    if _get_db():
        try:
            users_collection.insert_one(user)
        except DuplicateKeyError as e:
            if "username" in str(e):
                raise ValueError("Username already taken")
            elif "email" in str(e):
                raise ValueError("Email already registered")
            raise ValueError("Account already exists")
        except Exception as e:
            raise ValueError(f"Database error: {e}")
    else:
        key = user["username"]
        if key in _in_memory_users:
            raise ValueError("Username already taken")
        _in_memory_users[key] = user

    return {k: v for k, v in user.items() if k != "password"}

def find_user(username: str) -> dict | None:
    """Find a user by username (case-insensitive)."""
    key = username.lower().strip()
    if _get_db():
        try:
            return users_collection.find_one({"username": key}, {"_id": 0})
        except:
            pass
    return _in_memory_users.get(key)

def authenticate_user(username: str, password: str) -> dict | None:
    """
    Verify credentials. Checks MongoDB users first, then falls back to
    the ENV-based admin account. Returns user dict on success, None on failure.
    """
    # Check ENV admin first (always works, allows initial access)
    if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
        return {
            "username":  config.ADMIN_USERNAME,
            "full_name": "System Administrator",
            "role":      "admin",
            "email":     "admin@authshield.local",
        }
    # Check MongoDB users
    user = find_user(username)
    if user and user.get("active") and verify_password(password, user.get("password", "")):
        # Update last_login
        if _get_db():
            try:
                users_collection.update_one(
                    {"username": user["username"]},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
            except:
                pass
        return {k: v for k, v in user.items() if k != "password"}
    return None

def get_all_users() -> list:
    """Return all registered users (without passwords)."""
    if _get_db():
        try:
            users = list(users_collection.find({}, {"_id": 0, "password": 0}).sort("created_at", -1))
            for u in users:
                if u.get("created_at") and hasattr(u["created_at"], "isoformat"):
                    u["created_at"] = u["created_at"].isoformat()
                if u.get("last_login") and hasattr(u["last_login"], "isoformat"):
                    u["last_login"] = u["last_login"].isoformat()
            return users
        except:
            pass
    return [{k: v for k, v in u.items() if k != "password"} for u in _in_memory_users.values()]

# ── Login Events ──────────────────────────────────────────────────────────────
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
    return list(reversed(_in_memory_events[-limit:]))

def get_user_events(user_id: str):
    if _get_db():
        try:
            return list(events_collection.find({"user_id": user_id}, {"_id": 0}))
        except:
            pass
    return [e for e in _in_memory_events if e.get("user_id") == user_id]

def log_freeze_action(user_id: str, reason: str, risk_score: float, cluster_id: str = ""):
    entry = {
        "user_id":    user_id,
        "reason":     reason,
        "risk_score": risk_score,
        "cluster_id": cluster_id or "",
        "action":     "freeze",
        "timestamp":  datetime.utcnow()
    }
    if _get_db():
        try:
            return freeze_log_collection.insert_one(entry)
        except:
            pass
    _in_memory_freeze_log.append(entry)
    return True

def log_unfreeze_action(user_id: str):
    entry = {"user_id": user_id, "action": "unfreeze", "timestamp": datetime.utcnow()}
    if _get_db():
        try:
            return freeze_log_collection.insert_one(entry)
        except:
            pass
    _in_memory_freeze_log.append(entry)
    return True

def get_freeze_log(limit: int = 100):
    if _get_db():
        try:
            return list(freeze_log_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        except:
            pass
    return list(reversed(_in_memory_freeze_log[-limit:]))

# ── Frozen Users ──────────────────────────────────────────────────────────────
def mark_frozen(user_id: str, risk_score: float, reason: str, cluster_id: str = "", ip_address: str = ""):
    entry = {
        "user_id":    user_id,
        "risk_score": risk_score,
        "reason":     reason,
        "cluster_id": cluster_id or "",
        "ip_address": ip_address or "",
        "frozen_at":  datetime.utcnow(),
        "status":     "frozen"
    }
    if _get_db():
        try:
            frozen_users_collection.update_one(
                {"user_id": user_id},
                {"$set": entry},
                upsert=True
            )
            return True
        except:
            pass
    _in_memory_frozen_users[user_id] = entry
    return True

def mark_unfrozen(user_id: str):
    if _get_db():
        try:
            frozen_users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"status": "unfrozen", "unfrozen_at": datetime.utcnow()}}
            )
            return True
        except:
            pass
    if user_id in _in_memory_frozen_users:
        _in_memory_frozen_users[user_id]["status"] = "unfrozen"
    return True

def get_frozen_users():
    if _get_db():
        try:
            return list(frozen_users_collection.find({"status": "frozen"}, {"_id": 0}).sort("frozen_at", -1))
        except:
            pass
    return [v for v in _in_memory_frozen_users.values() if v.get("status") == "frozen"]

# ── Thresholds ────────────────────────────────────────────────────────────────
def get_thresholds():
    if _get_db():
        try:
            t = thresholds_collection.find_one({"name": "active"})
            if t:
                return {
                    "cluster_size": t.get("cluster_size", config.CLUSTER_SIZE_THRESHOLD),
                    "similarity":   t.get("similarity",   config.SIMILARITY_THRESHOLD),
                    "risk_score":   t.get("risk_score",   config.RISK_SCORE_THRESHOLD)
                }
        except:
            pass
    return _in_memory_thresholds.copy()

def update_thresholds(cluster_size: int, similarity: float, risk_score: float):
    _in_memory_thresholds.update({"cluster_size": cluster_size, "similarity": similarity, "risk_score": risk_score})
    if _get_db():
        try:
            return thresholds_collection.update_one(
                {"name": "active"},
                {"$set": {"cluster_size": cluster_size, "similarity": similarity, "risk_score": risk_score}},
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
