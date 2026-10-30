# BitFortress Security Controls & Threat Model

## 1. Key Custody & Signer Device Isolation
- **Zero Plaintext Private Keys in Application Database**: PostgreSQL stores strictly public keys (`secp256k1` compressed 33-byte hex) and BIP-174 witness script descriptors. Private keys never cross coordinator boundaries.
- **Simulated Custodian Devices (Regtest Mode)**: For development and automated testing, signers operate node-isolated custodian software wallets named `sg_custodian_{signer_id}` hosted on Bitcoin Core. Each wallet contains exclusively one signer keypair.
- **Standalone Offline Signer CLI (Production Mode)**: For production or air-gapped custody, BitFortress provides `tools/signer_cli.py`, allowing signers to inspect, generate, and sign PSBTs on independent physical workstations without network exposure.
- **Strict Separation of Duties**: Proposers (`FINANCE_MANAGER`) cannot approve transactions unless they hold an assigned `SIGNER` role with an authorized public key on the treasury wallet.

## 2. Independent BIP-143 Cryptographic Signature Verification
- **Pre-Approval Cryptographic Verification**: In `psbt_service.py`, `verify_signer_signature_cryptographic` does NOT merely check if the public key exists in `partial_signatures`. It independently calculates the exact 32-byte BIP-143 double-SHA256 signature hash (sighash) for SegWit inputs:
  $$\text{sighash} = \text{SHA-256}(\text{SHA-256}(\text{nVersion} \parallel \text{hashPrevouts} \parallel \text{hashSequence} \parallel \text{outpoint} \parallel \text{scriptCode} \parallel \text{amount} \parallel \text{nSequence} \parallel \text{hashOutputs} \parallel \text{nLockTime} \parallel \text{sighashType}))$$
- **ECDSA DER Verification**: The extracted DER signature bytes are verified against the registered public key and the computed sighash using `secp256k1` before any approval record is inserted into the database.
- **Negative Test Coverage**: Verified by automated test `test_invalid_signature_with_registered_pubkey_rejected`, which ensures corrupted signature bytes with a registered public key are rejected, approval count remains 0, status remains PENDING, no broadcast occurs, and a security audit event is logged.

## 3. Transaction Construction, Exact Math & Fee Handling
- **Integer Satoshi Accounting**: Internal balances, proposal amounts, fees, and change amounts are strictly represented in integer satoshis.
- **Exact Decimal String Serialization**: When communicating with Bitcoin Core RPC, amounts are converted via `sats_to_btc_str(satoshis)` into exact fixed-precision decimal strings (e.g. `"0.10000000"`), eliminating floating-point binary conversion inaccuracies.
- **Dynamic Fee Estimation**: BitFortress uses Bitcoin Core's `estimatesmartfee` to compute optimal sat/vB network feerates.
- **Dust Protection**: Automatically rejects outputs below the 546-satoshi Bitcoin dust threshold.
- **Address Validation**: All destination addresses are validated using Bitcoin Core `validateaddress` before PSBT construction.

## 4. Multi-Tenant Organization Authorization
- **Explicit Organization Context**: Request headers explicitly specify `X-Organization-Id`, validated against the authenticated user's active memberships (`get_current_org_membership`).
- **Endpoint Protection**: Privileged endpoints (such as `POST /signers/generate-keypair`) require `ORG_ADMIN` role and are disabled in production. All signer device operations verify that the authenticated caller owns the signer profile within that tenant.

## 5. Tamper-Evident Audit Trail & Out-of-Band Anchoring
- **Canonical SHA-256 Hash Chaining**: Every audit record links sequentially to the previous event hash. Canonical serialization includes:
  - `prev_hash`
  - `organization_id`
  - `actor_id`
  - `event_type`
  - `reference_type` & `reference_id`
  - `ip_address`
  - `created_at` (canonical UTC ISO-8601 formatting)
  - Canonical sorted JSON details
- **External Out-of-Band Anchoring**: Audit chain tips are periodically anchored to an append-only external log file (`audit_anchors.jsonl`) outside the database. During `verify_audit_chain`, historical events are verified against both internal chaining and external anchor records, immediately detecting rogue database administrators who rewrite historical tables.

## 6. Concurrency Controls & Idempotency
- **Row-Level Database Locking**: Uses `SELECT ... FOR UPDATE` on transaction proposals during the approval workflow to serialize concurrent signature submissions and eliminate race conditions.
- **Controlled Broadcast State Machine**: Transactions transition atomically from `PENDING` $\to$ `SIGNED` $\to$ `BROADCAST`, preventing duplicate on-chain broadcasts.
