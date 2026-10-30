import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api import (
    auth, organizations, treasury, transactions, approvals, signers,
    policies, audit, notifications, node
)
from app.models.models import (
    User, Organization, OrganizationMember, MemberRole, SignerProfile,
    TreasuryWallet, TreasurySigner, SpendingPolicy
)
import binascii
from app.core.security import get_password_hash
from app.bitcoin.keys import generate_keypair, hash160
from app.bitcoin.wallet_service import wallet_service
from app.services.signer_device_service import signer_device_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bitfortress.main")

def seed_initial_demo_data():
    """Seeds rich corporate demo data for immediate testing and demonstration."""
    db = SessionLocal()
    try:
        # Check if users already exist
        if db.query(User).count() > 0:
            return

        logger.info("Seeding initial corporate treasury demonstration environment...")

        # 1. Organization
        org = Organization(name="BitFortress Capital & Treasury", status="ACTIVE")
        db.add(org)
        db.flush()

        # 2. Spending Policy (0.5 BTC per transaction, 2.0 BTC daily)
        policy = SpendingPolicy(
            organization_id=org.id,
            per_transaction_limit=50_000_000,
            daily_limit=200_000_000,
            require_admin_override=True,
            is_active=True
        )
        db.add(policy)

        # 3. Create Users
        default_pw = get_password_hash("password123")
        users_data = [
            ("admin@satoshiguard.io", "Sarah Lin (Chief Risk Officer)", MemberRole.ORG_ADMIN),
            ("finance@satoshiguard.io", "Michael Chang (VP Finance)", MemberRole.FINANCE_MANAGER),
            ("signer1@satoshiguard.io", "David Kim (Treasury Signer 1)", MemberRole.SIGNER),
            ("signer2@satoshiguard.io", "Elena Rostova (Executive Signer 2)", MemberRole.SIGNER),
            ("signer3@satoshiguard.io", "Marcus Vance (Security Signer 3)", MemberRole.SIGNER),
            ("auditor@satoshiguard.io", "Rachel Adams (Internal Audit)", MemberRole.AUDITOR),
        ]

        created_users = {}
        for email, name, role in users_data:
            user = User(
                email=email,
                full_name=name,
                password_hash=default_pw,
                status="ACTIVE"
            )
            db.add(user)
            db.flush()
            created_users[email] = user

            membership = OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role=role
            )
            db.add(membership)

        # 4. Generate Keypairs and Signer Profiles for signers using isolated custodian devices
        signer_emails = ["signer1@satoshiguard.io", "signer2@satoshiguard.io", "signer3@satoshiguard.io"]
        signer_profiles = []
        for idx, email in enumerate(signer_emails, 1):
            try:
                device_pk = signer_device_service.get_device_public_key(idx)
                fp = hash160(binascii.unhexlify(device_pk))[:4].hex()
            except Exception:
                kp = generate_keypair()
                device_pk = kp["public_key"]
                fp = kp["fingerprint"]

            sp = SignerProfile(
                user_id=created_users[email].id,
                label=f"Hardware Key HSM-{idx:02d}",
                public_key=device_pk,
                fingerprint=fp,
                derivation_path="m/48'/1'/0'/2'",
                status="ACTIVE"
            )
            db.add(sp)
            db.flush()
            signer_profiles.append(sp)

        # 5. Create 2-of-3 Multisig Treasury Wallet on Regtest
        pubkeys = [sp.public_key for sp in signer_profiles]
        try:
            multisig_config = wallet_service.create_multisig_config(threshold=2, public_keys=pubkeys)
            
            treasury = TreasuryWallet(
                organization_id=org.id,
                wallet_name="Corporate Primary Reserve",
                address=multisig_config["address"],
                redeem_script=multisig_config["redeem_script"],
                descriptor=multisig_config["descriptor"],
                threshold=2,
                total_signers=3,
                balance_satoshis=0,
                network="regtest",
                status="ACTIVE"
            )
            db.add(treasury)
            db.flush()

            for idx, sp in enumerate(signer_profiles):
                ts = TreasurySigner(wallet_id=treasury.id, signer_id=sp.id, signer_order=idx)
                db.add(ts)

            db.commit()

            # 6. Fund the treasury with 10 BTC and confirm on regtest
            logger.info(f"Funding seeded treasury address {treasury.address} with 10 BTC on Regtest...")
            try:
                fund_res = wallet_service.fund_address(treasury.address, 10.0)
                sats, _ = wallet_service.get_address_balance_satoshis(treasury.address)
                treasury.balance_satoshis = sats
                db.commit()
                logger.info(f"Seeded Treasury ready with {sats} satoshis ({sats/100_000_000} BTC)!")
            except Exception as e:
                logger.warning(f"Could not fund treasury on startup (node might be initializing): {e}")

        except Exception as e:
            logger.error(f"Failed to create initial multisig config: {e}")
            db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding demo data: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    # Seed initial demo data
    seed_initial_demo_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="BitFortress: Bitcoin-Based Multisignature Corporate Treasury Management System",
    lifespan=lifespan
)

# CORS Middleware configured for Next.js development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(organizations.router, prefix=settings.API_V1_PREFIX)
app.include_router(treasury.router, prefix=settings.API_V1_PREFIX)
app.include_router(transactions.router, prefix=settings.API_V1_PREFIX)
app.include_router(approvals.router, prefix=settings.API_V1_PREFIX)
app.include_router(signers.router, prefix=settings.API_V1_PREFIX)
app.include_router(policies.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
app.include_router(node.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "service": "BitFortress API",
        "status": "OPERATIONAL",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
