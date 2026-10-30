import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.bitcoin.keys import generate_keypair, sign_hash_with_privkey, verify_signature
from app.services.policy_service import policy_service
from app.core.database import SessionLocal
from app.models.models import Organization, SpendingPolicy, User, TransactionProposal, ProposalStatus, TreasuryWallet

def test_password_hashing():
    pw = "SuperSecureVaultPass123"
    h = get_password_hash(pw)
    assert verify_password(pw, h) is True
    assert verify_password("WrongPass", h) is False

def test_jwt_token_creation_and_decoding():
    payload = {"sub": "42", "email": "officer@bitfortress.io", "role": "SIGNER"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["email"] == "officer@bitfortress.io"
    assert decoded["role"] == "SIGNER"

def test_secp256k1_key_generation_and_signatures():
    kp = generate_keypair()
    assert len(kp["public_key"]) == 66  # Compressed 33-byte hex
    assert len(kp["private_key"]) == 64
    assert len(kp["fingerprint"]) == 8

    # Sign a test hash
    test_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    sig = sign_hash_with_privkey(test_hash, kp["private_key"])
    assert len(sig) > 130 # DER signature + sighash byte

    # Verify signature
    import binascii
    is_valid = verify_signature(kp["public_key"], binascii.unhexlify(test_hash), sig)
    assert is_valid is True

    # Check that altered signature fails
    fake_sig = sig[:-4] + "0000"
    assert verify_signature(kp["public_key"], binascii.unhexlify(test_hash), fake_sig) is False

def test_spending_policy_enforcement():
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Test Org")
            db.add(org)
            db.commit()
            db.refresh(org)

        policy = policy_service.get_or_create_policy(db, org.id)
        policy.per_transaction_limit = 50_000_000 # 0.5 BTC
        policy.daily_limit = 200_000_000          # 2.0 BTC
        db.commit()

        # 0.4 BTC should pass
        allowed, reason = policy_service.validate_proposal_against_policies(db, org.id, 40_000_000)
        assert allowed is True
        assert reason is None

        # 0.6 BTC should be blocked by per-tx limit
        allowed, reason = policy_service.validate_proposal_against_policies(db, org.id, 60_000_000)
        assert allowed is False
        assert "exceeds per-transaction spending limit" in reason

    finally:
        db.close()

def test_duplicate_signature_and_rejection_logic():
    db = SessionLocal()
    try:
        from app.models.models import Approval, SignerProfile, TreasurySigner, ApprovalDecision
        from app.services.approval_service import approval_service

        # Get signer 1 user and their authorized treasury wallet
        signer1_user = db.query(User).filter(User.email == "signer1@satoshiguard.io").first()
        sp = db.query(SignerProfile).filter(SignerProfile.user_id == signer1_user.id).first()
        ts = db.query(TreasurySigner).filter(TreasurySigner.signer_id == sp.id).first()
        wallet = db.query(TreasuryWallet).filter(TreasuryWallet.id == ts.wallet_id).first()

        proposal = TransactionProposal(
            wallet_id=wallet.id,
            proposer_id=signer1_user.id,
            destination="bcrt1qtestdest998877",
            amount=1000000,
            fee_satoshis=1000,
            description="Test payment for rejection",
            status=ProposalStatus.PENDING
        )
        db.add(proposal)
        db.commit()
        db.refresh(proposal)

        # Test rejection flow
        res = approval_service.reject_proposal(
            db=db,
            proposal_id=proposal.id,
            user_id=signer1_user.id,
            reason="Unrecognized corporate vendor"
        )
        assert res["status"] == ProposalStatus.REJECTED

        # Test that once rejected, subsequent rejections fail
        with pytest.raises(ValueError, match="Cannot reject proposal in"):
            approval_service.reject_proposal(
                db=db,
                proposal_id=proposal.id,
                user_id=signer1_user.id,
                reason="Duplicate attempt"
            )

        # Test that rejected proposal cannot be approved
        with pytest.raises(ValueError, match="Cannot approve proposal in"):
            approval_service.approve_proposal(
                db=db,
                proposal_id=proposal.id,
                user_id=signer1_user.id,
                signed_psbt="cHNidP8BAHICAAAA..."
            )

    finally:
        db.close()
