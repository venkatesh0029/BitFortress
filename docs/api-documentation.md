# SatoshiGuard REST API Reference

Base URL: `http://localhost:8000/api`

### Authentication (`/auth`)
- `POST /auth/login`: Authenticates with email and password, returns JWT token.
- `POST /auth/register`: Creates organization and admin account.
- `GET /auth/me`: Retrieves current session profile and role.
- `GET /auth/demo-users`: Lists quick-switch profiles for demonstration.

### Treasury Management (`/treasury`)
- `GET /treasury`: Returns all organizational multisig wallets.
- `GET /treasury/{id}`: Returns wallet configuration, descriptor, and on-chain balance.
- `POST /treasury`: Creates an M-of-N multisig treasury wallet via Bitcoin Core RPC.
- `POST /treasury/{id}/fund`: Mines blocks and deposits Regtest BTC.
- `POST /treasury/{id}/sync`: Scans UTXOs and updates balance.

### Transactions (`/transactions`)
- `GET /transactions`: Lists transaction proposals with optional filters.
- `GET /transactions/{id}`: Returns proposal details, PSBT status, and approvals list.
- `POST /transactions`: Proposes a payment, validates spending policy, and builds PSBT.

### Approvals (`/approvals`)
- `GET /approvals/pending`: Returns pending proposals needing current signer's review.
- `POST /approvals/sign`: Cryptographically submits a signed PSBT or signature.
- `POST /approvals/reject`: Rejects a proposal with mandatory business justification.

### Signers (`/signers`)
- `GET /signers`: Lists all registered signers and public keys.
- `POST /signers`: Registers a signer's secp256k1 public key.
- `POST /signers/generate-keypair`: Generates demo secp256k1 keypair with derivation info.

### Policies (`/policies`)
- `GET /policies`: Gets active per-transaction and daily spending limits.
- `PUT /policies`: Updates spending limits (requires `ORG_ADMIN`).

### Audit Trail (`/audit`)
- `GET /audit`: Fetches immutable organizational audit log.

### Regtest Node (`/node`)
- `GET /node/info`: Returns Bitcoin Core Regtest blockchain status.
- `POST /node/mine`: Generates Regtest blocks on demand.
