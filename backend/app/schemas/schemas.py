from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field
from app.models.models import MemberRole, ProposalStatus, ApprovalDecision

# Auth & User
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    status: str
    created_at: datetime
    role: Optional[str] = None
    organization_id: Optional[int] = None
    must_change_password: Optional[bool] = False

    class Config:
        from_attributes = True

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Organization
class OrganizationCreate(BaseModel):
    name: str

class OrganizationResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class MemberAdd(BaseModel):
    email: EmailStr
    role: MemberRole

class MemberResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: MemberRole
    user: UserResponse
    created_at: datetime

    class Config:
        from_attributes = True

# Signer Profiles
class SignerProfileCreate(BaseModel):
    label: str
    public_key: str
    fingerprint: Optional[str] = None
    derivation_path: Optional[str] = "m/48'/1'/0'/2'"

class SignerProfileResponse(BaseModel):
    id: int
    user_id: int
    label: str
    public_key: str
    fingerprint: Optional[str]
    derivation_path: Optional[str]
    status: str
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

# Treasury Wallet
class TreasuryCreate(BaseModel):
    wallet_name: str
    threshold: int = Field(ge=1, le=15)
    signer_ids: List[int]

class TreasurySignerInfo(BaseModel):
    signer_id: int
    label: str
    public_key: str
    user_name: str

class TreasuryResponse(BaseModel):
    id: int
    organization_id: int
    wallet_name: str
    address: str
    threshold: int
    total_signers: int
    descriptor: Optional[str]
    redeem_script: Optional[str]
    balance_satoshis: int
    balance_btc: float
    network: str
    status: str
    created_at: datetime
    signers: List[TreasurySignerInfo] = []

    class Config:
        from_attributes = True

# Proposals
class ProposalCreate(BaseModel):
    wallet_id: int
    destination: str
    amount_satoshis: int = Field(gt=0)
    fee_satoshis: Optional[int] = 1000
    description: str

class ApprovalResponse(BaseModel):
    id: int
    signer_id: int
    signer_name: str
    signer_label: str
    public_key: str
    decision: ApprovalDecision
    signature_reference: Optional[str]
    rejection_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ProposalResponse(BaseModel):
    id: int
    wallet_id: int
    wallet_name: str
    proposer_id: int
    proposer_name: str
    destination: str
    amount_satoshis: int
    amount_btc: float
    fee_satoshis: int
    description: str
    status: ProposalStatus
    txid: Optional[str]
    broadcast_at: Optional[datetime]
    confirmations: int
    threshold: int
    approvals_count: int
    rejections_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProposalDetailResponse(ProposalResponse):
    unsigned_psbt: Optional[str]
    current_psbt: Optional[str]
    finalized_tx_hex: Optional[str]
    approvals: List[ApprovalResponse] = []
    signers: List[TreasurySignerInfo] = []

# Approval Submission
class SignApprovalRequest(BaseModel):
    proposal_id: int
    signed_psbt: str # Base64 PSBT containing the signer's partial cryptographic signature
    signature_reference: Optional[str] = None

class RejectApprovalRequest(BaseModel):
    proposal_id: int
    reason: str

# Policies
class SpendingPolicyCreate(BaseModel):
    per_transaction_limit: int
    daily_limit: int
    require_admin_override: bool = True

class SpendingPolicyResponse(BaseModel):
    id: int
    organization_id: int
    per_transaction_limit: int
    daily_limit: int
    per_tx_btc: float
    daily_btc: float
    require_admin_override: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Audit
class AuditEventResponse(BaseModel):
    id: int
    organization_id: int
    actor_id: Optional[int]
    actor_name: Optional[str]
    event_type: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    prev_hash: Optional[str] = None
    curr_hash: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Notifications
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    category: str
    read_status: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Regtest Node Admin
class MineRequest(BaseModel):
    blocks: int = 1
    address: Optional[str] = None

class FundTreasuryRequest(BaseModel):
    wallet_id: int
    amount_btc: float = 5.0
