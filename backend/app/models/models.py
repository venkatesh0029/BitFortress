from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, Text, BigInteger, Boolean,
    DateTime, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class MemberRole(str, enum.Enum):
    ORG_ADMIN = "ORG_ADMIN"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    SIGNER = "SIGNER"
    AUDITOR = "AUDITOR"
    SYSTEM_OPERATOR = "SYSTEM_OPERATOR"

class ProposalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FINALIZED = "FINALIZED"
    BROADCAST = "BROADCAST"
    CONFIRMED = "CONFIRMED"

class ApprovalDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    treasury_wallets = relationship("TreasuryWallet", back_populates="organization", cascade="all, delete-orphan")
    spending_policies = relationship("SpendingPolicy", back_populates="organization", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    signer_profiles = relationship("SignerProfile", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(MemberRole), nullable=False, default=MemberRole.SIGNER)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

class SignerProfile(Base):
    __tablename__ = "signer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100), nullable=False)
    public_key = Column(String(130), nullable=False)  # Hex encoded compressed/uncompressed public key
    fingerprint = Column(String(8), nullable=True)    # Master key fingerprint (e.g., 73c5da0a)
    derivation_path = Column(String(100), nullable=True, default="m/48'/1'/0'/2'")
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="signer_profiles")
    treasury_assignments = relationship("TreasurySigner", back_populates="signer")
    approvals = relationship("Approval", back_populates="signer")

class TreasuryWallet(Base):
    __tablename__ = "treasury_wallets"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    wallet_name = Column(String(100), nullable=False)
    address = Column(String(100), nullable=False, index=True)  # Native Segwit P2WSH or P2SH multisig address
    redeem_script = Column(Text, nullable=True)
    descriptor = Column(Text, nullable=True)
    threshold = Column(Integer, nullable=False, default=2)     # M in M-of-N
    total_signers = Column(Integer, nullable=False, default=3) # N in M-of-N
    network = Column(String(20), default="regtest")
    balance_satoshis = Column(BigInteger, default=0)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    organization = relationship("Organization", back_populates="treasury_wallets")
    signers = relationship("TreasurySigner", back_populates="wallet", cascade="all, delete-orphan")
    proposals = relationship("TransactionProposal", back_populates="wallet", cascade="all, delete-orphan")

class TreasurySigner(Base):
    __tablename__ = "treasury_signers"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("treasury_wallets.id", ondelete="CASCADE"), nullable=False)
    signer_id = Column(Integer, ForeignKey("signer_profiles.id", ondelete="CASCADE"), nullable=False)
    signer_order = Column(Integer, default=0)

    wallet = relationship("TreasuryWallet", back_populates="signers")
    signer = relationship("SignerProfile", back_populates="treasury_assignments")

class TransactionProposal(Base):
    __tablename__ = "transaction_proposals"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("treasury_wallets.id", ondelete="CASCADE"), nullable=False)
    proposer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    destination = Column(String(100), nullable=False)
    amount = Column(BigInteger, nullable=False)  # Exact amount in satoshis
    fee_satoshis = Column(BigInteger, default=1000)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(ProposalStatus), default=ProposalStatus.PENDING, index=True)
    txid = Column(String(64), nullable=True, index=True)
    broadcast_at = Column(DateTime(timezone=True), nullable=True)
    confirmations = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    wallet = relationship("TreasuryWallet", back_populates="proposals")
    proposer = relationship("User")
    psbt_record = relationship("PSBTRecord", back_populates="proposal", uselist=False, cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="proposal", cascade="all, delete-orphan")

class PSBTRecord(Base):
    __tablename__ = "psbt_records"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("transaction_proposals.id", ondelete="CASCADE"), unique=True, nullable=False)
    unsigned_psbt = Column(Text, nullable=False)      # Base64 encoded initial PSBT
    current_psbt = Column(Text, nullable=False)       # Base64 encoded PSBT with accumulated signatures
    finalized_tx_hex = Column(Text, nullable=True)    # Hex string of fully signed, finalized tx
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    proposal = relationship("TransactionProposal", back_populates="psbt_record")

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("transaction_proposals.id", ondelete="CASCADE"), nullable=False)
    signer_id = Column(Integer, ForeignKey("signer_profiles.id", ondelete="CASCADE"), nullable=False)
    decision = Column(SQLEnum(ApprovalDecision), nullable=False)
    signature_reference = Column(String(255), nullable=True) # Derivation path / key identifier used
    signature_data = Column(Text, nullable=True)             # Signature hex or partial PSBT data
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    proposal = relationship("TransactionProposal", back_populates="approvals")
    signer = relationship("SignerProfile", back_populates="approvals")

class SpendingPolicy(Base):
    __tablename__ = "spending_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    per_transaction_limit = Column(BigInteger, default=50000000)  # satoshis (default: 0.5 BTC)
    daily_limit = Column(BigInteger, default=200000000)          # satoshis (default: 2.0 BTC)
    require_admin_override = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", back_populates="spending_policies")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False) # e.g. PROPOSAL_CREATED, SIGNATURE_ADDED, BROADCAST_SUCCESS
    reference_type = Column(String(50), nullable=True) # e.g. PROPOSAL, WALLET, POLICY
    reference_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    prev_hash = Column(String(64), nullable=True)
    curr_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    organization = relationship("Organization", back_populates="audit_events")
    actor = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="INFO") # INFO, WARNING, SUCCESS, ACTION_REQUIRED
    read_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="notifications")
