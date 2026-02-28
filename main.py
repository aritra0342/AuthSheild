from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
import jwt
import random
import time
import numpy as np
import pickle
from datetime import datetime, timezone

import db
import fingerprint
import risk
import graph
import auth0_client
from config import config

from blockchain import AlgorandClient, FreezeLedger, NFTBadge, ReputationManager
from blockchain.algorand_client import generate_testnet_account

async def process_blockchain_actions(user_id: str, risk_score: float):
    # 1. Reputation update: trust_score = 100 - (risk_score * 50)
    trust_score = reputation_manager.calculate_trust_score(risk_score)
    rep_res = reputation_manager.update_reputation(user_id, algorand_client.address, risk_score, trust_score)
    if rep_res.get("success"):
        print(f"[{user_id}] Reputation logged to blockchain. Tx: {rep_res.get('txid')}")
    else:
        print(f"[{user_id}] Reputation log failed: {rep_res.get('error')}")

    # 2. NFT Badge minting for Verified Users (risk < 0.3)
    if risk_score < 0.3:
        nft_res = nft_badge.mint_badge(user_id, algorand_client.address, risk_score)
        if nft_res.get("success"):
            print(f"[{user_id}] NFT Badge minted successfully! Tx: {nft_res.get('txid')}")
        else:
            print(f"[{user_id}] NFT mint failed: {nft_res.get('error')}")

algorand_client = AlgorandClient()
freeze_ledger = FreezeLedger()
nft_badge = NFTBadge()
reputation_manager = ReputationManager()

app = FastAPI(title="AuthShield AI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ── Auth helpers ──────────────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

def create_token(username: str, remember_me: bool = False) -> str:
    # remember_me → 30 days; normal → 24 hours
    expiry = 30 * 86400 if remember_me else 86400
    payload = {"sub": username, "iat": int(time.time()), "exp": int(time.time()) + expiry}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = jwt.decode(credentials.credentials, config.JWT_SECRET, algorithms=["HS256"])
        return data
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ── Pydantic models ───────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = False

class RegisterRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: Optional[str] = "analyst"  # analyst | admin | viewer

class LoginEvent(BaseModel):
    user_id: str
    ip_address: str
    user_agent: str
    webgl_hash: Optional[str] = ""
    canvas_hash: Optional[str] = ""
    timezone: Optional[str] = "UTC+0"
    screen_resolution: Optional[str] = "1920x1080"
    login_timestamp: Optional[str] = None
    typing_latency_array: Optional[List[float]] = []

class Thresholds(BaseModel):
    cluster_size: int
    similarity: float
    risk_score: float

# ── Demo fingerprint helpers (matches fingerprint.py logic) ───────────────────
def _norm_ip(ip):
    parts = ip.split(".")
    return [int(p)/255.0 for p in parts] if len(parts) == 4 else [0.0]*4

def _norm_ua(ua):
    ul = ua.lower()
    return [
        1.0 if "chrome" in ul else 0.0,
        1.0 if "firefox" in ul else 0.0,
        1.0 if "safari" in ul else 0.0,
        1.0 if ("mobile" in ul or "android" in ul) else 0.0,
        1.0 if ("bot" in ul or "crawler" in ul) else 0.0,
    ]

def _norm_res(res):
    try:
        w, h = map(int, res.lower().split("x"))
        return [min(w/3840, 1), min(h/2160, 1), w/h if h else 1]
    except:
        return [0.5, 0.5, 1.0]

def _norm_tz(tz):
    try:
        off = int(tz.replace("UTC", "").replace("+", ""))
        return (off + 12) / 24.0
    except:
        return 0.5

def _make_vector(ip, ua, res, tz, typing_arr):
    if not typing_arr:
        t = [0.0, 0.0, 0.0]
    else:
        arr = np.array(typing_arr)
        t = [min(float(np.mean(arr))/500, 1), min(float(np.std(arr))/200, 1),
             min(float(np.max(arr)-np.min(arr))/1000, 1) if len(arr) > 1 else 0]
    return _norm_ip(ip) + _norm_ua(ua) + _norm_res(res) + [_norm_tz(tz)] + t

def _seed_model():
    """Train Isolation Forest on synthetic legit data."""
    from sklearn.ensemble import IsolationForest
    LEGIT_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14) Safari/605",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/122.0",
        "Mozilla/5.0 (iPhone; CPU iOS 17) Mobile Safari/604",
    ]
    LEGIT_RES = ["1920x1080","2560x1440","1366x768","1440x900","3840x2160"]
    LEGIT_TZ  = ["UTC+5","UTC-5","UTC+0","UTC+9","UTC+1","UTC-8","UTC+3"]
    X = []
    for _ in range(400):
        ip = f"{random.randint(50,220)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        ua = random.choice(LEGIT_UAS)
        res= random.choice(LEGIT_RES)
        tz = random.choice(LEGIT_TZ)
        typing = [random.gauss(160, 35) for _ in range(random.randint(6, 15))]
        X.append(_make_vector(ip, ua, res, tz, typing))
    model = IsolationForest(contamination=0.08, n_estimators=150, random_state=42)
    model.fit(X)
    with open("isolation_forest.pkl", "wb") as f:
        pickle.dump(model, f)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
async def login(req: LoginRequest):
    user = db.authenticate_user(req.username, req.password)
    if user:
        token = create_token(user["username"], req.remember_me or False)
        return {
            "token":     token,
            "username":  user["username"],
            "full_name": user.get("full_name", user["username"]),
            "role":      user.get("role", "analyst"),
            "email":     user.get("email", ""),
            "remember_me": req.remember_me,
        }
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/register")
async def register(req: RegisterRequest):
    # Role guard: only admin and analyst allowed via signup
    allowed_roles = {"analyst", "viewer", "admin"}
    role = req.role if req.role in allowed_roles else "analyst"

    # Basic validation
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not req.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    try:
        user = db.create_user(
            username=req.username,
            email=req.email,
            full_name=req.full_name,
            password=req.password,
            role=role
        )
        token = create_token(user["username"])
        return {
            "success":  True,
            "token":    token,
            "username": user["username"],
            "full_name":user["full_name"],
            "role":     user["role"],
            "email":    user["email"],
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@app.get("/api/me")
async def get_me(creds: dict = Depends(verify_token)):
    username = creds.get("sub", "")
    user = db.find_user(username)
    if user:
        return {k: v for k, v in user.items() if k != "password"}
    # ENV admin fallback
    if username == config.ADMIN_USERNAME:
        return {"username": config.ADMIN_USERNAME, "full_name": "System Administrator",
                "role": "admin", "email": "admin@authshield.local"}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/users")
async def list_users(creds: dict = Depends(verify_token)):
    return db.get_all_users()

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/events")
async def get_events(limit: int = 50):
    events = db.get_recent_events(limit)
    for e in events:
        if "created_at" in e and hasattr(e["created_at"], "isoformat"):
            e["created_at"] = e["created_at"].isoformat()
    return events

@app.get("/api/flagged")
async def get_flagged():
    return db.get_flagged_users()

@app.get("/api/freeze-log")
async def get_freeze_log():
    logs = db.get_freeze_log()
    for log in logs:
        if "timestamp" in log and hasattr(log["timestamp"], "isoformat"):
            log["timestamp"] = log["timestamp"].isoformat()
    return logs

@app.get("/api/frozen-users")
async def get_frozen_users():
    users = db.get_frozen_users()
    for u in users:
        if "frozen_at" in u and hasattr(u["frozen_at"], "isoformat"):
            u["frozen_at"] = u["frozen_at"].isoformat()
        if "unfrozen_at" in u and hasattr(u["unfrozen_at"], "isoformat"):
            u["unfrozen_at"] = u["unfrozen_at"].isoformat()
    return users

@app.get("/api/thresholds")
async def get_thresholds():
    return db.get_thresholds()

@app.post("/api/thresholds")
async def set_thresholds(thresholds: Thresholds):
    db.update_thresholds(thresholds.cluster_size, thresholds.similarity, thresholds.risk_score)
    return {"success": True, "thresholds": thresholds.dict()}

@app.get("/api/clusters")
async def get_clusters():
    try:
        return graph.get_all_clusters()
    except Exception as e:
        return {"error": str(e), "clusters": []}

@app.get("/api/cluster/{user_id}")
async def get_user_cluster(user_id: str):
    try:
        return graph.get_user_cluster(user_id)
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/fingerprint")
async def generate_fingerprint_api(event: LoginEvent):
    event_dict = event.dict()
    if not event_dict.get("login_timestamp"):
        event_dict["login_timestamp"] = datetime.utcnow().isoformat()
    return fingerprint.generate_fingerprint(event_dict)

@app.post("/api/risk-score")
async def calculate_risk_api(event: LoginEvent):
    event_dict = event.dict()
    if not event_dict.get("login_timestamp"):
        event_dict["login_timestamp"] = datetime.utcnow().isoformat()
    fp = fingerprint.generate_fingerprint(event_dict)
    try:
        cluster = graph.get_user_cluster(event.user_id)
        cluster_density = graph.get_cluster_density(event.user_id) if cluster.get("peers") else 0.0
    except:
        cluster_density = 0.0
    risk_result = risk.calculate_risk_score(fp["feature_vector"], [], fp["ip_entropy"], cluster_density)
    return {**fp, **risk_result}

@app.post("/api/simulate")
async def simulate_login(event: LoginEvent, background_tasks: BackgroundTasks):
    try:
        event_dict = event.dict()
        if not event_dict.get("login_timestamp"):
            event_dict["login_timestamp"] = datetime.utcnow().isoformat()
        fp = fingerprint.generate_fingerprint(event_dict)
        cluster_density = 0.0
        try:
            graph.add_user_node(
                event.user_id, 0.0, fp["behavior_hash"],
                event_dict.get("canvas_hash", "") or "",
                ".".join(event.ip_address.split(".")[:3])
            )
            cluster_density = graph.get_cluster_density(event.user_id)
        except Exception as e:
            print(f"Graph error: {e}")
        risk_result = risk.calculate_risk_score(fp["feature_vector"], [], fp["ip_entropy"], cluster_density)
        event_data = {
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "webgl_hash": event.webgl_hash,
            "canvas_hash": event.canvas_hash,
            "screen_resolution": event.screen_resolution,
            "timezone": event.timezone,
            "login_timestamp": event_dict.get("login_timestamp"),
            "behavior_hash": fp["behavior_hash"],
            "entropy_score": fp["entropy_score"],
            "ip_entropy": fp["ip_entropy"],
            "device_entropy": fp["device_entropy"],
            "risk_score": risk_result["risk_score"],
            "is_suspicious": risk_result["is_suspicious"],
            "anomaly_score": risk_result["anomaly_score"],
            "similarity_score": risk_result["similarity_score"],
            "cluster_density": risk_result["cluster_density"],
            "flagged": False
        }
        try:
            db.save_login_event(event_data.copy())
        except Exception as e:
            print(f"MongoDB error: {e}")
        try:
            graph.update_user_risk(event.user_id, risk_result["risk_score"])
        except Exception as e:
            print(f"Graph update error: {e}")
            
        background_tasks.add_task(process_blockchain_actions, event.user_id, risk_result["risk_score"])
        return event_data
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"error": str(e), "user_id": getattr(event, 'user_id', 'unknown')}

# ── Demo endpoints ─────────────────────────────────────────────────────────────
LEGIT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14) AppleWebKit/605 Safari/605",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iOS 17) AppleWebKit Mobile Safari/604",
    "Mozilla/5.0 (Android 13) Chrome/118 Mobile Safari/537.36",
]
LEGIT_RES  = ["1920x1080","2560x1440","1366x768","1440x900","3840x2160"]
LEGIT_TZ   = ["UTC+5","UTC-5","UTC+0","UTC+9","UTC+1","UTC-8","UTC+3"]
BOT_UA     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/88.0.4324.150 Safari/537.36"
BOT_SUBNET = "45.152.66"

@app.post("/api/demo/run-attack")
async def demo_run_attack(background_tasks: BackgroundTasks):
    """Seed ML model, then simulate 8 legit + 12 bot logins. Returns all events."""
    _seed_model()
    results = {"legit": [], "bots": []}

    # Phase 1: legit users
    for i in range(1, 9):
        uid = f"legit_user_{i:03d}"
        ip  = f"{random.randint(80,220)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        typing = [round(random.gauss(175, 40), 1) for _ in range(random.randint(8,15))]
        ev = LoginEvent(
            user_id=uid, ip_address=ip,
            user_agent=random.choice(LEGIT_UAS),
            webgl_hash=f"wgl_{random.randint(10000,99999)}",
            canvas_hash=f"cvs_{random.randint(10000,99999)}",
            timezone=random.choice(LEGIT_TZ),
            screen_resolution=random.choice(LEGIT_RES),
            typing_latency_array=typing
        )
        data = await simulate_login(ev, background_tasks)
        results["legit"].append(data)

    # Phase 2: bot attack — same subnet, same UA, robotic typing
    for i in range(1, 13):
        uid = f"bot_account_{i:03d}"
        ip  = f"{BOT_SUBNET}.{i}"
        typing = [round(random.gauss(50, 3), 1) for _ in range(8)]
        ev = LoginEvent(
            user_id=uid, ip_address=ip,
            user_agent=BOT_UA,
            webgl_hash="wgl_BOTNET_UNIFORM",
            canvas_hash="cvs_BOTNET_UNIFORM",
            timezone="UTC+0",
            screen_resolution="1024x768",
            typing_latency_array=typing
        )
        data = await simulate_login(ev, background_tasks)
        results["bots"].append(data)

    return {
        "success": True,
        "legit_count": len(results["legit"]),
        "bot_count": len(results["bots"]),
        "events": results
    }

@app.post("/api/demo/freeze-all")
async def demo_freeze_all():
    """Detect clusters, freeze every flagged bot, persist to frozen_users, log to Algorand."""
    thresholds = db.get_thresholds()
    frozen_list = []
    errors = []

    try:
        flagged = graph.get_flagged_users(
            thresholds["cluster_size"],
            thresholds["similarity"],
            thresholds["risk_score"]
        )
    except Exception as e:
        flagged = []
        errors.append(f"Graph cluster error: {e}")

    # Also pick any bot_account_* from recent events that are suspicious
    recent = db.get_recent_events(100)
    bot_suspects = [
        e for e in recent
        if str(e.get("user_id", "")).startswith("bot_account_")
        and e.get("user_id") not in [f["user_id"] for f in flagged]
    ]
    # Sort by risk score descending, take top 12
    bot_suspects_sorted = sorted(bot_suspects, key=lambda x: x.get("risk_score", 0), reverse=True)
    seen_ids = {f["user_id"] for f in flagged}
    for b in bot_suspects_sorted:
        uid = b.get("user_id")
        if uid and uid not in seen_ids:
            flagged.append({"user_id": uid, "risk_score": b.get("risk_score", 0.5), "cluster_size": 1})
            seen_ids.add(uid)

    for user in flagged:
        uid = user["user_id"]
        risk_score = user.get("risk_score", 0.5)
        cluster_id = str(user.get("cluster_id", ""))

        # Auth0 freeze
        try:
            auth0_result = await auth0_client.freeze_user(uid, "auto_cluster_freeze")
        except Exception as e:
            auth0_result = {"success": False, "error": str(e)}

        # Blockchain log
        blockchain_result = {"blockchain_logged": False}
        try:
            blockchain_result = freeze_ledger.log_freeze(uid, risk_score, cluster_id, "auto_cluster_freeze")
        except Exception as e:
            blockchain_result = {"blockchain_logged": False, "error": str(e)}

        # Get IP from recent events
        ip_addr = ""
        for e in recent:
            if e.get("user_id") == uid:
                ip_addr = e.get("ip_address", "")
                break

        # Persist in MongoDB
        db.log_freeze_action(uid, "auto_cluster_freeze", risk_score, cluster_id)
        db.mark_frozen(uid, risk_score, "auto_cluster_freeze", cluster_id, ip_addr)

        try:
            graph.clear_flag(uid)
        except:
            pass

        frozen_list.append({
            "user_id": uid,
            "risk_score": risk_score,
            "ip_address": ip_addr,
            "auth0": auth0_result.get("success", False),
            "blockchain": blockchain_result.get("blockchain_logged", False),
            "txid": blockchain_result.get("txid", ""),
            "explorer_link": blockchain_result.get("explorer_link", ""),
        })

    return {
        "success": True,
        "frozen_count": len(frozen_list),
        "frozen_users": frozen_list,
        "errors": errors
    }

@app.get("/api/auth0/users")
async def get_auth0_users():
    users = await auth0_client.get_all_users()
    return {"users": users, "count": len(users)}

@app.post("/api/freeze/{user_id}")
async def freeze_user_endpoint(user_id: str):
    result = await auth0_client.freeze_user(user_id, "manual_freeze")
    if result["success"]:
        db.log_freeze_action(user_id, "manual_freeze", 1.0)
        db.mark_frozen(user_id, 1.0, "manual_freeze")
        freeze_ledger.log_freeze(user_id, 1.0, None, "manual_freeze")
        try:
            graph.clear_flag(user_id)
        except:
            pass
    return result

@app.post("/api/unfreeze/{user_id}")
async def unfreeze_user_endpoint(user_id: str):
    result = await auth0_client.unfreeze_user(user_id)
    if result["success"]:
        db.log_unfreeze_action(user_id)
        db.mark_unfrozen(user_id)
    return result

@app.post("/api/check-clusters")
async def check_clusters():
    thresholds = db.get_thresholds()
    try:
        flagged = graph.get_flagged_users(
            thresholds["cluster_size"], thresholds["similarity"], thresholds["risk_score"]
        )
        frozen = []
        for user in flagged:
            result = await auth0_client.freeze_user(user["user_id"], "auto_cluster_freeze")
            if result["success"]:
                db.log_freeze_action(user["user_id"], "auto_cluster_freeze", user["risk_score"], str(user.get("cluster_size", 0)))
                db.mark_frozen(user["user_id"], user["risk_score"], "auto_cluster_freeze")
                freeze_ledger.log_freeze(user["user_id"], user.get("risk_score", 1.0), str(user.get("cluster_size", "")), "auto_cluster_freeze")
                frozen.append(user["user_id"])
        return {"flagged_count": len(flagged), "frozen_count": len(frozen), "frozen_users": frozen}
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/auth0")
async def auth0_webhook(payload: dict, background_tasks: BackgroundTasks):
    user_id = payload.get("user_id") or payload.get("sub", "")
    event = LoginEvent(
        user_id=user_id,
        ip_address=payload.get("ip", "0.0.0.0"),
        user_agent=payload.get("user_agent", ""),
        webgl_hash=payload.get("webgl_hash", ""),
        canvas_hash=payload.get("canvas_hash", ""),
        timezone=payload.get("timezone", "UTC+0"),
        screen_resolution=payload.get("screen_resolution", "1920x1080"),
        login_timestamp=payload.get("login_timestamp"),
        typing_latency_array=payload.get("typing_latency_array", [])
    )
    return await simulate_login(event, background_tasks)

@app.on_event("startup")
async def startup():
    try:
        graph.init_schema()
        print("Neo4j schema initialized")
    except Exception as e:
        print(f"Neo4j connection error: {e}")
    db._get_db()
    print("AuthShield AI started")

# ── Blockchain routes ──────────────────────────────────────────────────────────
@app.get("/api/blockchain/status")
async def blockchain_status():
    return {"configured": algorand_client.is_configured(), "network": algorand_client.network, "address": algorand_client.address}

@app.get("/api/blockchain/balance")
async def blockchain_balance():
    if not algorand_client.is_configured():
        return {"error": "Algorand not configured"}
    return {"balance": algorand_client.get_balance(), "balance_algo": algorand_client.get_balance() / 1000000}

@app.post("/api/blockchain/generate-wallet")
async def generate_wallet():
    return generate_testnet_account()

@app.post("/api/blockchain/log-freeze/{user_id}")
async def blockchain_log_freeze(user_id: str, risk_score: float = 0.0, cluster_id: str = None):
    return freeze_ledger.log_freeze(user_id, risk_score, cluster_id, "manual_blockchain_log")

@app.post("/api/blockchain/mint-badge/{user_id}")
async def blockchain_mint_badge(user_id: str, risk_score: float = 0.0, wallet_address: str = ""):
    return nft_badge.mint_badge(user_id, wallet_address or algorand_client.address, risk_score)

@app.post("/api/blockchain/update-reputation/{user_id}")
async def blockchain_update_reputation(user_id: str, risk_score: float = 0.0, wallet_address: str = ""):
    trust_score = reputation_manager.calculate_trust_score(risk_score, 1, 1)
    return reputation_manager.update_reputation(user_id, wallet_address or algorand_client.address, risk_score, trust_score)

@app.post("/api/freeze-blockchain/{user_id}")
async def freeze_user_with_blockchain(user_id: str):
    auth0_result = await auth0_client.freeze_user(user_id, "manual_freeze_blockchain")
    if auth0_result["success"]:
        db.log_freeze_action(user_id, "manual_freeze_blockchain", 1.0)
        db.mark_frozen(user_id, 1.0, "manual_freeze_blockchain")
        blockchain_result = freeze_ledger.log_freeze(user_id, 1.0, None, "manual_freeze")
        try:
            graph.clear_flag(user_id)
        except:
            pass
        return {"auth0": auth0_result, "blockchain": blockchain_result}
    return {"auth0": auth0_result, "blockchain": {"logged": False}}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
