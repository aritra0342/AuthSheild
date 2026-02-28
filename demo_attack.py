"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  AuthShield AI — Botnet Attack Demo                         ║
║  Simulates legitimate users, then coord inates a botnet and shows detection  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python demo_attack.py                          # default: localhost:8000
    python demo_attack.py --host http://x.x.x.x:8000
    python demo_attack.py --skip-legit             # jump straight to attack
    python demo_attack.py --no-freeze              # detect but do not freeze

Requires:  httpx  (already in requirements.txt)
"""

import argparse
import random
import time
import json
import sys
import httpx
from datetime import datetime, timezone

# ─── ANSI colours ─────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_BLUE  = "\033[44m"

def c(color, text): return f"{color}{text}{RESET}"
def bold(text):     return f"{BOLD}{text}{RESET}"
def banner():
    lines = [
        "",
        c(CYAN, "  ╔══════════════════════════════════════════════════════╗"),
        c(CYAN, "  ║") + bold(c(RED, "   🛡️  AuthShield AI — Botnet Attack Simulation   ")) + c(CYAN, "  ║"),
        c(CYAN, "  ╚══════════════════════════════════════════════════════╝"),
        "",
    ]
    print("\n".join(lines))

def section(title, color=BLUE):
    width = 56
    pad   = (width - len(title) - 4) // 2
    print()
    print(c(color, "  ┌" + "─" * (width) + "┐"))
    print(c(color, f"  │{'':>{pad}}") + bold(f" {title} ") + c(color, f"{'':>{width-len(title)-pad-3}}│"))
    print(c(color, "  └" + "─" * (width) + "┘"))

def risk_bar(score: float, width: int = 20) -> str:
    filled = int(score * width)
    bar    = "█" * filled + "░" * (width - filled)
    if score < 0.35:
        color = GREEN
    elif score < 0.65:
        color = YELLOW
    else:
        color = RED
    return c(color, bar) + f" {score:.3f}"

def timestamp() -> str:
    return c(DIM, datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3])

def print_event(label: str, uid: str, ip: str, risk: float, suspicious: bool, frozen: bool = False):
    sus_tag   = c(RED, " ⚠ SUSPICIOUS") if suspicious else c(GREEN, " ✔ OK")
    frz_tag   = c(BG_RED, " 🔒 FROZEN ") if frozen else ""
    print(f"  {timestamp()}  {c(MAGENTA, label):<30}  "
          f"IP:{c(YELLOW, ip):<16}  "
          f"Risk:{risk_bar(risk, 12)}{sus_tag}{frz_tag}")

def post(client: httpx.Client, url: str, payload: dict) -> dict:
    try:
        r = client.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": str(e)}
    except httpx.RequestError as e:
        return {"error": f"Connection failed: {e}"}

def get(client: httpx.Client, url: str) -> dict:
    try:
        r = client.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ─── User-agent pools ─────────────────────────────────────────────────────────
LEGIT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605.1 Mobile Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0) AppleWebKit/605.1 Mobile/15E148 Safari/604.1",
]
# Botnet UA: same chrome build — classic botnet fingerprint
BOT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/88.0.4324.150 Safari/537.36"

LEGIT_RESOLUTIONS = ["1920x1080", "2560x1440", "1366x768", "1440x900", "3840x2160"]
BOT_RESOLUTION    = "1024x768"   # suspiciously old

LEGIT_TIMEZONES = ["UTC+5", "UTC-5", "UTC+0", "UTC+9", "UTC+1", "UTC-8", "UTC+3"]
BOT_TIMEZONE    = "UTC+0"        # all bots same timezone

# ─── Simulate a single login ──────────────────────────────────────────────────
def simulate_login(client: httpx.Client, base: str, payload: dict) -> dict:
    return post(client, f"{base}/api/simulate", payload)

# ─── Phase 1 : Legitimate traffic ─────────────────────────────────────────────
def phase_legit(client: httpx.Client, base: str, count: int = 8):
    section("PHASE 1 — Legitimate Users Logging In", GREEN)
    print(c(DIM, f"  Simulating {count} real users with diverse fingerprints...\n"))
    results = []
    for i in range(1, count + 1):
        uid  = f"legit_user_{i:03d}"
        ip   = f"{random.randint(80,220)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        ua   = random.choice(LEGIT_UAS)
        res  = random.choice(LEGIT_RESOLUTIONS)
        tz   = random.choice(LEGIT_TIMEZONES)
        # Realistic typing latency: ~100–300 ms per key
        typing = [round(random.gauss(180, 40), 1) for _ in range(random.randint(8, 15))]

        payload = {
            "user_id": uid,
            "ip_address": ip,
            "user_agent": ua,
            "webgl_hash": f"wgl_{random.randint(10000,99999)}",
            "canvas_hash": f"cvs_{random.randint(10000,99999)}",
            "timezone": tz,
            "screen_resolution": res,
            "typing_latency_array": typing,
        }
        data = simulate_login(client, base, payload)
        if "error" in data:
            print(c(RED, f"  ✗ Server error: {data['error']}"))
            return []

        risk  = data.get("risk_score", 0)
        sus   = data.get("is_suspicious", False)
        print_event(uid, uid, ip, risk, sus)
        results.append(data)
        time.sleep(0.25)

    avg_risk = sum(r.get("risk_score", 0) for r in results) / len(results) if results else 0
    print(f"\n  {c(GREEN, '✔')} Avg risk score for legit users: {bold(f'{avg_risk:.4f}')}")
    return results

# ─── Phase 2 : Botnet attack ───────────────────────────────────────────────────
def phase_botnet(client: httpx.Client, base: str, bot_count: int = 12):
    section("PHASE 2 — Botnet Attack Incoming 🤖", RED)
    print(c(DIM, f"  Launching {bot_count} bot accounts from same /24 subnet...\n"))

    # All bots come from 45.152.x.x — a single purchased subnet
    BOT_SUBNET = "45.152.66"
    results = []
    for i in range(1, bot_count + 1):
        uid = f"bot_account_{i:03d}"
        ip  = f"{BOT_SUBNET}.{i}"          # sequential IPs in same /24
        # Suspiciously uniform typing — bots type at exactly the same speed
        typing = [round(random.gauss(52, 2), 1) for _ in range(8)]

        payload = {
            "user_id": uid,
            "ip_address": ip,
            "user_agent": BOT_UA,           # same UA for all bots
            "webgl_hash": "wgl_BOTNET",     # identical hardware hash
            "canvas_hash": "cvs_BOTNET",    # identical canvas hash
            "timezone": BOT_TIMEZONE,
            "screen_resolution": BOT_RESOLUTION,
            "typing_latency_array": typing,
        }
        data = simulate_login(client, base, payload)
        if "error" in data:
            print(c(RED, f"  ✗ Server error: {data['error']}"))
            return []

        risk = data.get("risk_score", 0)
        sus  = data.get("is_suspicious", False)
        print_event(uid, uid, ip, risk, sus)
        results.append({"uid": uid, **data})
        time.sleep(0.15)

    avg_risk = sum(r.get("risk_score", 0) for r in results) / len(results) if results else 0
    print(f"\n  {c(RED, '⚠')} Avg risk score for botnet: {bold(c(RED, f'{avg_risk:.4f}'))}")
    return results

# ─── Phase 3 : Cluster detection ──────────────────────────────────────────────
def phase_detect(client: httpx.Client, base: str):
    section("PHASE 3 — Cluster Detection Engine Running", YELLOW)
    print(c(DIM, "  Scanning Neo4j graph for coordinated clusters...\n"))
    time.sleep(0.5)

    clusters = get(client, f"{base}/api/clusters")
    if "error" in clusters:
        print(c(RED, f"  ✗ Cluster API error: {clusters['error']}"))
        return []

    cluster_list = clusters if isinstance(clusters, list) else clusters.get("clusters", [])
    if not cluster_list:
        print(c(YELLOW, "  ℹ No clusters returned (Neo4j may not be running). Showing flagged users instead."))
        return []

    print(f"  {c(CYAN, bold(str(len(cluster_list))))} cluster(s) detected:\n")
    flagged_users = []
    for idx, cluster in enumerate(cluster_list, 1):
        size    = cluster.get("cluster_size", cluster.get("size", "?"))
        avg_r   = cluster.get("avg_risk_score", cluster.get("risk", 0))
        members = cluster.get("members", cluster.get("users", []))
        color   = RED if avg_r > 0.6 else YELLOW

        print(f"    {c(color, f'Cluster #{idx}')}  "
              f"size={bold(str(size))}  "
              f"avg_risk={risk_bar(avg_r, 10)}")
        if members:
            preview = ", ".join(str(m) for m in members[:5])
            if len(members) > 5:
                preview += f" … +{len(members)-5} more"
            print(f"      {c(DIM, 'members:')} {preview}")
        flagged_users.extend(members if members else [])

    return flagged_users

# ─── Phase 4 : Auto-freeze ────────────────────────────────────────────────────
def phase_freeze(client: httpx.Client, base: str, bot_results: list, do_freeze: bool = True):
    section("PHASE 4 — Auto-Freeze & Blockchain Audit", MAGENTA)

    # Collect user IDs of suspicious bots
    suspects = [r["uid"] for r in bot_results if r.get("is_suspicious") or r.get("risk_score", 0) > 0.5]

    if not suspects:
        # If threshold not exceeded yet, pick top-risk bots
        suspects = sorted(bot_results, key=lambda r: r.get("risk_score", 0), reverse=True)
        suspects = [r["uid"] for r in suspects[:6]]

    print(c(DIM, f"  {len(suspects)} accounts meet the freeze threshold.\n"))

    frozen_count = 0
    blockchain_count = 0

    for uid in suspects:
        if do_freeze:
            print(f"  {timestamp()}  Freezing {c(YELLOW, uid)} ...", end="  ", flush=True)
            result = post(client, f"{base}/api/freeze-blockchain/{uid}", {})
            auth0_ok      = result.get("auth0", {}).get("success", False)
            blockchain_ok = result.get("blockchain", {}).get("blockchain_logged", False)
            txid          = result.get("blockchain", {}).get("txid", "")
            explorer      = result.get("blockchain", {}).get("explorer_link", "")

            status_auth0 = c(GREEN, "Auth0 ✔") if auth0_ok else c(RED, "Auth0 ✗")
            status_chain = c(GREEN, "Algorand ✔") if blockchain_ok else c(YELLOW, "Algorand (not configured)")
            print(f"{status_auth0}  {status_chain}")

            if txid:
                print(f"           {c(DIM, '└─ tx:')} {c(CYAN, txid[:20])}…  {c(DIM, explorer)}")

            if auth0_ok:   frozen_count += 1
            if blockchain_ok: blockchain_count += 1
        else:
            print(f"  {c(YELLOW, '⏭')} (--no-freeze mode) Would freeze {c(YELLOW, uid)}")
        time.sleep(0.2)

    return frozen_count, blockchain_count

# ─── Summary ──────────────────────────────────────────────────────────────────
def print_summary(legit: list, bots: list, frozen: int, blockchain: int):
    section("SUMMARY — AuthShield Detection Report", CYAN)

    legit_avg = sum(r.get("risk_score", 0) for r in legit) / len(legit) if legit else 0
    bot_avg   = sum(r.get("risk_score", 0) for r in bots)  / len(bots)  if bots  else 0
    bot_sus   = sum(1 for r in bots if r.get("is_suspicious") or r.get("risk_score", 0) > 0.5)

    rows = [
        ("Legitimate users simulated",  c(GREEN,  str(len(legit)))),
        ("Avg risk (legit)",            c(GREEN,  f"{legit_avg:.4f}")),
        ("Bot accounts simulated",      c(RED,    str(len(bots)))),
        ("Avg risk (botnet)",           c(RED,    f"{bot_avg:.4f}")),
        ("Bots flagged as suspicious",  c(RED,    str(bot_sus))),
        ("Accounts frozen (Auth0)",     c(MAGENTA,str(frozen))),
        ("Events on Algorand chain",    c(CYAN,   str(blockchain))),
    ]

    for label, value in rows:
        print(f"  {c(DIM, '·')} {label:<38} {bold(value)}")

    print()
    if frozen > 0:
        print(c(BG_GREEN, c(BOLD, f"  ✔  Attack NEUTRALISED — {frozen} bot accounts frozen  ")))
    elif bot_sus > 0:
        print(c(BG_RED, c(BOLD, "  ⚠  Bots DETECTED — Auth0 not connected (freeze skipped)  ")))
    else:
        print(c(YELLOW, "  ℹ  Detection complete. Tune RISK_SCORE_THRESHOLD if no flags raised."))
    print()

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AuthShield Botnet Attack Demo")
    parser.add_argument("--host",        default="http://localhost:8000", help="API base URL")
    parser.add_argument("--bots",        type=int, default=12,  help="Number of bot accounts (default 12)")
    parser.add_argument("--legit",       type=int, default=8,   help="Number of legit users (default 8)")
    parser.add_argument("--skip-legit",  action="store_true",   help="Skip legitimate traffic phase")
    parser.add_argument("--no-freeze",   action="store_true",   help="Detect but do not freeze accounts")
    parser.add_argument("--delay",       type=float, default=0, help="Extra seconds between phases")
    args = parser.parse_args()

    banner()
    print(f"  Target: {bold(c(CYAN, args.host))}")
    print(f"  Bots:   {bold(str(args.bots))}   |   Legit users: {bold(str(args.legit))}")

    # Health check
    print(f"\n  {c(DIM, 'Checking server...')}", end=" ", flush=True)
    with httpx.Client() as client:
        health = get(client, f"{args.host}/api/health")
        if "error" in health:
            print(c(RED, "✗"))
            print(c(RED, f"\n  Cannot reach {args.host}"))
            print(c(YELLOW, "  → Start the server with:  uvicorn main:app --reload"))
            sys.exit(1)
        print(c(GREEN, f"✔  server is {health.get('status','up')}"))

        # Run phases
        legit_results = []
        if not args.skip_legit:
            legit_results = phase_legit(client, args.host, args.legit)
            if args.delay: time.sleep(args.delay)

        bot_results = phase_botnet(client, args.host, args.bots)
        if args.delay: time.sleep(args.delay)

        phase_detect(client, args.host)
        if args.delay: time.sleep(args.delay)

        frozen_count, blockchain_count = phase_freeze(
            client, args.host, bot_results, do_freeze=not args.no_freeze
        )

        print_summary(legit_results, bot_results, frozen_count, blockchain_count)

if __name__ == "__main__":
    main()
