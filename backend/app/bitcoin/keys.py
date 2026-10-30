import hashlib
import binascii
import ecdsa
from typing import Tuple, Dict

def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def hash160(data: bytes) -> bytes:
    h = hashlib.sha256(data).digest()
    r = hashlib.new('ripemd160')
    r.update(h)
    return r.digest()

def generate_keypair() -> Dict[str, str]:
    """Generates a secp256k1 private key and its compressed public key (hex) with fingerprint."""
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    
    # Compressed public key format: prefix 02 (if y is even) or 03 (if y is odd) + 32-byte x
    x = vk.pubkey.point.x()
    y = vk.pubkey.point.y()
    prefix = b'\x02' if y % 2 == 0 else b'\x03'
    pubkey_bytes = prefix + x.to_bytes(32, 'big')
    pubkey_hex = binascii.hexlify(pubkey_bytes).decode('ascii')
    
    # Fingerprint is the first 4 bytes of hash160(pubkey)
    fp = hash160(pubkey_bytes)[:4]
    fingerprint_hex = binascii.hexlify(fp).decode('ascii')
    
    # Private key in hex
    privkey_hex = binascii.hexlify(sk.to_string()).decode('ascii')
    
    return {
        "private_key": privkey_hex,
        "public_key": pubkey_hex,
        "fingerprint": fingerprint_hex,
        "derivation_path": "m/48'/1'/0'/2'"
    }

def sign_hash_with_privkey(message_hash_hex: str, privkey_hex: str) -> str:
    """Signs a 32-byte hex hash using secp256k1 and returns DER-encoded signature + SIGHASH_ALL (01) hex."""
    msg_hash = binascii.unhexlify(message_hash_hex)
    sk = ecdsa.SigningKey.from_string(binascii.unhexlify(privkey_hex), curve=ecdsa.SECP256k1)
    sig_der = sk.sign_digest(msg_hash, sigencode=ecdsa.util.sigencode_der)
    # Append SIGHASH_ALL (0x01)
    full_sig = sig_der + b'\x01'
    return binascii.hexlify(full_sig).decode('ascii')

def verify_signature(pubkey_hex: str, message_hash_bytes: bytes, sig_der_hex: str) -> bool:
    """Verifies a DER signature (with or without sighash byte) against a compressed public key."""
    try:
        pubkey_bytes = binascii.unhexlify(pubkey_hex)
        sig_bytes = binascii.unhexlify(sig_der_hex)
        # Strip trailing SIGHASH byte if present (e.g. 0x01)
        if len(sig_bytes) > 70 and sig_bytes[-1] in [1, 2, 3, 0x81, 0x82, 0x83]:
            sig_bytes = sig_bytes[:-1]
            
        vk = ecdsa.VerifyingKey.from_string(pubkey_bytes, curve=ecdsa.SECP256k1)
        return vk.verify_digest(sig_bytes, message_hash_bytes, sigdecode=ecdsa.util.sigdecode_der)
    except Exception:
        return False
