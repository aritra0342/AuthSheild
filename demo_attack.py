"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              AuthShield AI — Botnet Attack Demonstration                    ║
║  Phases: 0-seed model → 1-legit users → 2-botnet attack → 3-detect → 4-freeze
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python demo_attack.py                          # default: localhost:8000
    python demo_attack.py --host http://x.x.x.x:8000
    python demo_attack.py --skip-legit             # jump straight to attack
    python demo_attack.py --no-freeze              # detect but do not freeze
    python demo_attack.py --bots 20 --legit 15    # custom counts

Requires: httpx  (already in requirements.txt)  Python ≥ 3.10
"""

import argparse
import random
import time
import sys
import numpy as np
import pickle
import os

# ─── ANSI colours ─────────────────────────────────────────────────────────────
R = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
MAG    = "\033[95m"
CYAN   = "\033[96m"
BG_RED   = "\033[41m"
BG_GREEN = "\033[42m"
BG_BLUE  = "\033[44m"

def c(col, txt):  return f"{col}{txt}{R}"
def b(txt):       return f"{BOLD}{txt}{R}"

def banner():
    print()
    print(c(CYAN,"  ╔══════════════════════════════════════════════════════════╗"))
    print(c(CYAN,"  ║") + b(c(RED,  "   🛡️  AuthShield AI — Botnet Attack Simulation       ")) + c(CYAN,"║"))
    print(c(CYAN,"  ╚══════════════════════════════════════════════════════════╝"))
    print()

def section(title, col=BLUE):
    pad = (58 - len(title)) // 2
    print()
    print(c(col, "  ┌" + "─"*58 + "┐"))
    print(c(col, f"  │{'':{pad}}") + b(title) + c(col, f"{'':>{58-len(title)-pad}}│"))
    print(c(col, "  └" + "─"*58 + "┘"))

def ts():
    from datetime import datetime, timezone
    return c(DIM, datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3])

def risk_bar(score: float, w: int = 18) -> str:
    filled = int(score * w)
    bar    = "█" * filled + "░" * (w - filled)
    col    = GREEN if score < 0.40 else YELLOW if score < 0.65 else RED
    return c(col, bar) + f" {score:.3f}"

def row(label, ip, risk, sus, frozen=False):
    sus_tag = c(RED, " ⚠ SUSPICIOUS") if sus else c(GREEN, " ✔ OK")
    frz_tag = c(BG_RED, " 🔒 FROZEN ") if frozen else ""
    print(f"  {ts()}  {c(MAG, label):<30}  IP:{c(YELLOW, ip):<16}  "
          f"Risk:{risk_bar(risk)}{sus_tag}{frz_tag}")

# ─── HTTP helpers ──────────────────────────────────────────────────────────────
import httpx

def post(cl: httpx.Client, url: str, body: dict) -> dict:
    try:
        r = cl.post(url, json=body, timeout=20)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": str(e)}
    except httpx.RequestError as e:
        return {"error": f"Connection: {e}"}

def get(cl: httpx.Client, url: str) -> dict:
    try:
        r = cl.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ─── Fingerprint helpers (local, mirrors fingerprint.py) ─────────────────────
def _norm_ip(ip):
    parts = ip.split(".")
    return [int(p)/255.0 for p in parts] if len(parts) == 4 else [0]*4

def _norm_ua(ua):
    ul = ua.lower()
    return [
        1.0 if "chrome"  in ul else 0.0,
        1.0 if "firefox" in ul else 0.0,
        1.0 if "safari"  in ul else 0.0,
        1.0 if ("mobile" in ul or "android" in ul) else 0.0,
        1.0 if ("bot" in ul or "crawler" in ul) else 0.0,
    ]

def _norm_res(res):
    try:
        w, h = map(int, res.lower().split("x"))
        return [min(w/3840,1), min(h/2160,1), w/h if h else 1]
    except:
        return [0.5, 0.5, 1.0]

def _norm_tz(tz):
    try:
        off = int(tz.replace("UTC","").replace("+",""))
        return (off+12)/24.0
    except:
        return 0.5

def _norm_typing(arr):
    if not arr: return [0.0, 0.0, 0.0]
    a = np.array(arr)
    return [min(float(np.mean(a))/500,1), min(float(np.std(a))/200,1),
            min(float(np.max(a)-np.min(a))/1000,1) if len(a)>1 else 0]

def make_vector(ip, ua, res, tz, typing):
    return _norm_ip(ip) + _norm_ua(ua) + _norm_res(res) + [_norm_tz(tz)] + _norm_typing(typing)

# ─── Phase 0 : Seed the Isolation Forest ──────────────────────────────────────
LEGIT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14) AppleWebKit/605 Safari/605",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iOS 17_0) AppleWebKit Mobile Safari/604",
    "Mozilla/5.0 (iPad; CPU OS 17) AppleWebKit Mobile/15E148 Safari/604",
    "Mozilla/5.0 (Android 13; Mobile) Chrome/118 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0) Firefox/120.0 Gecko/20100101",
]
LEGIT_RES = ["1920x1080","2560x1440","1366x768","1440x900","3840x2160","1280x800","2560x1600"]
LEGIT_TZ  = ["UTC+5","UTC-5","UTC+0","UTC+9","UTC+1","UTC-8","UTC+3","UTC+8","UTC-3"]
BOT_UA  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/88.0.4324.150 Safari/537.36"
BOT_RES = "1024x768"
BOT_TZ  = "UTC+0"
BOT_SUBNET = "45.152.66"

def phase_seed(n_samples: int = 300):
    section("PHASE 0 — Training Anomaly Detection Model", BLUE)
    print(c(DIM, f"  Building baseline from {n_samples} synthetic legit fingerprints..."))

    from sklearn.ensemble import IsolationForest
    X = []
    for _ in range(n_samples):
        ip = f"{random.randint(50,220)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        ua = random.choice(LEGIT_UAS)
        res= random.choice(LEGIT_RES)
        tz = random.choice(LEGIT_TZ)
        typing = [random.gauss(160, 35) for _ in range(random.randint(6,15))]
        X.append(make_vector(ip, ua, res, tz, typing))

    model = IsolationForest(contamination=0.08, n_estimators=150, random_state=42)
    model.fit(X)
    with open("isolation_forest.pkl", "wb") as f:
        pickle.dump(model, f)

    print(c(GREEN, f"  ✔ Model trained on {n_samples} samples — isolation_forest.pkl written"))
    print(c(DIM, "  The model now knows what 'normal' logins look like.\n"))

# ─── Phase 1 : Legit traffic ──────────────────────────────────────────────────
def phase_legit(cl: httpx.Client, base: str, n: int):
    section("PHASE 1 — Legitimate Users Logging In", GREEN)
    print(c(DIM, f"  Simulating {n} real users with diverse devices & locations...\n"))
    results = []
    for i in range(1, n+1):
        uid  = f"legit_user_{i:03d}"
        ip   = f"{random.randint(80,220)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        typing = [round(random.gauss(175, 40), 1) for _ in range(random.randint(8,15))]
        payload = {
            "user_id": uid,
            "ip_address": ip,
            "user_agent": random.choice(LEGIT_UAS),
            "webgl_hash":  f"wgl_{random.randint(10000,99999)}",
            "canvas_hash": f"cvs_{random.randint(10000,99999)}",
            "timezone": random.choice(LEGIT_TZ),
            "screen_resolution": random.choice(LEGIT_RES),
            "typing_latency_array": typing,
        }
        data = post(cl, f"{base}/api/simulate", payload)
        if "error" in data:
            print(c(RED, f"  ✗ {data['error']}")); return []
        risk = data.get("risk_score", 0)
        row(uid, ip, risk, data.get("is_suspicious", False))
        results.append(data)
        time.sleep(0.2)

    avg = sum(r.get("risk_score",0) for r in results)/len(results) if results else 0
    print(f"\n  {c(GREEN,'✔')} Average risk score (legit users): {b(f'{avg:.4f}')}")
    return results

# ─── Phase 2 : Botnet attack ──────────────────────────────────────────────────
def phase_botnet(cl: httpx.Client, base: str, n: int):
    section("PHASE 2 — 🤖  Botnet Attack Launched", RED)
    print(c(DIM, f"  {n} bot accounts — same /24 subnet · identical UA · robotic typing\n"))
    results = []
    for i in range(1, n+1):
        uid  = f"bot_account_{i:03d}"
        ip   = f"{BOT_SUBNET}.{i}"
        # Robotic typing: extremely uniform intervals, ~50ms (automated tool)
        typing = [round(random.gauss(50, 3), 1) for _ in range(8)]
        payload = {
            "user_id":           uid,
            "ip_address":        ip,
            "user_agent":        BOT_UA,
            "webgl_hash":        "wgl_BOTNET_UNIFORM",
            "canvas_hash":       "cvs_BOTNET_UNIFORM",
            "timezone":          BOT_TZ,
            "screen_resolution": BOT_RES,
            "typing_latency_array": typing,
        }
        data = post(cl, f"{base}/api/simulate", payload)
        if "error" in data:
            print(c(RED, f"  ✗ {data['error']}")); return []
        risk = data.get("risk_score", 0)
        row(uid, ip, risk, data.get("is_suspicious", False))
        results.append({"uid": uid, **data})
        time.sleep(0.12)

    avg = sum(r.get("risk_score",0) for r in results)/len(results) if results else 0
    sus = sum(1 for r in results if r.get("is_suspicious"))
    print(f"\n  {c(RED,'⚠')} Average risk score (botnet): {b(c(RED,f'{avg:.4f}'))}")
    print(f"  {c(RED,'⚠')} Flagged as suspicious individually: {b(c(RED,str(sus)))}/{n}")
    return results

# ─── Phase 3 : Cluster detection ──────────────────────────────────────────────
def phase_detect(cl: httpx.Client, base: str):
    section("PHASE 3 — Graph Cluster Detection (Neo4j)", YELLOW)
    print(c(DIM, "  Scanning user graph for coordinated login clusters...\n"))
    time.sleep(0.4)

    # Trigger cluster check
    check = post(cl, f"{base}/api/check-clusters", {})
    flagged_n = check.get("flagged_count", 0)
    frozen_n  = check.get("frozen_count",  0)
    frozen_ids= check.get("frozen_users",  [])

    if "error" not in check:
        print(f"  {c(CYAN,'◉')} Cluster scan complete:")
        print(f"     Flagged accounts : {b(c(RED, str(flagged_n)))}")
        print(f"     Auto-frozen (Auth0): {b(c(MAG, str(frozen_n)))}")
        if frozen_ids:
            preview = ", ".join(frozen_ids[:5])
            if len(frozen_ids) > 5: preview += f" … +{len(frozen_ids)-5} more"
            print(f"     {c(DIM,'Frozen IDs:')} {preview}")
    else:
        print(c(YELLOW, f"  ℹ Cluster check: {check.get('error','no response')}"))

    # Also fetch raw cluster list
    clusters_resp = get(cl, f"{base}/api/clusters")
    cluster_list  = clusters_resp if isinstance(clusters_resp, list) else clusters_resp.get("clusters", [])
    if cluster_list:
        print(f"\n  {b(str(len(cluster_list)))} cluster(s) in graph:\n")
        for idx, cl_data in enumerate(cluster_list, 1):
            size    = cl_data.get("cluster_size", cl_data.get("size", "?"))
            avg_r   = cl_data.get("avg_risk_score", cl_data.get("risk", 0))
            members = cl_data.get("members", cl_data.get("users", []))
            col     = RED if avg_r > 0.6 else YELLOW if avg_r > 0.3 else CYAN
            print(f"    {c(col, f'Cluster #{idx}')}  "
                  f"size={b(str(size))}  avg_risk={risk_bar(avg_r, 10)}")
            if members:
                preview = ", ".join(str(m) for m in members[:4])
                if len(members) > 4: preview += f" … +{len(members)-4}"
                print(f"      {c(DIM,'members:')} {preview}")
    return frozen_ids

# ─── Phase 4 : Manual freeze with blockchain ──────────────────────────────────
def phase_freeze(cl: httpx.Client, base: str, bot_results: list, do_freeze: bool):
    section("PHASE 4 — Manual Freeze + Algorand Audit Trail", MAG)

    # Pick top-risk bots
    sorted_bots = sorted(bot_results, key=lambda r: r.get("risk_score",0), reverse=True)
    targets = sorted_bots[:min(6, len(sorted_bots))]

    print(c(DIM, f"  Freezing top-{len(targets)} highest-risk accounts with blockchain logging...\n"))

    frozen_count = 0
    chain_count  = 0
    for entry in targets:
        uid = entry["uid"]
        if do_freeze:
            print(f"  {ts()}  Locking {c(YELLOW, uid)} ...", end="  ", flush=True)
            result    = post(cl, f"{base}/api/freeze-blockchain/{uid}", {})
            auth_ok   = result.get("auth0",       {}).get("success",          False)
            chain_ok  = result.get("blockchain",  {}).get("blockchain_logged", False)
            txid      = result.get("blockchain",  {}).get("txid", "")
            link      = result.get("blockchain",  {}).get("explorer_link", "")

            a_str = c(GREEN,"Auth0 ✔") if auth_ok  else c(RED,"Auth0 ✗ (not configured)")
            c_str = c(GREEN,"Algorand ✔") if chain_ok else c(YELLOW,"Algorand ─ (no mnemonic set)")
            print(f"{a_str}  {c_str}")
            if txid:
                print(f"           {c(DIM,'└─ txid:')} {c(CYAN, txid[:22])}…")
                print(f"           {c(DIM,'└─ link:')} {c(DIM, link)}")
            if auth_ok:  frozen_count += 1
            if chain_ok: chain_count  += 1
        else:
            print(f"  {c(YELLOW,'⏭')} (--no-freeze) Would freeze {c(YELLOW, uid)}")
        time.sleep(0.15)
    return frozen_count, chain_count

# ─── Summary printout ─────────────────────────────────────────────────────────
def summary(legit, bots, frozen, on_chain):
    section("FINAL REPORT — AuthShield Detection Summary", CYAN)
    l_avg  = sum(r.get("risk_score",0) for r in legit)/len(legit) if legit else 0
    b_avg  = sum(r.get("risk_score",0) for r in bots) /len(bots)  if bots  else 0
    b_sus  = sum(1 for r in bots if r.get("is_suspicious"))

    print(f"  {c(DIM,'◦')} Legit users simulated      {b(str(len(legit)))}")
    print(f"  {c(DIM,'◦')} Avg risk — legit            {b(c(GREEN, f'{l_avg:.4f}'))}")
    print(f"  {c(DIM,'◦')} Bot accounts simulated      {b(str(len(bots)))}")
    print(f"  {c(DIM,'◦')} Avg risk — botnet           {b(c(RED,   f'{b_avg:.4f}'))}")
    print(f"  {c(DIM,'◦')} Risk Δ (bot − legit)        {b(c(YELLOW,f'{b_avg-l_avg:+.4f}'))}")
    print(f"  {c(DIM,'◦')} Suspicious flags            {b(c(RED if b_sus else GREEN, str(b_sus)))}")
    print(f"  {c(DIM,'◦')} Accounts frozen (Auth0)     {b(c(MAG,  str(frozen)))}")
    print(f"  {c(DIM,'◦')} Events on Algorand chain    {b(c(CYAN, str(on_chain)))}")
    print()

    if frozen > 0:
        print(c(BG_GREEN, b(f"  ✔  ATTACK NEUTRALISED  —  {frozen} bot account(s) frozen in Auth0  ")))
    elif b_sus > 0:
        print(c(BG_RED, b(f"  ⚠  {b_sus} BOT(S) DETECTED  —  Auth0 not connected (configure creds)  ")))
    elif b_avg > l_avg + 0.01:
        print(c(YELLOW, b(f"  ℹ  Risk differential detected (+{b_avg-l_avg:.3f}). Bots identified at graph level.")))
    else:
        print(c(YELLOW,  "  ℹ  Tune RISK_SCORE_THRESHOLD lower or run --seed-model for more contrast."))
    print()

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="AuthShield AI — Botnet Demo")
    ap.add_argument("--host",       default="http://localhost:8000")
    ap.add_argument("--bots",       type=int,   default=12)
    ap.add_argument("--legit",      type=int,   default=8)
    ap.add_argument("--skip-legit", action="store_true")
    ap.add_argument("--no-freeze",  action="store_true")
    ap.add_argument("--delay",      type=float, default=0.0)
    args = ap.parse_args()

    banner()
    print(f"  Target : {b(c(CYAN,  args.host))}")
    print(f"  Config : {b(str(args.bots))} bots  |  {b(str(args.legit))} legit users")
    print()

    # ── Phase 0 : seed model locally ──────────────────────────────────────────
    phase_seed(n_samples=400)

    # ── Health check ──────────────────────────────────────────────────────────
    print(c(DIM, "  Connecting to AuthShield API..."), end=" ", flush=True)
    with httpx.Client() as cl:
        health = get(cl, f"{args.host}/api/health")
        if "error" in health:
            print(c(RED, "✗"))
            print(c(RED,    f"\n  Cannot reach {args.host}"))
            print(c(YELLOW, "  → Start the server first:  uvicorn main:app --reload\n"))
            sys.exit(1)
        print(c(GREEN, f"✔  server is {health.get('status','up')}"))

        legit_res = []
        if not args.skip_legit:
            legit_res = phase_legit(cl, args.host, args.legit)
            if args.delay: time.sleep(args.delay)

        bot_res = phase_botnet(cl, args.host, args.bots)
        if args.delay: time.sleep(args.delay)

        phase_detect(cl, args.host)
        if args.delay: time.sleep(args.delay)

        frozen, on_chain = phase_freeze(cl, args.host, bot_res, not args.no_freeze)
        summary(legit_res, bot_res, frozen, on_chain)

if __name__ == "__main__":
    main()
