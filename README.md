<div align="center">

# 🛡️ AuthShield AI

**AI-Powered Botnet & Credential-Stuffing Detection with Blockchain Audit Trails**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Algorand](https://img.shields.io/badge/Algorand-Testnet-black?logo=algorand)](https://algorand.com/)
[![Auth0](https://img.shields.io/badge/Auth0-Integration-eb5424?logo=auth0)](https://auth0.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20Local-47A248?logo=mongodb)](https://www.mongodb.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph%20DB-008CC1?logo=neo4j)](https://neo4j.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [How the Bot Attack Works](#-how-the-bot-attack-works)
- [Why Algorand?](#-why-algorand)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the App](#-running-the-app)
- [Botnet Demo Script](#-botnet-demo-script)
- [API Reference](#-api-reference)
- [Blockchain Endpoints](#blockchain-endpoints)
- [Dashboard](#-dashboard)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Security Notes](#-security-notes)

---

## 🔍 Overview

**AuthShield AI** is a real-time threat-detection backend that protects Auth0-managed applications from:

- 🤖 **Credential stuffing / botnet attacks** — coordinated login attempts from clusters of fake or compromised accounts.
- 🕵️ **Anomalous login behaviour** — unusual device fingerprints, IP ranges, or typing patterns.
- 🔗 **Account takeover (ATO)** — flagged users are automatically frozen in Auth0 before damage occurs.

Every freeze and unfreeze action is written to the **Algorand blockchain** as an immutable, time-stamped audit record — verifiable by any third party without trusting a central database.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   CLIENT BROWSER                    │
                    │          static/index.html  ·  app.js  ·  style.css │
                    └──────────────────────┬──────────────────────────────┘
                                           │  HTTP / REST
                    ┌──────────────────────▼──────────────────────────────┐
                    │                FastAPI Backend (main.py)             │
                    │  /api/simulate  /api/freeze  /webhook/auth0  …      │
                    └──┬──────────┬───────────┬───────────────┬───────────┘
                       │          │           │               │
           ┌───────────▼─┐  ┌────▼────┐  ┌──▼──────┐  ┌────▼──────────────────┐
           │  fingerprint│  │  risk.py│  │ graph.py│  │  blockchain/           │
           │  .py        │  │(IsoForest│  │(Neo4j)  │  │  algorand_client.py   │
           │  Feature    │  │ Anomaly)│  │ Cluster │  │  freeze_ledger.py      │
           │  Extraction │  └────┬────┘  │ Graph   │  │  nft_badge.py          │
           └─────────────┘       │       └──┬──────┘  │  reputation.py         │
                                 │          │         └────────────┬───────────┘
                       ┌─────────▼──────────▼─┐                   │
                       │     MongoDB (db.py)   │        ┌──────────▼──────────┐
                       │  login_events         │        │  Algorand Testnet   │
                       │  freeze_log           │        │  (Algonode / Custom)│
                       │  frozen_users         │        └─────────────────────┘
                       │  thresholds           │
                       └──────────────────────┘
                                 │
                       ┌─────────▼──────────┐
                       │   Auth0 Management  │
                       │   API (auth0_client)│
                       │  Block / Unblock    │
                       └────────────────────┘
```

### Data Flow

1. A login event arrives at `/api/simulate` (or `/webhook/auth0` from Auth0 Actions).
2. `fingerprint.py` extracts a **16-dimensional feature vector** from IP, User-Agent, screen resolution, timezone, and typing cadence.
3. `risk.py` scores the event via an **Isolation Forest** anomaly model + cosine-similarity against the user's cluster centroid.
4. `graph.py` (Neo4j) adds/updates the user node and detects **botnet clusters** using community detection.
5. If the risk score exceeds the threshold, the user is **frozen via Auth0 Management API**.
6. The freeze action is **recorded on Algorand** — immutably and verifiably.
7. In background tasks: reputation scores are updated and NFT badges are minted for low-risk verified users.

---

## 🤖 How the Bot Attack Works

AuthShield includes a full **4-phase botnet simulation** to demonstrate detection capabilities. Bots betray themselves through **uniformity** — the same subnet, the same fingerprint, and robotic typing patterns.

### The Telltale Signals

| Signal | Legitimate User | Bot Account |
|---|---|---|
| IP address | Random & diverse (e.g. `143.22.87.4`) | All from `45.152.66.X` (same `/24` subnet) |
| User-Agent | 7 different browsers/OSes | Always `Chrome/88` (old, identical) |
| WebGL hash | `wgl_12345` (unique per device) | `wgl_BOTNET_UNIFORM` (hardcoded) |
| Canvas hash | `cvs_12345` (unique per device) | `cvs_BOTNET_UNIFORM` (hardcoded) |
| Typing latency | `~175ms ± 40ms` (human variance) | `~50ms ± 3ms` (robotic, too fast & too uniform) |
| Timezone | Varied (`UTC+5`, `UTC-8`, …) | Always `UTC+0` |
| Screen resolution | Varied (`1920x1080`, `2560x1440`, …) | Always `1024x768` |

### Detection Layers

1. **Isolation Forest** — individual anomaly detection on the 16-dim feature vector.
2. **Neo4j Cluster Graph** — nodes sharing the same subnet or behavior hash get linked; communities exceeding the cluster-size threshold are auto-flagged.
3. **Auth0 Freeze** — flagged accounts are blocked in real time via the Management API.
4. **Algorand Audit Trail** — every freeze is written immutably on-chain with a transaction ID.

---

## ⛓️ Why Algorand?

Traditional security audit logs live in the same database as the system they protect. If that database is compromised, the audit trail is worthless.

AuthShield uses **Algorand** to solve this:

| Property | Benefit in AuthShield |
|---|---|
| **Immutability** | Once a freeze event is written on-chain, it cannot be altered or deleted. |
| **Transparency** | Any freeze/unfreeze can be verified by a third party on [AlgoExplorer](https://testnet.algoexplorer.io/) using the transaction ID. |
| **Speed** | Algorand finalises transactions in ~3.9 seconds — fast enough for real-time security events. |
| **Near-zero fees** | Payment transactions carry `amt=0 ALGO` with metadata in the `note` field — costs are negligible (<0.001 ALGO per event). |
| **NFT Badges (ARC-69)** | Low-risk verified users (risk < 0.3) receive an on-chain **Verified User Badge** (ASA) as proof of trustworthiness. |
| **Reputation Tokens** | Trust score = `100 − (risk_score × 50)`, stored as on-chain notes, decentralised from the app database. |

### What Algorand Records

| Event | Algorand Note Payload |
|---|---|
| User Freeze | `{ type: "FREEZE", user_id, risk_score, cluster_id, reason, timestamp }` |
| User Unfreeze | `{ type: "UNFREEZE", user_id, admin_id, reason, timestamp }` |
| Cluster Detection | `{ type: "CLUSTER_DETECTION", cluster_size, flagged_count, avg_risk_score }` |
| Reputation Update | `{ type: "REPUTATION_UPDATE", user_id, risk_score, trust_score, timestamp }` |
| NFT Badge Mint | ARC-69 ASA creation for verified users with `risk_score < 0.3` |

All records include `"system": "AuthShield AI"` for easy indexer queries.

---

## ✨ Features

- **Device Fingerprinting** — 16-dim feature vectors from IP, UA, canvas hash, WebGL hash, screen resolution, timezone, and typing latency.
- **ML Anomaly Detection** — Isolation Forest trained on historical login vectors; auto-seeded on first run.
- **Graph-based Cluster Detection** — Neo4j + Cypher; flags coordinated botnet clusters exceeding configurable thresholds.
- **Automatic User Freeze** — Auth0 Management API blocks suspicious users in real-time.
- **Blockchain Audit Trail** — Every freeze/unfreeze is written to Algorand Testnet as an immutable 0-ALGO note transaction.
- **NFT Badges** — ARC-69 compliant Algorand Standard Assets minted for verified low-risk users.
- **Reputation System** — Decentralised trust scoring stored as on-chain notes.
- **Real-Time Dashboard** — Vanilla HTML/CSS/JS dashboard to monitor events, clusters, freeze logs, and blockchain status.
- **Auth0 Webhook** — Direct integration endpoint for Auth0 Actions / Log Streams.
- **Multi-user Auth** — JWT-based login with role support (`admin`, `analyst`, `viewer`).
- **4-Phase Demo Script** — `demo_attack.py` simulates a full botnet attack end-to-end in your terminal.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI + Uvicorn |
| **Identity** | Auth0 (Management API v2) + JWT |
| **Database** | MongoDB (login events, freeze log, frozen users) |
| **Graph DB** | Neo4j (user cluster analysis) |
| **ML** | scikit-learn Isolation Forest |
| **Blockchain** | Algorand (py-algorand-sdk) |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript |
| **Config** | python-dotenv |
| **Password hashing** | bcrypt + passlib |

---

## 📦 Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | ≥ 3.10 | Runtime |
| MongoDB | ≥ 6.0 | Login event storage |
| Neo4j | ≥ 5.x | Graph-based cluster detection |
| Auth0 Account | — | User IAM & block/unblock API |
| Algorand wallet | — | Blockchain audit trail (testnet) |

> **Free tiers work fine** — MongoDB Atlas free, Neo4j Aura free, Algorand Testnet (no real funds required).

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/aritra0342/AuthSheild.git
cd AuthSheild

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt
```

### Python Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response validation |
| `pymongo` | MongoDB driver |
| `neo4j` | Neo4j graph database driver |
| `numpy` | Numerical feature processing |
| `scikit-learn` | Isolation Forest anomaly detection |
| `httpx` | Async HTTP client (Auth0 + demo script) |
| `python-dotenv` | `.env` file loading |
| `py-algorand-sdk` | Algorand blockchain integration |
| `PyJWT` | JWT token creation & verification |
| `passlib[bcrypt]` | Password hashing |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```dotenv
# ── Auth0 ─────────────────────────────────────────────────────────────────────
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_mgmt_client_id        # Machine-to-Machine app
AUTH0_CLIENT_SECRET=your_mgmt_client_secret
AUTH0_AUDIENCE=https://your-tenant.auth0.com/api/v2/

# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=authshield

# ── Neo4j ──────────────────────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ── Algorand ───────────────────────────────────────────────────────────────────
ALGORAND_NETWORK=testnet
ALGORAND_MNEMONIC=word1 word2 ... word25   # 25-word mnemonic
ALGORAND_NODE=https://testnet-api.algonode.cloud
ALGORAND_INDEXER=https://testnet-idx.algonode.cloud

# ── Risk Thresholds ────────────────────────────────────────────────────────────
CLUSTER_SIZE_THRESHOLD=5
SIMILARITY_THRESHOLD=0.85
RISK_SCORE_THRESHOLD=0.7
AUTOENCODER_THRESHOLD=0.1

# ── JWT ────────────────────────────────────────────────────────────────────────
JWT_SECRET=your_random_secret_32chars
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### Generating an Algorand Testnet Wallet

You do **not** need real ALGO. Start the server and call:

```bash
POST http://localhost:8000/api/blockchain/generate-wallet
```

This returns an `address` and `mnemonic`. Paste the mnemonic into `ALGORAND_MNEMONIC`, then fund the address with free testnet ALGO using the `fund_url` from the response.

---

## ▶️ Running the App

```bash
# Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** to see the live dashboard.  
Interactive API docs: **http://localhost:8000/docs**

---

## 🎯 Botnet Demo Script

`demo_attack.py` runs a complete end-to-end botnet simulation against the running server:

```
PHASE 0 → Train Isolation Forest on 400 synthetic legit fingerprints
PHASE 1 → Simulate N legitimate users (diverse IPs, browsers, typing)
PHASE 2 → Launch botnet (same subnet · identical UA · robotic typing)
PHASE 3 → Graph cluster detection via Neo4j
PHASE 4 → Freeze top-risk bots + write Algorand audit trail
```

### Usage

```bash
# Default: 8 legit users + 12 bots
python demo_attack.py

# Custom counts
python demo_attack.py --bots 20 --legit 15

# Skip legit phase, go straight to attack
python demo_attack.py --skip-legit

# Detect clusters but do NOT freeze (dry run)
python demo_attack.py --no-freeze

# Target a remote server
python demo_attack.py --host http://your-server:8000
```

### Sample Output

```
  ╔══════════════════════════════════════════════════════════╗
  ║   🛡️  AuthShield AI — Botnet Attack Simulation           ║
  ╚══════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────┐
  │        PHASE 1 — Legitimate Users Logging In             │
  └──────────────────────────────────────────────────────────┘
  04:59:55.221  legit_user_001   IP:143.22.87.4    Risk:█░░░░░░░░░░░░░░░░░ 0.104  ✔ OK
  04:59:55.221  legit_user_002   IP:92.168.12.44   Risk:█░░░░░░░░░░░░░░░░░ 0.098  ✔ OK

  ┌──────────────────────────────────────────────────────────┐
  │        PHASE 2 — 🤖  Botnet Attack Launched              │
  └──────────────────────────────────────────────────────────┘
  05:01:06.278  bot_account_001  IP:45.152.66.1    Risk:██████████████░░░░ 0.847  ⚠ SUSPICIOUS  🔒 FROZEN
  05:01:06.399  bot_account_002  IP:45.152.66.2    Risk:█████████████░░░░░ 0.831  ⚠ SUSPICIOUS  🔒 FROZEN
  ...
  ⚠ Average risk score (botnet): 0.8340
  ⚠ Flagged as suspicious individually: 12/12

  ┌──────────────────────────────────────────────────────────┐
  │        PHASE 3 — Graph Cluster Detection (Neo4j)         │
  └──────────────────────────────────────────────────────────┘
  ◉ Cluster scan complete:
     Flagged accounts  : 12
     Auto-frozen (Auth0): 12

  ┌──────────────────────────────────────────────────────────┐
  │        PHASE 4 — Manual Freeze + Algorand Audit Trail    │
  └──────────────────────────────────────────────────────────┘
  bot_account_001  Auth0 ✔  Algorand ✔
    └─ txid: ABCDE12345...
    └─ link: https://testnet.algoexplorer.io/tx/ABCDE12345...

  ┌──────────────────────────────────────────────────────────┐
  │        FINAL REPORT — AuthShield Detection Summary       │
  └──────────────────────────────────────────────────────────┘
  ◦ Legit users simulated     8
  ◦ Avg risk — legit          0.0952
  ◦ Bot accounts simulated    12
  ◦ Avg risk — botnet         0.8340
  ◦ Risk Δ (bot − legit)      +0.7388
  ◦ Suspicious flags          12
  ◦ Accounts frozen (Auth0)   12
  ◦ Events on Algorand chain  6

  ✔  ATTACK NEUTRALISED  —  12 bot account(s) frozen in Auth0
```

> **Note:** Risk scores will appear lower (≈ 0.11) when `RISK_SCORE_THRESHOLD` is too high or when the Isolation Forest hasn't seen enough bot traffic yet. Run the demo a second time or lower `RISK_SCORE_THRESHOLD` in `.env` to `0.1` for more dramatic separation.

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/login` | Login with username/password → JWT |
| `POST` | `/api/register` | Register a new user |
| `GET` | `/api/me` | Get current user profile |
| `GET` | `/api/users` | List all users (authenticated) |
| `POST` | `/api/simulate` | Simulate a login event (fingerprint + risk score) |
| `POST` | `/api/fingerprint` | Extract feature vector only |
| `POST` | `/api/risk-score` | Calculate risk score for a fingerprint |
| `GET` | `/api/events` | Recent login events |
| `GET` | `/api/flagged` | Currently flagged users |
| `GET` | `/api/clusters` | All detected botnet clusters |
| `GET` | `/api/cluster/{user_id}` | Cluster info for a specific user |
| `POST` | `/api/check-clusters` | Re-evaluate all clusters and auto-freeze |
| `POST` | `/api/freeze/{user_id}` | Manually freeze a user (Auth0 only) |
| `POST` | `/api/unfreeze/{user_id}` | Unfreeze a user |
| `POST` | `/api/freeze-blockchain/{user_id}` | Freeze + write Algorand audit entry |
| `POST` | `/webhook/auth0` | Auth0 Actions / Log Streams webhook |
| `GET` | `/api/thresholds` | Get detection thresholds |
| `POST` | `/api/thresholds` | Update detection thresholds |
| `GET` | `/api/auth0/users` | List all Auth0 users |
| `GET` | `/api/freeze-log` | Freeze/unfreeze history |
| `GET` | `/api/frozen-users` | Currently frozen users |

### Demo Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/demo/run-attack` | Runs Phase 1 + Phase 2 (8 legit + 12 bots) server-side |
| `POST` | `/api/demo/freeze-all` | Detects clusters and freezes all flagged bots with blockchain log |

### Blockchain Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/blockchain/status` | Algorand connection status & address |
| `GET` | `/api/blockchain/balance` | Signing account ALGO balance |
| `POST` | `/api/blockchain/generate-wallet` | Generate a new testnet keypair |
| `POST` | `/api/blockchain/log-freeze/{user_id}` | Write a freeze record on-chain |
| `POST` | `/api/blockchain/mint-badge/{user_id}` | Mint ARC-69 NFT badge for a verified user |
| `POST` | `/api/blockchain/update-reputation/{user_id}` | Write a reputation update on-chain |

---

## 🖥️ Dashboard

The built-in dashboard (`static/index.html`) provides:

- **Live event feed** — rolling table of login events with colour-coded risk scores.
- **Flagged & frozen users panel** — one-click freeze/unfreeze with blockchain logging toggle.
- **Cluster graph** — visualises detected botnet clusters from Neo4j.
- **Blockchain panel** — Algorand connection status, ALGO balance, and explorer links for every audit record.
- **Threshold controls** — adjust cluster-size, similarity, and risk-score thresholds without restarting.
- **Demo attack button** — trigger the full attack simulation from the UI.

---

## 📂 Project Structure

```
AuthSheild/
├── main.py                # FastAPI app — all routes & startup
├── config.py              # Environment config loader
├── fingerprint.py         # Feature extraction (16-dim vector)
├── risk.py                # Isolation Forest anomaly + risk scoring
├── graph.py               # Neo4j cluster detection (Cypher)
├── db.py                  # MongoDB helpers (events, freeze log, users)
├── auth0_client.py        # Auth0 Management API (freeze / unfreeze)
│
├── blockchain/
│   ├── __init__.py        # Package exports
│   ├── algorand_client.py # Core Algorand SDK wrapper (AlgodClient)
│   ├── freeze_ledger.py   # On-chain freeze / unfreeze / cluster logs
│   ├── nft_badge.py       # ARC-69 NFT badge minting for verified users
│   └── reputation.py      # Decentralised trust score (100 − risk×50)
│
├── static/
│   ├── index.html         # Dashboard HTML
│   ├── app.js             # Dashboard JavaScript
│   └── style.css          # Dashboard styles
│
├── demo_attack.py         # 4-phase botnet attack simulation CLI
├── test_botnet.py         # Comprehensive botnet scenario unit tests
├── test_api.py            # Basic API smoke tests
├── test_debug.py          # Debug helpers
│
├── demo.bat               # Windows one-click demo launcher
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── vercel.json            # Vercel deployment config
└── .gitignore
```

---

## 🧪 Testing

```bash
# Run the 4-phase demo attack against a local running server
python demo_attack.py

# Basic API smoke test
python test_api.py

# Comprehensive botnet scenario tests
python test_botnet.py

# Or with pytest
pip install pytest
pytest test_api.py test_botnet.py -v
```

---

## 🔒 Security Notes

- **Never commit `.env`** — it contains API secrets and your Algorand mnemonic.
- The Algorand mnemonic controls the signing account. Keep it safe — anyone with the mnemonic can spend the wallet's ALGO.
- For production, rotate credentials regularly and use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.).
- The dashboard has no authentication by default — protect it behind a reverse proxy (Nginx, Caddy) with basic auth in production.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
Built with ❤️ using FastAPI · Algorand · Auth0 · Neo4j · MongoDB · scikit-learn
</div>
