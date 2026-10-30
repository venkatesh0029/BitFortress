# BitFortress Architecture & Technical Specification

## 1. System Overview
**BitFortress** is an institutional-grade, Bitcoin-native multisignature treasury management platform. It eliminates single-point-of-failure key risk by enforcing strict threshold policies (e.g., 2-of-3, 3-of-5) before any Bitcoin transaction can be finalized and broadcast.

```
                           BitFortress Architecture
                                     |
               +---------------------+---------------------+
               |                                           |
     Next.js 16+ Frontend                       Isolated Signer Devices
     (App Router, TypeScript)                   (Hardware Custodian Keys)
               |                                           |
               | HTTPS / JSON REST API                     | PSBT Signatures Only
               v                                           v
       FastAPI Backend Layer <=============================+
               |
  +------------+------------+---------------+----------------+
  |                         |               |                |
Auth & Multi-Org RBAC  Treasury Core   Policy Engine    Audit Trail
(JWT, Argon2/Bcrypt)   (PSBT Pipeline) (Spend Velocity) (SHA-256 Chained)
  |                         |               |                |
  +------------+------------+---------------+----------------+
               |
  +------------+--------------------+
  |                                 |
PostgreSQL 18              Bitcoin Core v28 (Regtest)
- Multi-Org Isolation      - PSBT Creation (`createpsbt`)
- Signer Public Profiles   - UTXO Descriptor Analysis (`utxoupdatepsbt`)
- Treasury Wallets         - Combination (`combinepsbt`)
- Row-Locked Proposals     - Finalization (`finalizepsbt`)
- SHA-256 Hash Chaining    - Node RPC Broadcast (`sendrawtransaction`)
```

## 2. Cryptographic Custody & BIP-174 Signing Flow
BitFortress implements an air-gapped / isolated custodian architecture:
1. **Zero Server Private Key Knowledge**: The coordinator backend and PostgreSQL database store strictly secp256k1 public keys and wallet descriptors. Private keys never cross coordinator boundaries.
2. **Device Signer Isolation**: Signers operate independent signing devices (represented by isolated custodian wallets `sg_custodian_{signer_id}`). Each custodian signs the original unsigned PSBT independently.
3. **Mandatory Signature Extraction**: An approval is rejected unless the submitted PSBT contains a valid ECDSA partial signature cryptographically verified against the signer's registered public key.
4. **Deterministic PSBT Combination**: The coordinator merges verified PSBTs using Bitcoin Core `combinepsbt`, auto-finalizes via `finalizepsbt` once threshold $M$ is attained, and broadcasts to the network.

## 3. PSBT Transaction Lifecycle & Concurrency Controls
1. **Proposal Creation**: Authorized finance manager submits destination address, satoshi amount, and business justification.
2. **Strict Satoshi Math & Dust Protection**: All amounts and fee estimations are computed in integer satoshis. Destinations are validated via Bitcoin Core `validateaddress`, and outputs below the 546-satoshi dust threshold are rejected.
3. **Descriptor-Enriched PSBT**: The coordinator creates an unsigned PSBT spending selected multisig UTXOs and enriches input metadata via `utxoupdatepsbt`.
4. **Row-Level Concurrency Locking**: Proposals are locked using PostgreSQL `SELECT ... FOR UPDATE` during approval processing to eliminate race conditions between simultaneous signers.
5. **Independent Signing**: Signers review transaction inputs, outputs, destination, and fee, then generate ECDSA DER signatures.
6. **Signature Verification & Merging**: Backend verifies each partial signature and combines them via `combinepsbt`.
7. **Threshold Enforcement**: When verified signature count $\ge M$, the transaction is finalized (`finalizepsbt`) and broadcast to the Bitcoin network (`sendrawtransaction`).
8. **Confirmation**: Regtest block is generated to confirm the transfer on-chain.

## 4. Immutable Cryptographic Audit Chain
All lifecycle events (proposals, policy rejections, signature submissions, quorums, broadcasts) are recorded into an append-only audit trail protected by SHA-256 hash chaining:
$$\text{Current Hash} = \text{SHA-256}(\text{Previous Hash} \parallel \text{Org ID} \parallel \text{Action} \parallel \text{Actor ID} \parallel \text{Timestamp} \parallel \text{Payload JSON})$$
The chain can be verified at any time via `GET /api/audit/verify` or through the Security Center UI. Tampering with any historical record immediately invalidates the cryptographic chain.

