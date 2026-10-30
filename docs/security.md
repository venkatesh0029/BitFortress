# SatoshiGuard Security Controls & Threat Model

## 1. Key Custody Model
- **Zero Plaintext Private Keys in Application Database**: PostgreSQL never stores private keys. Signers maintain custody of their own signing material.
- **Client-Side Signer Isolation**: The web application never receives or transmits private keys across public network boundaries.
- **Strict Separation of Duties**: Proposers (Finance Managers) cannot approve transactions unless they are separately assigned as signers on the treasury policy.

## 2. Cryptographic Verification
- An approval is invalid without an authentic ECDSA DER signature cryptographically verified against the registered signer's secp256k1 public key.
- A user clicking an "Approve" button without providing a valid cryptographic signature will be rejected by backend authorization policies.
- PSBT integrity checks ensure that altering the recipient address or amount invalidates prior partial signatures.

## 3. Spending Policies & Rate Controls
- **Per-Transaction Spending Cap**: Prevents unauthorized large-scale treasury drainage.
- **24-Hour Rolling Volume Limit**: Protects against rapid successive withdrawals.
- **Audit Logging**: Every policy violation, signature submission, rejection, or broadcast event is logged immutably with timestamp, actor ID, and IP address.
