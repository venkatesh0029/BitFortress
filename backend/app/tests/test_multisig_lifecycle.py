import pytest
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.models import (
    User, Organization, OrganizationMember, MemberRole,
    SignerProfile, TreasuryWallet, TreasurySigner,
    TransactionProposal, PSBTRecord, Approval, SpendingPolicy,
    ProposalStatus, ApprovalDecision
)
from app.bitcoin.rpc_client import bitcoin_rpc, BitcoinRPCClient
from app.bitcoin.wallet_service import wallet_service
from app.bitcoin.psbt_service import psbt_service
from app.services.approval_service import approval_service
from app.services.signer_device_service import signer_device_service
from app.services.audit_service import audit_service
from app.services.transaction_service import transaction_service

@pytest.fixture(scope="module")
def setup_regtest_multisig():
    """Sets up an end-to-end 2-of-3 multisig environment with 3 isolated custodian wallets on Bitcoin Regtest."""
    db = SessionLocal()
    wallet_service.ensure_miner_wallet_ready()

    # 1. Dedicated test organization
    org = db.query(Organization).filter(Organization.name == "E2E Clean Multisig Corp").first()
    if not org:
        org = Organization(name="E2E Clean Multisig Corp", status="ACTIVE")
        db.add(org)
        db.flush()

    # 2. Spending Policy
    policy = db.query(SpendingPolicy).filter(SpendingPolicy.organization_id == org.id).first()
    if not policy:
        policy = SpendingPolicy(
            organization_id=org.id,
            per_transaction_limit=100000000, # 1.0 BTC
            daily_limit=500000000            # 5.0 BTC
        )
        db.add(policy)
        db.flush()

    # 3. Create 3 isolated custodian wallets and users
    custodian_users = []
    signer_profiles = []
    pubkeys = []

    for i in range(1, 4):
        email = f"e2e_clean_custodian_{i}@test.io"
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                password_hash="testpassword",
                full_name=f"E2E Custodian {i}",
                status="ACTIVE"
            )
            db.add(u)
            db.flush()

        mem = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == u.id
        ).first()
        if not mem:
            mem = OrganizationMember(
                organization_id=org.id,
                user_id=u.id,
                role=MemberRole.SIGNER
            )
            db.add(mem)
            db.flush()

        custodian_users.append(u)

        sp = db.query(SignerProfile).filter(SignerProfile.user_id == u.id).first()
        if not sp:
            sp = SignerProfile(
                user_id=u.id,
                label=f"Clean HSM-0{i}",
                public_key="placeholder",
                fingerprint=f"clean00{i}",
                derivation_path="m/48'/1'/0'/2'",
                status="ACTIVE"
            )
            db.add(sp)
            db.flush()

        # Stable pubkey from isolated Bitcoin Core custodian wallet matching sp.id
        pk = signer_device_service.get_device_public_key(sp.id)
        sp.public_key = pk
        pubkeys.append(pk)
        signer_profiles.append(sp)

    # 4. Create 2-of-3 Multisig Wallet
    ms_config = wallet_service.create_multisig_config(threshold=2, public_keys=pubkeys)
    w = db.query(TreasuryWallet).filter(
        TreasuryWallet.organization_id == org.id,
        TreasuryWallet.wallet_name == "Clean 2-of-3 Multisig Reserve"
    ).first()
    if not w:
        w = TreasuryWallet(
            organization_id=org.id,
            wallet_name="Clean 2-of-3 Multisig Reserve",
            address=ms_config["address"],
            redeem_script=ms_config["redeem_script"],
            descriptor=ms_config["descriptor"],
            threshold=2,
            total_signers=3,
            balance_satoshis=0,
            network="regtest",
            status="ACTIVE"
        )
        db.add(w)
        db.flush()

        for idx, sp in enumerate(signer_profiles):
            ts = TreasurySigner(wallet_id=w.id, signer_id=sp.id, signer_order=idx)
            db.add(ts)
    else:
        w.address = ms_config["address"]
        w.redeem_script = ms_config["redeem_script"]
        w.descriptor = ms_config["descriptor"]
        db.flush()

    db.commit()

    # 5. Fund multisig wallet with 2 BTC
    wallet_service.fund_address(w.address, 2.0)
    sats, _ = wallet_service.get_address_balance_satoshis(w.address)
    w.balance_satoshis = sats
    db.commit()

    yield {
        "db": db,
        "org": org,
        "wallet": w,
        "custodian_users": custodian_users,
        "signer_profiles": signer_profiles,
        "pubkeys": pubkeys
    }

    db.close()


def test_empty_or_unsigned_psbt_rejected(setup_regtest_multisig):
    """Verifies Critical #1: The approval counter CANNOT increase without a cryptographically signed PSBT."""
    ctx = setup_regtest_multisig
    db = ctx["db"]
    wallet = ctx["wallet"]
    user1 = ctx["custodian_users"][0]

    miner_rpc = BitcoinRPCClient(wallet_name="sg_miner_funder")
    dest_addr = miner_rpc.call("getnewaddress", ["e2e_clean_dest_1", "bech32"])

    prop = transaction_service.propose_transaction(
        db=db,
        wallet_id=wallet.id,
        proposer_id=user1.id,
        destination=dest_addr,
        amount_satoshis=5000000,
        fee_satoshis=2000,
        description="Clean Test 1 - Unsigned Reject"
    )

    # 1. Attempt approval with None / Empty PSBT
    with pytest.raises(ValueError, match="A cryptographically signed PSBT is required"):
        approval_service.approve_proposal(
            db=db,
            proposal_id=prop.id,
            user_id=user1.id,
            signed_psbt=""
        )

    # 2. Attempt approval with unsigned raw PSBT (no partial signatures)
    with pytest.raises(ValueError, match="does not contain a cryptographic signature matching signer public key"):
        approval_service.approve_proposal(
            db=db,
            proposal_id=prop.id,
            user_id=user1.id,
            signed_psbt=prop.psbt_record.unsigned_psbt
        )

    # Verified: Status remains PENDING, 0 approvals recorded
    db.refresh(prop)
    assert prop.status == ProposalStatus.PENDING
    assert len(prop.approvals) == 0


def test_full_multisig_quorum_lifecycle_and_broadcast(setup_regtest_multisig):
    """
    Addresses Reviewer's Challenge:
    - 1 signer signs -> Threshold NOT met (1/2) -> Cannot broadcast
    - Same signer duplicate approval attempt -> Rejected
    - 2nd independent valid signer signs -> Threshold MET (2/2) -> Automatically broadcasts to Bitcoin Regtest!
    """
    ctx = setup_regtest_multisig
    db = ctx["db"]
    wallet = ctx["wallet"]
    user1 = ctx["custodian_users"][0]
    sp1 = ctx["signer_profiles"][0]
    user2 = ctx["custodian_users"][1]
    sp2 = ctx["signer_profiles"][1]

    miner_rpc = BitcoinRPCClient(wallet_name="sg_miner_funder")
    dest_addr = miner_rpc.call("getnewaddress", ["e2e_clean_dest_2", "bech32"])

    prop = transaction_service.propose_transaction(
        db=db,
        wallet_id=wallet.id,
        proposer_id=user1.id,
        destination=dest_addr,
        amount_satoshis=10000000, # 0.1 BTC
        fee_satoshis=2000,
        description="Clean Test 2 - Full 2-of-3 Quorum Flow"
    )

    # Step A: Custodian 1 signs with isolated device
    sign_res1 = signer_device_service.sign_psbt_with_device(sp1.id, prop.psbt_record.unsigned_psbt)
    signed_psbt_1 = sign_res1["signed_psbt"]

    # Submit Custodian 1's signature
    approve_res1 = approval_service.approve_proposal(
        db=db,
        proposal_id=prop.id,
        user_id=user1.id,
        signed_psbt=signed_psbt_1
    )

    # Threshold is 2, collected 1 -> Proposal CANNOT broadcast
    assert approve_res1["approved_count"] == 1
    assert approve_res1["threshold"] == 2
    assert approve_res1["broadcast_info"] is None

    db.refresh(prop)
    assert prop.status == ProposalStatus.PENDING
    assert prop.txid is None

    # Step B: Custodian 1 attempts duplicate approval -> MUST BE REJECTED
    with pytest.raises(ValueError, match="You have already submitted a decision"):
        approval_service.approve_proposal(
            db=db,
            proposal_id=prop.id,
            user_id=user1.id,
            signed_psbt=signed_psbt_1
        )

    # Step C: Custodian 2 signs independently with isolated device
    sign_res2 = signer_device_service.sign_psbt_with_device(sp2.id, prop.psbt_record.unsigned_psbt)
    signed_psbt_2 = sign_res2["signed_psbt"]

    # Submit Custodian 2's signature -> Quorum achieved!
    approve_res2 = approval_service.approve_proposal(
        db=db,
        proposal_id=prop.id,
        user_id=user2.id,
        signed_psbt=signed_psbt_2
    )

    assert approve_res2["approved_count"] == 2
    assert approve_res2["threshold"] == 2
    assert approve_res2["broadcast_info"] is not None
    assert approve_res2["broadcast_info"]["broadcast"] is True

    # Step D: Verified on-chain broadcast to Bitcoin network
    db.refresh(prop)
    assert prop.status == ProposalStatus.BROADCAST
    assert prop.txid is not None
    assert len(prop.txid) == 64
    assert prop.confirmations >= 1


def test_tampered_psbt_rejected(setup_regtest_multisig):
    """Verifies that a modified or tampered PSBT cannot reuse prior signatures."""
    ctx = setup_regtest_multisig
    db = ctx["db"]
    wallet = ctx["wallet"]
    user1 = ctx["custodian_users"][0]
    sp1 = ctx["signer_profiles"][0]

    miner_rpc = BitcoinRPCClient(wallet_name="sg_miner_funder")
    dest_a = miner_rpc.call("getnewaddress", ["clean_dest_a", "bech32"])
    dest_b = miner_rpc.call("getnewaddress", ["clean_dest_b", "bech32"])

    # Create proposal A
    prop_a = transaction_service.propose_transaction(
        db=db,
        wallet_id=wallet.id,
        proposer_id=user1.id,
        destination=dest_a,
        amount_satoshis=1000000,
        fee_satoshis=2000,
        description="Clean Proposal A - Legitimate"
    )

    # Sign proposal A
    sign_a = signer_device_service.sign_psbt_with_device(sp1.id, prop_a.psbt_record.unsigned_psbt)

    # Create proposal B with different destination
    prop_b = transaction_service.propose_transaction(
        db=db,
        wallet_id=wallet.id,
        proposer_id=user1.id,
        destination=dest_b,
        amount_satoshis=2000000,
        fee_satoshis=2000,
        description="Clean Proposal B - Modified"
    )

    # Attacker tries to submit signature from Proposal A into Proposal B
    with pytest.raises(ValueError):
        approval_service.approve_proposal(
            db=db,
            proposal_id=prop_b.id,
            user_id=user1.id,
            signed_psbt=sign_a["signed_psbt"]
        )


def test_cryptographic_hash_chained_audit_integrity():
    """Verifies High #5: SHA-256 hash-chained audit log and tamper-detection proof."""
    db = SessionLocal()
    # Create dedicated isolated test organization
    audit_org = Organization(name="Audit Hash Chain Isolated Test Corp", status="ACTIVE")
    db.add(audit_org)
    db.commit()

    # Record 3 chained audit events
    e1 = audit_service.record_event(
        db=db,
        organization_id=audit_org.id,
        event_type="TEST_EVENT_GENESIS",
        details={"block": 1}
    )

    e2 = audit_service.record_event(
        db=db,
        organization_id=audit_org.id,
        event_type="TEST_EVENT_MIDDLE",
        details={"block": 2}
    )

    assert e2.prev_hash == e1.curr_hash

    e3 = audit_service.record_event(
        db=db,
        organization_id=audit_org.id,
        event_type="TEST_EVENT_TIP",
        details={"block": 3}
    )

    assert e3.prev_hash == e2.curr_hash

    # Verify intact chain
    verification = audit_service.verify_audit_chain(db, audit_org.id)
    assert verification["is_valid"] is True
    assert verification["total_records"] == 3

    # Simulate Malicious Database Tampering: attacker modifies details of e1
    db.execute(
        text("UPDATE audit_events SET details = '{\"tampered\": true}' WHERE id = :id"),
        {"id": e1.id}
    )
    db.commit()

    # Verify that the cryptographic hash chain catches the tampering immediately!
    tamper_check = audit_service.verify_audit_chain(db, audit_org.id)
    assert tamper_check["is_valid"] is False
    assert tamper_check["broken_at_id"] == e1.id
    assert "tampering detected" in tamper_check["error"]
    db.close()
