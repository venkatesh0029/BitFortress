# BitFortress: Bitcoin-Based Multisignature Corporate Treasury Management System

**BitFortress** is an institutional-grade, Bitcoin-native corporate treasury management platform. It uses Bitcoin multisignature wallets (Native SegWit P2WSH) and Partially Signed Bitcoin Transactions (BIP-174 PSBT) to mandate multi-custodian quorum authorization before corporate funds can be disbursed.

Designed without Docker requirements, all components run natively on the development machine.

---

## 1. System Architecture

```
                                   BitFortress
                                        |
                 +----------------------+----------------------+
                 |                                             |
       Next.js 16+ Frontend                          Authorized Signers
       (App Router, TypeScript)                      (Secp256k1 Hardware Keys / Offline CLI)
                 |                                             |
                 | HTTPS / JSON REST API                       | BIP-174 PSBT Signatures
                 v                                             v
          FastAPI Backend Layer <==============================+
                 |
   +-------------+-------------+----------------+----------------+
   |                           |                |                |
Authentication            Treasury Core    Policy Engine    Audit Trail
and RBAC (JWT)            (BIP-143 Sighash (Spend Limits)   (Canonical SHA-256
                           Verification)                     & External Anchors)
   |                           |                |                |
   +-------------+-------------+----------------+----------------+
                 |
       +---------+---------+
       |                   |
PostgreSQL 18       Bitcoin Core v28 (Regtest)
Database Persistence - Native PSBT creation & combination
                     - Multisig address derivation
                     - On-chain broadcast (`sendrawtransaction`)
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | Next.js 16 (App Router) | Responsive institutional application |
| **Language** | TypeScript | Type safety and schema synchronization |
| **Styling** | Vanilla CSS & Tailwind CSS v4 | Professional dark-mode financial interface |
| **Visuals & Charts** | Recharts & Framer Motion | Treasury liquidity & signer participation charts |
| **Backend API** | Python FastAPI & Uvicorn | High-performance asynchronous REST API |
| **Database** | PostgreSQL 18 | Persistent ACID relational data |
| **ORM & Migrations** | SQLAlchemy 2.0 & Alembic | Data models and schema versioning |
| **Blockchain Node** | Bitcoin Core v28 (Regtest) | Local private Bitcoin blockchain |
| **Transaction Protocol** | BIP-174 PSBT | Partially Signed Bitcoin Transaction workflow |
| **Cryptographic Library** | Secp256k1 & ECDSA | BIP-143 double-SHA256 sighash & ECDSA DER verification |
| **Authentication** | JWT with Argon2/Bcrypt | Role-based access control (RBAC) & tenant isolation |
| **External Signer CLI** | Python Secp256k1 CLI | Standalone offline signer tool (`tools/signer_cli.py`) |
| **Test Suite** | Pytest & pytest-asyncio | Automated unit, policy, and cryptographic security tests |

---

## 3. Pre-Seeded Demonstration Personas

BitFortress comes pre-seeded with 6 corporate personas for instant demonstration and testing:

| Persona | Role | Default Password | Key Custody / Device Model |
|---|---|---|---|
| **Sarah Lin** | `ORG_ADMIN` (Chief Risk Officer) | `password123` | Policy configuration & Member governance |
| **Michael Chang** | `FINANCE_MANAGER` (VP Finance) | `password123` | Payment proposal creation & liquidity monitoring |
| **David Kim** | `SIGNER` (Treasury Custodian 1) | `password123` | Custodian Device 1 / Offline CLI (`029c611...`) |
| **Elena Rostova** | `SIGNER` (Executive Signer 2) | `password123` | Custodian Device 2 / Offline CLI (`02dcb3f...`) |
| **Marcus Vance** | `SIGNER` (Security Signer 3) | `password123` | Custodian Device 3 / Offline CLI (`03cca75...`) |
| **Rachel Adams** | `AUDITOR` (Internal Audit) | `password123` | Read-only compliance & immutable audit logs |

*Note: For production deployments (`ENVIRONMENT=production`), all default demonstration credentials and fallback JWT secrets are automatically rejected at startup, and seeded users are required to change passwords (`must_change_password`).*

---

## 4. Custody Architecture: Simulated Devices & Offline Signer CLI

### Demonstration Mode (Simulated Custodian Signing Devices)
For automated local testing and interactive web demonstrations, BitFortress provisions node-isolated custodian software wallets named `sg_custodian_{signer_id}` on Bitcoin Core. Each custodian wallet holds strictly one signer keypair, ensuring private keys never touch the coordinator or PostgreSQL database.

### Production Mode (Independent Offline Signer CLI)
For true air-gapped custody or independent machine signing, BitFortress includes a standalone signer CLI tool:
```powershell
# Inspect or generate custodian signing keys offline
python tools/signer_cli.py generate-key

# Offline signer tool usage guide
python tools/signer_cli.py info
```
This enables signers to sign PSBTs completely out-of-band on physically separate machines, importing only the signed PSBT base64 payload into the BitFortress web coordinator.

---

## 5. How to Run Locally (No Docker Required)

### Prerequisites
- Node.js LTS (v20+) & npm
- Python 3.11+
- PostgreSQL 18+
- Bitcoin Core v28+ (Binaries included in `bitcoin_bin/`)

### Running the System

#### 1. Start Bitcoin Core Regtest
```powershell
& "bitcoin_bin\bitcoin-28.0\bin\bitcoind.exe" -datadir="bitcoin_data" -conf="bitcoin_data\bitcoin.conf"
```

#### 2. Start PostgreSQL Cluster (Port 5433)
```powershell
& "C:\Program Files\PostgreSQL\18\bin\postgres.exe" -D "local_pgdata" -p 5433
```

#### 3. Start FastAPI Backend (Port 8000)
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### 4. Start Next.js Frontend (Port 3000)
```powershell
cd frontend
npm run dev -- -p 3000
```

Open your browser at [http://localhost:3000](http://localhost:3000).

---

## 6. Automated Test Suite (10/10 Passing Tests)

Run unit, integration, and full multisig lifecycle security tests:
```powershell
cd backend
.\venv\Scripts\pytest.exe -o pythonpath=. -v
```

**Verified Test Cases (10/10 Passing):**
1. `test_empty_or_unsigned_psbt_rejected`: Enforces that approvals strictly require authentic cryptographic signatures; empty or unsigned PSBTs are rejected without increasing approval count.
2. `test_full_multisig_quorum_lifecycle_and_broadcast`: Full 2-of-3 multisig lifecycle: 1 signer cannot spend, 2 independent signers reach quorum, auto-finalize PSBT, and broadcast valid transaction to Bitcoin Regtest.
3. `test_tampered_psbt_rejected`: Proves that a tampered PSBT (altered destination or amount) cannot reuse previous approvals and is rejected.
4. `test_invalid_signature_with_registered_pubkey_rejected` *(Reviewer Benchmark Negative Test)*: Injects corrupted signature bytes into a PSBT while retaining the valid registered public key. Proves that independent BIP-143 sighash cryptographic verification rejects the submission, keeping approval count at 0, proposal status PENDING, no broadcast attempted, and logging a security audit event.
5. `test_cryptographic_hash_chained_audit_integrity`: Validates SHA-256 hash chaining across canonical fields (`ip_address`, canonical UTC `created_at`), external out-of-band JSONL anchoring (`audit_anchors.jsonl`), and tamper detection proof.
6. `test_password_hashing`: Verifies robust password hashing using modern cryptographic standards.
7. `test_jwt_token_creation_and_decoding`: Verifies cryptographic JWT session token claims and expiry.
8. `test_secp256k1_key_generation_and_signatures`: Verifies pure secp256k1 ECDSA DER signature verification.
9. `test_spending_policy_enforcement`: Verifies per-transaction caps and 24-hour velocity spending limits.
10. `test_duplicate_signature_and_rejection_logic`: Verifies duplicate signature rejection and proposal veto enforcement.

---

## 7. Security Guarantees & Hardening

1. **Independent BIP-143 Cryptographic Signature Verification**: The coordinator independently reconstructs the exact BIP-143 transaction signature hash (sighash) for SegWit inputs and verifies the ECDSA DER signature against the registered public key before recording approvals or state transitions.
2. **Zero Coordinator Private Key Knowledge**: Private keys are never stored in PostgreSQL or sent across coordinator network boundaries.
3. **Out-of-Band External Audit Anchoring**: Every audit record links sequentially via SHA-256 (`prev_hash` $\to$ `curr_hash`), and the tip hash is periodically anchored to an external append-only log (`audit_anchors.jsonl`), preventing rogue database administrators from rewriting history undetected.
4. **Production Configuration Guardrails**: Rejects fallback development credentials in production (`ENVIRONMENT=production`) and mandates password changes on seeded accounts.
5. **Multi-Tenant Organization Authorization**: Explicit `X-Organization-Id` header context with role-based access control (RBAC) enforced across all transaction, wallet, signer, and audit endpoints.
6. **Exact Integer & Decimal Math**: Uses exact integer satoshis throughout the application and exact decimal string formatting (`sats_to_btc_str`) for Bitcoin RPC calls, paired with Bitcoin Core fee estimation (`estimatesmartfee`).
7. **Concurrency-Safe Approvals**: Uses row-level database locking (`SELECT ... FOR UPDATE`) to prevent race conditions during concurrent signing.
