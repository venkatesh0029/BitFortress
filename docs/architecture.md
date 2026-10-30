# SatoshiGuard Architecture & Technical Specification

## 1. System Overview
**SatoshiGuard** is an institutional-grade, Bitcoin-native multisignature treasury management platform. It eliminates single-point-of-failure key risk by enforcing strict threshold policies (e.g., 2-of-3, 3-of-5) before any Bitcoin transaction can be finalized and broadcast.

```
                          SatoshiGuard Architecture
                                     |
               +---------------------+---------------------+
               |                                           |
     Next.js 15+ Frontend                       Signer Hardware/Client
     (App Router, TypeScript)                   (Secp256k1 Private Keys)
               |                                           |
               | HTTPS / JSON REST API                     | PSBT Signatures
               v                                           v
       FastAPI Backend Layer <=============================+
               |
  +------------+------------+---------------+----------------+
  |                         |               |                |
Auth & RBAC            Treasury Core   Policy Engine    Audit Trail
(JWT, Argon2/Bcrypt)   (PSBT Pipeline) (Spending Limits)(Immutable Log)
  |                         |               |                |
  +------------+------------+---------------+----------------+
               |
  +------------+--------------------+
  |                                 |
PostgreSQL 18              Bitcoin Core v28 (Regtest)
- Organizations            - PSBT Creation (`createpsbt`)
- Signer Profiles          - PSBT Analysis (`analyzepsbt`)
- Treasury Wallets         - Combination (`combinepsbt`)
- Transaction Proposals    - Finalization (`finalizepsbt`)
- Audit Logs               - Node RPC Broadcast
```

## 2. PSBT Transaction Lifecycle
1. **Proposal Creation**: Authorized finance manager submits destination address, satoshi amount, and business justification.
2. **Policy Verification**: Backend policy engine calculates if the transaction satisfies per-transaction limits and 24-hour cumulative limits.
3. **PSBT Construction**: Bitcoin Core integration layer creates an unsigned PSBT spending selected multisig UTXOs.
4. **Signer Notification**: Eligible signers receive in-app alerts and inspect raw transaction parameters.
5. **Independent Signing**: Signers review transaction inputs, outputs, destination, and fee, then generate ECDSA DER signatures.
6. **Signature Verification & Merging**: Backend verifies each partial signature and combines them via `combinepsbt`.
7. **Threshold Enforcement**: When valid signature count $\ge M$, the transaction is finalized (`finalizepsbt`) and broadcast to the Bitcoin network (`sendrawtransaction`).
8. **Confirmation**: Regtest block is generated to confirm the transfer on-chain.
