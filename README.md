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
- [Why Algorand?](#-why-algorand)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the App](#-running-the-app)
- [API Reference](#-api-reference)
- [Blockchain Endpoints](#-blockchain-endpoints)
- [Dashboard](#-dashboard)
- [Project Structure](#-project-structure)

---

## 🔍 Overview

**AuthShield AI** is a real-time threat-detection backend that protects Auth0-managed applications from:

- 🤖 **Credential stuffing / botnet attacks** — coordinated login attempts from clusters of fake or compromised accounts.
- 🕵️ **Anomalous login behaviour** — unusual device fingerprints, IP ranges, or typing patterns.
- 🔗 **Account takeover (ATO)** — flagged users are automatically frozen in Auth0 before damage occurs.

Every freeze and unfreeze action is written to the **Algorand blockchain** as an immutable, time-stamped audit record. This means your security posture can be independently verified without trusting a central database.

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
                       │  thresholds           │        └─────────────────────┘
                       └──────────────────────┘
                                 │
                       ┌─────────▼──────────┐
                       │   Auth0 Management  │
                       │   API (auth0_client)│
                       │  Block / Unblock   │
                       └────────────────────┘
```

### Data Flow

1. A login event arrives at `/api/simulate` (or `/webhook/auth0` from Auth0 Actions).
2. `fingerprint.py` extracts a 16-dimensional **feature vector** from the IP, User-Agent, screen resolution, timezone, and typing cadence.
3. `risk.py` scores the event via an **Isolation Forest** anomaly model + cosine-similarity against the user's cluster centroid.
4. `graph.py` (Neo4j) adds/updates the user node and detects **botnet clusters** using Louvain community detection.
5. If the risk score exceeds the threshold, the user is **frozen via Auth0 Management API**.
6. The freeze action is **recorded on Algorand** — immutably and verifiably.

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
| **NFT Badges (ARC-69)** | Low-risk verified users can receive an on-chain **Verified User Badge** (ASA) as proof of trustworthiness. |
| **Reputation Tokens** | A `REP` token tracks long-term user trust scores decentralised from the application database. |

### What Algorand Records

| Event | Algorand Note Payload |
|---|---|
| User Freeze | `{ type: "FREEZE", user_id, risk_score, cluster_id, reason, timestamp }` |
| User Unfreeze | `{ type: "UNFREEZE", user_id, admin_id, reason, timestamp }` |
| Cluster Detection | `{ type: "CLUSTER_DETECTION", cluster_size, flagged_count, avg_risk_score }` |
| Reputation Update | `{ type: "REPUTATION_UPDATE", user_id, risk_score, trust_score, timestamp }` |

All records include the field `"system": "AuthShield AI"` for easy indexer queries.

---

## ✨ Features

- **Device Fingerprinting** — 16-dim feature vectors from IP, UA, canvas hash, WebGL hash, screen resolution, timezone, and typing latency.
- **ML Anomaly Detection** — Isolation Forest trained on historical login vectors.
- **Graph-based Cluster Detection** — Neo4j + Cypher; flags coordinated botnet clusters exceeding configurable thresholds.
- **Automatic User Freeze** — Auth0 Management API blocks suspicious users in real-time.
- **Blockchain Audit Trail** — Every freeze/unfreeze is written to Algorand Testnet as an immutable 0-ALGO note transaction.
- **NFT Badges** — ARC-69 compliant Algorand Standard Assets minted for verified low-risk users.
- **Reputation System** — Decentralised trust scoring stored as on-chain notes.
- **Real-Time Dashboard** — Vanilla HTML/CSS/JS dashboard to monitor events, clusters, freeze logs, and blockchain status.
- **Auth0 Webhook** — Direct integration endpoint for Auth0 Actions / Log Streams.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI + Uvicorn |
| **Identity** | Auth0 (Management API v2) |
| **Database** | MongoDB (login events, freeze log) |
| **Graph DB** | Neo4j (user cluster analysis) |
| **ML** | scikit-learn Isolation Forest |
| **Blockchain** | Algorand (py-algorand-sdk) |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript |
| **Config** | python-dotenv |

---

## 📦 Prerequisites

Install the following before proceeding:

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

| Package | Version | Why it's needed |
|---|---|---|
| `fastapi` | ≥ 0.100 | REST API framework |
| `uvicorn` | ≥ 0.22 | ASGI server |
| `pydantic` | ≥ 2.0 | Request/response validation |
| `pymongo` | ≥ 4.4 | MongoDB driver |
| `neo4j` | ≥ 5.10 | Neo4j graph database driver |
| `numpy` | ≥ 1.24 | Numerical feature processing |
| `scikit-learn` | ≥ 1.3 | Isolation Forest anomaly detection |
| `httpx` | ≥ 0.24 | Async HTTP client (Auth0 API calls) |
| `python-dotenv` | ≥ 1.0 | `.env` file loading |
| `python-multipart` | ≥ 0.0.6 | Form data parsing |
| `py-algorand-sdk` | ≥ 2.0 | Algorand blockchain integration |
| `pyteal` | ≥ 0.20 | Algorand smart contract DSL (optional) |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```dotenv
# ── Auth0 ────────────────────────────────────────────────────────────────────
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_mgmt_client_id        # Machine-to-Machine app
AUTH0_CLIENT_SECRET=your_mgmt_client_secret
AUTH0_AUDIENCE=https://your-tenant.auth0.com/api/v2/

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=authshield

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ── Algorand ──────────────────────────────────────────────────────────────────
ALGORAND_NETWORK=testnet
ALGORAND_MNEMONIC=word1 word2 ... word25   # 25-word mnemonic
ALGORAND_NODE=https://testnet-api.algonode.cloud
ALGORAND_INDEXER=https://testnet-idx.algonode.cloud

# ── Risk Thresholds ───────────────────────────────────────────────────────────
CLUSTER_SIZE_THRESHOLD=5
SIMILARITY_THRESHOLD=0.85
RISK_SCORE_THRESHOLD=0.7
AUTOENCODER_THRESHOLD=0.1
```

### Generating an Algorand Testnet Wallet

You do **not** need real ALGO. Start the server and call:

```bash
POST http://localhost:8000/api/blockchain/generate-wallet
```

This returns an `address` and `mnemonic`. Paste the mnemonic into `ALGORAND_MNEMONIC`, then fund the address with free testnet ALGO using the link returned in `fund_url`.

---

## ▶️ Running the App

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** to see the live dashboard.

Interactive API docs are available at **http://localhost:8000/docs**.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
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

### Blockchain Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/blockchain/status` | Algorand connection status |
| `GET` | `/api/blockchain/balance` | Signing account ALGO balance |
| `POST` | `/api/blockchain/generate-wallet` | Generate a new testnet keypair |
| `POST` | `/api/blockchain/log-freeze/{user_id}` | Write a freeze record on-chain |
| `POST` | `/api/blockchain/mint-badge/{user_id}` | Mint ARC-69 NFT badge for a verified user |
| `POST` | `/api/blockchain/update-reputation/{user_id}` | Write a reputation update on-chain |

---

## 🖥️ Dashboard

The built-in dashboard (`static/index.html`) provides:

- **Live event table** — rolling feed of login events with risk scores.
- **Flagged users panel** — one-click freeze/unfreeze with optional blockchain logging.
- **Cluster graph** — visualises detected botnet clusters.
- **Blockchain panel** — shows Algorand connection status, balance, and explorer links for audit records.
- **Threshold controls** — adjust cluster-size, similarity, and risk-score thresholds without restarting.

---

## 📂 Project Structure

```
AuthSheild/
├── main.py                 # FastAPI app — all routes
├── config.py               # Environment config loader
├── fingerprint.py          # Feature extraction (16-dim vector)
├── risk.py                 # Isolation Forest anomaly + risk scoring
├── graph.py                # Neo4j cluster detection
├── db.py                   # MongoDB helpers
├── auth0_client.py         # Auth0 Management API (freeze/unfreeze)
├── blockchain/
│   ├── __init__.py         # Package exports
│   ├── algorand_client.py  # Core Algorand SDK wrapper (AlgodClient)
│   ├── freeze_ledger.py    # On-chain freeze / unfreeze / cluster logs
│   ├── nft_badge.py        # ARC-69 NFT badge minting for verified users
│   └── reputation.py       # Decentralised reputation score tracking
├── static/
│   ├── index.html          # Dashboard HTML
│   ├── app.js              # Dashboard JavaScript
│   └── style.css           # Dashboard styles
├── test_api.py             # Basic API smoke tests
├── test_debug.py           # Debug helpers
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore
```

---

## 🧪 Testing

```bash
# Basic API smoke test
python test_api.py

# Or with pytest
pip install pytest
pytest test_api.py -v
```

---

## 🔒 Security Notes

- **Never commit `.env`** — it contains API secrets and your Algorand mnemonic.
- The Algorand mnemonic controls the signing account. Keep it safe — anyone with the mnemonic can spend the wallet's ALGO.
- For production, rotate credentials regularly and use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
Built with ❤️ using FastAPI, Algorand, Auth0, Neo4j, and MongoDB
</div>
