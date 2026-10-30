# BitFortress Architecture & Technical Specification

## 1. System Overview
**BitFortress** is an institutional-grade, Bitcoin-native multisignature treasury management platform. It eliminates single-point-of-failure key risk by enforcing strict threshold policies (e.g., 2-of-3, 3-of-5) before any Bitcoin transaction can be finalized and broadcast.

```
                           BitFortress Architecture
                                     |
               +---------------------+---------------------+
               |                                           |
     Next.js 16+ Frontend                       Isolated Signer Devices
     (App Router, TypeScript)                   (Simulated Devices / Offline CLI)
               |                                           |
               | HTTPS / JSON REST API                     | BIP-174 PSBT Signatures Only
               v                                           v
       FastAPI Backend Layer <=============================+
               |
  +------------+------------+---------------+----------------+
  |                         |               |                |
Auth & Multi-Org RBAC  Treasury Core   Policy Engine    Audit Trail
(Explicit Org Header)  (BIP-143 Pre-   (Spend Velocity) (Canonical Hash Chain
                        Verification)                    & External JSONL Anchors)
  |                         |               |                |
  +------------+------------+---------------+----------------+
               |
  +------------+--------------------+
  |                                 |
PostgreSQL 18              Bitcoin Core v28 (Regtest)
- Explicit Tenant Scoping  - PSBT Creation (`createpsbt`)
- Signer Public Profiles   - UTXO Descriptor Analysis (`utxoupdatepsbt`)
- Treasury Wallets         - Combination (`combinepsbt`)
- Row-Locked Proposals     - Finalization (`finalizepsbt`)
- SHA-256 Hash Chaining    - Node RPC Broadcast (`sendrawtransaction`)
                           - Smart Fee Estimation (`estimatesmartfee`)
```

## 2. Cryptographic Custody & BIP-174 Signing Flow
BitFortress implements an air-gapped / isolated custodian architecture:
1. **Zero Server Private Key Knowledge**: The coordinator backend and PostgreSQL database store strictly secp256k1 public keys and wallet descriptors. Private keys never cross coordinator boundaries.
2. **Device Signer Isolation**:
   - **Regtest Simulation**: For local testing and live browser demonstrations, signers use node-isolated custodian software wallets (`sg_custodian_{signer_id}`).
   - **Production Isolation**: Signers execute `tools/signer_cli.py` on independent physical machines or hardware devices, providing base64 PSBT signatures out-of-band.
3. **Independent Cryptographic Signature Verification**:
   - When a signed PSBT is submitted to `POST /api/approvals`, the coordinator does not merely inspect whether the public key is present.
   - It reconstructs the BIP-143 witness script signature hash (sighash) for every input being signed.
   - It executes pure ECDSA DER verification using `secp256k1` (`ecdsa.VerifyingKey.verify_digest`).
   - If signature verification fails, the approval is rejected, approval count remains 0, the proposal remains `PENDING`, and a security audit event is logged.
4. **Deterministic PSBT Combination**: The coordinator merges verified PSBTs using Bitcoin Core `combinepsbt`, auto-finalizes via `finalizepsbt` once threshold $M$ is attained, and broadcasts to the network.

## 3. PSBT Transaction Lifecycle & Concurrency Controls
1. **Proposal Creation**: Authorized finance manager submits destination address, satoshi amount, and business justification.
2. **Strict Satoshi Math & Dust Protection**: All amounts and fee estimations are computed in integer satoshis. Destinations are validated via Bitcoin Core `validateaddress`, and outputs below the 546-satoshi dust threshold are rejected.
3. **Descriptor-Enriched PSBT**: The coordinator creates an unsigned PSBT spending selected multisig UTXOs and enriches input metadata via `utxoupdatepsbt`.
4. **Row-Level Concurrency Locking**: Proposals are locked using PostgreSQL `SELECT ... FOR UPDATE` during approval processing to eliminate race conditions between simultaneous signers.
5. **Independent Signing**: Signers review transaction inputs, outputs, destination, and fee, then generate ECDSA DER signatures.
6. **Signature Verification & Merging**: Backend independently validates ECDSA signatures against the BIP-143 sighash, then merges them via `combinepsbt`.
7. **Threshold Enforcement**: When verified signature count $\ge M$, the transaction is finalized (`finalizepsbt`) and broadcast to the Bitcoin network (`sendrawtransaction`).
8. **Confirmation**: Regtest block is generated to confirm the transfer on-chain.

## 4. Immutable Cryptographic Audit Chain & External Anchoring
All lifecycle events (proposals, policy rejections, signature submissions, quorums, broadcasts) are recorded into an append-only audit trail protected by SHA-256 hash chaining:
$$\text{Current Hash} = \text{SHA-256}(\text{Previous Hash} \parallel \text{Org ID} \parallel \text{Actor ID} \parallel \text{Event} \parallel \text{Ref Type} \parallel \text{Ref ID} \parallel \text{IP} \parallel \text{UTC Time} \parallel \text{JSON Details})$$

- **Out-of-Band Anchoring**: The chain tip is periodically written to `audit_anchors.jsonl`.
- **Tamper Detection**: `GET /api/audit/verify` verifies both internal sequential hash integrity and consistency with external anchor checkpoints, detecting any database rewrites or retroactive modifications.
