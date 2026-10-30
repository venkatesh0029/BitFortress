# SatoshiGuard Security Controls & Threat Model

## 1. Key Custody & Signer Device Isolation
- **Zero Plaintext Private Keys in Application Database**: PostgreSQL never stores private keys. Signers maintain independent custody of their own signing material.
- **Isolated Signer Device Architecture**: Signers operate distinct isolated custodian signing devices (represented by Bitcoin Core custodian wallets `sg_custodian_{signer_id}`). Signing keys never cross coordinator boundaries.
- **Strict Separation of Duties**: Proposers (`FINANCE_MANAGER`) cannot approve transactions unless they are separately assigned as signers on the treasury policy with a registered secp256k1 public key.

## 2. Cryptographic PSBT Verification
- **Mandatory Signature Enforcement**: An approval cannot be recorded without a valid signed PSBT containing an authentic ECDSA DER signature matching the registered signer's public key.
- **Quorum Integrity**: The quorum counter increments strictly on cryptographically verified partial signatures extracted from the PSBT, preventing empty or fraudulent approvals.
- **Tamper Protection**: Changing any transaction parameter (recipient, satoshi amount, fee, or change address) invalidates previously collected partial signatures, requiring a new proposal.

## 3. Transaction Construction & Integer Value Protection
- **Integer Satoshi Math**: Eliminates floating-point rounding hazards across inputs, fees, outputs, and change calculations.
- **Dust Protection**: Automatically rejects outputs below the Bitcoin dust threshold (546 satoshis).
- **Destination Validation**: Verifies destination addresses using Bitcoin Core `validateaddress` before PSBT construction.
- **Descriptor Metadata Enrichment**: Enriches PSBT inputs via `utxoupdatepsbt` to ensure custodians have full BIP-174 witness script context for signing.

## 4. Multi-Tenant Organization Isolation
- **Tenant Scope Enforcement**: All wallet queries, transaction listings, and proposal approvals are strictly filtered by `organization_id`.
- Users cannot access, view, or sign transactions outside their active authorized corporate organization.

## 5. Concurrency Controls & Idempotency
- **Row-Level Database Locking**: Uses `SELECT ... FOR UPDATE` on transaction proposals during the approval workflow to serialize concurrent signature submissions and prevent race conditions.
- **Controlled Broadcast State Machine**: Transactions transition atomically from `PENDING` $\to$ `SIGNED` $\to$ `BROADCAST`, preventing duplicate on-chain broadcasts.

## 6. Cryptographically Verifiable Audit Chain
- **SHA-256 Hash Chaining**: Every audit event links to the previous event hash, forming an unbroken cryptographic chain from genesis to tip.
- **Tamper Detection**: Any retroactive modification or deletion in the database breaks the chain and is immediately flagged by the verification engine (`GET /api/audit/verify`).

