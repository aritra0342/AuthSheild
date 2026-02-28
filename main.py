from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
from datetime import datetime

import db
import fingerprint
import risk
import graph
import auth0_client
from config import config

from blockchain import AlgorandClient, FreezeLedger, NFTBadge, ReputationManager
from blockchain.algorand_client import generate_testnet_account

algorand_client = AlgorandClient()
freeze_ledger = FreezeLedger()
nft_badge = NFTBadge()
reputation_manager = ReputationManager()

app = FastAPI(title="AuthShield AI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

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

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/events")
async def get_events(limit: int = 50):
    events = db.get_recent_events(limit)
    for e in events:
        if "created_at" in e:
            e["created_at"] = e["created_at"].isoformat()
    return events

@app.get("/api/flagged")
async def get_flagged():
    flagged = db.get_flagged_users()
    return flagged

@app.get("/api/freeze-log")
async def get_freeze_log():
    logs = db.get_freeze_log()
    for log in logs:
        if "timestamp" in log:
            log["timestamp"] = log["timestamp"].isoformat()
    return logs

@app.get("/api/thresholds")
async def get_thresholds():
    return db.get_thresholds()

@app.post("/api/thresholds")
async def set_thresholds(thresholds: Thresholds):
    db.update_thresholds(
        thresholds.cluster_size,
        thresholds.similarity,
        thresholds.risk_score
    )
    return {"success": True, "thresholds": thresholds.dict()}

@app.get("/api/clusters")
async def get_clusters():
    try:
        clusters = graph.get_all_clusters()
        return clusters
    except Exception as e:
        return {"error": str(e), "clusters": []}

@app.get("/api/cluster/{user_id}")
async def get_user_cluster(user_id: str):
    try:
        cluster = graph.get_user_cluster(user_id)
        return cluster
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/fingerprint")
async def generate_fingerprint_api(event: LoginEvent):
    event_dict = event.dict()
    if not event_dict.get("login_timestamp"):
        event_dict["login_timestamp"] = datetime.utcnow().isoformat()
    
    fp = fingerprint.generate_fingerprint(event_dict)
    return fp

@app.post("/api/risk-score")
async def calculate_risk_api(event: LoginEvent):
    event_dict = event.dict()
    if not event_dict.get("login_timestamp"):
        event_dict["login_timestamp"] = datetime.utcnow().isoformat()
    
    fp = fingerprint.generate_fingerprint(event_dict)
    
    try:
        cluster = graph.get_user_cluster(event.user_id)
        cluster_vectors = []
        cluster_density = 0.0
        if cluster.get("peers"):
            cluster_density = graph.get_cluster_density(event.user_id)
    except:
        cluster_vectors = []
        cluster_density = 0.0
    
    risk_result = risk.calculate_risk_score(
        fp["feature_vector"],
        cluster_vectors,
        fp["ip_entropy"],
        cluster_density
    )
    
    return {
        **fp,
        **risk_result
    }

@app.post("/api/simulate")
async def simulate_login(event: LoginEvent):
    try:
        event_dict = event.dict()
        if not event_dict.get("login_timestamp"):
            event_dict["login_timestamp"] = datetime.utcnow().isoformat()
        
        fp = fingerprint.generate_fingerprint(event_dict)
        
        cluster_density = 0.0
        try:
            graph.add_user_node(
                event.user_id,
                0.0,
                fp["behavior_hash"],
                event_dict.get("canvas_hash", "") or "",
                ".".join(event.ip_address.split(".")[:3])
            )
            cluster_density = graph.get_cluster_density(event.user_id)
        except Exception as e:
            print(f"Graph error: {e}")
            cluster_density = 0.0
        
        risk_result = risk.calculate_risk_score(
            fp["feature_vector"],
            [],
            fp["ip_entropy"],
            cluster_density
        )
        
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
        
        return event_data
        
    except Exception as e:
        print(f"Simulate error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "user_id": getattr(event, 'user_id', 'unknown')}

@app.get("/api/auth0/users")
async def get_auth0_users():
    users = await auth0_client.get_all_users()
    return {"users": users, "count": len(users)}

@app.post("/api/freeze/{user_id}")
async def freeze_user_endpoint(user_id: str):
    result = await auth0_client.freeze_user(user_id, "manual_freeze")
    
    if result["success"]:
        db.log_freeze_action(user_id, "manual_freeze", 1.0)
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
    
    return result

@app.post("/api/check-clusters")
async def check_clusters():
    thresholds = db.get_thresholds()
    
    try:
        flagged = graph.get_flagged_users(
            thresholds["cluster_size"],
            thresholds["similarity"],
            thresholds["risk_score"]
        )
        
        frozen = []
        for user in flagged:
            result = await auth0_client.freeze_user(
                user["user_id"], 
                "auto_cluster_freeze"
            )
            if result["success"]:
                db.log_freeze_action(
                    user["user_id"],
                    "auto_cluster_freeze",
                    user["risk_score"],
                    str(user.get("cluster_size", 0))
                )
                frozen.append(user["user_id"])
        
        return {
            "flagged_count": len(flagged),
            "frozen_count": len(frozen),
            "frozen_users": frozen
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/auth0")
async def auth0_webhook(payload: dict):
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
    
    return await simulate_login(event)

@app.on_event("startup")
async def startup():
    try:
        graph.init_schema()
        print("Neo4j schema initialized")
    except Exception as e:
        print(f"Neo4j connection error: {e}")
    
    print("AuthShield AI started")

@app.get("/api/blockchain/status")
async def blockchain_status():
    return {
        "configured": algorand_client.is_configured(),
        "network": algorand_client.network,
        "address": algorand_client.address
    }

@app.get("/api/blockchain/balance")
async def blockchain_balance():
    if not algorand_client.is_configured():
        return {"error": "Algorand not configured. Set ALGORAND_MNEMONIC in .env"}
    return {
        "balance": algorand_client.get_balance(),
        "balance_algo": algorand_client.get_balance() / 1000000
    }

@app.post("/api/blockchain/generate-wallet")
async def generate_wallet():
    account = generate_testnet_account()
    return account

@app.post("/api/blockchain/log-freeze/{user_id}")
async def blockchain_log_freeze(user_id: str, risk_score: float = 0.0, cluster_id: str = None):
    result = freeze_ledger.log_freeze(user_id, risk_score, cluster_id, "manual_blockchain_log")
    return result

@app.post("/api/blockchain/mint-badge/{user_id}")
async def blockchain_mint_badge(user_id: str, risk_score: float = 0.0, wallet_address: str = ""):
    result = nft_badge.mint_badge(user_id, wallet_address or algorand_client.address, risk_score)
    return result

@app.post("/api/blockchain/update-reputation/{user_id}")
async def blockchain_update_reputation(user_id: str, risk_score: float = 0.0, wallet_address: str = ""):
    trust_score = reputation_manager.calculate_trust_score(risk_score, 1, 1)
    result = reputation_manager.update_reputation(
        user_id, 
        wallet_address or algorand_client.address, 
        risk_score, 
        trust_score
    )
    return result

@app.post("/api/freeze-blockchain/{user_id}")
async def freeze_user_with_blockchain(user_id: str):
    auth0_result = await auth0_client.freeze_user(user_id, "manual_freeze_blockchain")
    
    if auth0_result["success"]:
        db.log_freeze_action(user_id, "manual_freeze_blockchain", 1.0)
        
        blockchain_result = freeze_ledger.log_freeze(user_id, 1.0, None, "manual_freeze")
        
        try:
            graph.clear_flag(user_id)
        except:
            pass
        
        return {
            "auth0": auth0_result,
            "blockchain": blockchain_result
        }
    
    return {"auth0": auth0_result, "blockchain": {"logged": False}}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
