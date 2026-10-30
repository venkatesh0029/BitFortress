# SatoshiGuard: Bitcoin-Based Multisignature Corporate Treasury Management System

**SatoshiGuard** is an institutional-grade, Bitcoin-native corporate treasury management platform. It uses Bitcoin multisignature wallets (Native SegWit P2WSH) and Partially Signed Bitcoin Transactions (BIP-174 PSBT) to mandate multi-custodian quorum authorization before corporate funds can be disbursed.

Designed without Docker requirements, all components run natively on the development machine.

---

## 1. System Architecture

```
                                  SatoshiGuard
                                        |
                 +----------------------+----------------------+
                 |                                             |
       Next.js 16+ Frontend                          Authorized Signers
       (App Router, TypeScript)                      (Secp256k1 Hardware Keys)
                 |                                             |
                 | HTTPS / JSON REST API                       | PSBT Signatures
                 v                                             v
          FastAPI Backend Layer <==============================+
                 |
   +-------------+-------------+----------------+----------------+
   |                           |                |                |
Authentication            Treasury Core    Policy Engine    Audit Trail
and RBAC (JWT)            (PSBT Engine)    (Spend Limits)   (Append-Only Log)
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
| **Styling** | Tailwind CSS v4 | Professional dark-mode financial interface |
| **Visuals & Charts** | Recharts & Framer Motion | Treasury liquidity & signer participation charts |
| **Backend API** | Python FastAPI & Uvicorn | High-performance asynchronous REST API |
| **Database** | PostgreSQL 18 | Persistent ACID relational data |
| **ORM & Migrations** | SQLAlchemy 2.0 & Alembic | Data models and schema versioning |
| **Blockchain Node** | Bitcoin Core v28 (Regtest) | Local private Bitcoin blockchain |
| **Transaction Protocol** | BIP-174 PSBT | Partially Signed Bitcoin Transaction workflow |
| **Cryptographic Library** | Secp256k1 & ECDSA | Public key registration and signature verification |
| **Authentication** | JWT with Argon2/Bcrypt | Role-based access control (RBAC) |
| **Test Suite** | Pytest & pytest-asyncio | Automated unit, policy, and security tests |

---

## 3. Pre-Seeded Demonstration Personas

SatoshiGuard comes pre-seeded with 6 corporate personas for instant 1-click testing:

| Persona | Role | Default Password | Key Custody |
|---|---|---|---|
| **Sarah Lin** | `ORG_ADMIN` (Chief Risk Officer) | `password123` | Policy configuration & Member governance |
| **Michael Chang** | `FINANCE_MANAGER` (VP Finance) | `password123` | Payment proposal creation & liquidity monitoring |
| **David Kim** | `SIGNER` (Treasury Custodian 1) | `password123` | Hardware Key HSM-01 (`029c611...`) |
| **Elena Rostova** | `SIGNER` (Executive Signer 2) | `password123` | Hardware Key HSM-02 (`02dcb3f...`) |
| **Marcus Vance** | `SIGNER` (Security Signer 3) | `password123` | Hardware Key HSM-03 (`03cca75...`) |
| **Rachel Adams** | `AUDITOR` (Internal Audit) | `password123` | Read-only compliance & immutable audit logs |

---

## 4. How to Run Locally (No Docker Required)

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

## 5. Automated Test Suite

Run unit, integration, and full multisig lifecycle security tests:
```powershell
cd backend
.\venv\Scripts\pytest.exe -o pythonpath=. -v
```

**Verified Test Cases (9/9 Passing):**
1. `test_empty_or_unsigned_psbt_rejected`: Enforces that approvals require authentic cryptographic signatures; empty approvals are strictly rejected.
2. `test_full_multisig_quorum_lifecycle_and_broadcast`: Demonstrates full 2-of-3 multisig lifecycle: 1 signer cannot spend, 2 independent custodian signers reach threshold, auto-finalize PSBT, and broadcast valid transaction to Bitcoin Regtest.
3. `test_tampered_psbt_rejected`: Proves that a tampered PSBT (altered output/amount) is immediately rejected and cannot reuse previous approvals.
4. `test_cryptographic_hash_chained_audit_integrity`: Validates SHA-256 hash chaining across audit log events, proving that tampering with any historical event is detected.
5. `test_password_hashing`: Verifies robust password hashing using modern cryptographic standards.
6. `test_jwt_token_creation_and_decoding`: Verifies cryptographic JWT session token claims and expiry.
7. `test_secp256k1_key_generation_and_signatures`: Verifies pure secp256k1 ECDSA DER signature verification.
8. `test_spending_policy_enforcement`: Verifies per-transaction caps and 24-hour velocity spending limits.
9. `test_duplicate_signature_and_rejection_logic`: Verifies duplicate signature rejection and veto enforcement.

---

## 6. Security Guarantees & Threat Model

1. **Zero Coordinator Key Knowledge**: Private keys are never stored in PostgreSQL or sent across coordinator network boundaries. Signers sign using isolated custodian signing devices.
2. **Mandatory Cryptographic Validation**: Approvals strictly require an authentic ECDSA DER signature extracted from the signed PSBT matching the registered signer's secp256k1 public key.
3. **Integer Satoshi Math & Dust Protection**: Eliminates float rounding bugs and rejects outputs below the 546-satoshi dust limit.
4. **Multi-Tenant Organization Isolation**: Enforces tenant-level scoping across all transaction queries, approvals, and wallet operations.
5. **Concurrency-Safe Approvals**: Uses row-level database locking (`SELECT ... FOR UPDATE`) to prevent race conditions during concurrent signing.
6. **Immutable Cryptographic Audit Trail**: Every corporate action is hash-chained via SHA-256 (`prev_hash` $\to$ `curr_hash`), making database tampering mathematically detectable.

