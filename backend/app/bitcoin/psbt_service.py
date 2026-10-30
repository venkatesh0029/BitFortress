import logging
import base64
import struct
import hashlib
import ecdsa
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple
from app.bitcoin.rpc_client import bitcoin_rpc, BitcoinRPCException
from app.bitcoin.wallet_service import wallet_service

logger = logging.getLogger("bitfortress.bitcoin.psbt")

# SegWit standard dust limit in satoshis
DUST_LIMIT_SATOSHIS = 546

def sats_to_btc_str(sats: int) -> str:
    """Converts integer satoshis to exact 8-decimal Bitcoin string to prevent floating-point inaccuracies."""
    btc_dec = (Decimal(sats) / Decimal(100_000_000)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    return f"{btc_dec:.8f}"

def sha256d(b: bytes) -> bytes:
    """Computes double SHA-256 hash."""
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def ser_varint(n: int) -> bytes:
    """Serializes integer into Bitcoin protocol variable length integer format."""
    if n < 0xfd:
        return struct.pack('<B', n)
    elif n <= 0xffff:
        return b'\xfd' + struct.pack('<H', n)
    elif n <= 0xffffffff:
        return b'\xfe' + struct.pack('<I', n)
    else:
        return b'\xff' + struct.pack('<Q', n)

def compute_bip143_sighash_for_input(decoded_psbt: Dict[str, Any], input_idx: int) -> bytes:
    """
    Computes the exact 32-byte BIP-143 signature hash for a SegWit input (P2WSH/P2SH-P2WSH).
    Formula: hash256(nVersion || hashPrevouts || hashSequence || outpoint || scriptCode || value || nSequence || hashOutputs || nLockTime || sighashType)
    """
    tx = decoded_psbt["tx"]
    vin = tx["vin"]
    vout = tx["vout"]

    # 1. hashPrevouts (32 bytes)
    prevouts = b"".join([bytes.fromhex(i["txid"])[::-1] + struct.pack("<I", i["vout"]) for i in vin])
    hashPrevouts = sha256d(prevouts)

    # 2. hashSequence (32 bytes)
    sequences = b"".join([struct.pack("<I", i["sequence"]) for i in vin])
    hashSequence = sha256d(sequences)

    # 3. hashOutputs (32 bytes)
    outputs = b""
    for o in vout:
        sats = int(round(Decimal(str(o["value"])) * Decimal(100_000_000)))
        spk = bytes.fromhex(o["scriptPubKey"]["hex"])
        outputs += struct.pack("<Q", sats) + ser_varint(len(spk)) + spk
    hashOutputs = sha256d(outputs)

    # Target input details
    inp = decoded_psbt["inputs"][input_idx]
    target_vin = vin[input_idx]
    outpoint = bytes.fromhex(target_vin["txid"])[::-1] + struct.pack("<I", target_vin["vout"])
    nSequence = struct.pack("<I", target_vin["sequence"])

    # ScriptCode: for P2WSH it is the witnessScript with varint length prefix
    if "witness_script" in inp and "hex" in inp["witness_script"]:
        wscript = bytes.fromhex(inp["witness_script"]["hex"])
    elif "redeem_script" in inp and "hex" in inp["redeem_script"]:
        wscript = bytes.fromhex(inp["redeem_script"]["hex"])
    else:
        raise ValueError(f"Input {input_idx} lacks witness_script or redeem_script for sighash calculation.")

    scriptCode = ser_varint(len(wscript)) + wscript

    # Amount of input (8-byte little-endian satoshis)
    if "witness_utxo" in inp:
        val_sats = int(round(Decimal(str(inp["witness_utxo"]["amount"])) * Decimal(100_000_000)))
    else:
        raise ValueError(f"Input {input_idx} lacks witness_utxo for SegWit sighash calculation.")

    nVersion = struct.pack("<i", tx["version"])
    nLockTime = struct.pack("<I", tx["locktime"])
    nHashType = struct.pack("<I", 1)  # SIGHASH_ALL

    preimage = (
        nVersion +
        hashPrevouts +
        hashSequence +
        outpoint +
        scriptCode +
        struct.pack("<Q", val_sats) +
        nSequence +
        hashOutputs +
        nLockTime +
        nHashType
    )
    return sha256d(preimage)


class PSBTService:
    def estimate_fee(self, inputs_count: int, outputs_count: int, threshold: int, total_signers: int, fee_rate_sat_vb: int = 2) -> int:
        """
        Estimates the virtual size (vB) and fee for a Native SegWit/P2SH multisig transaction.
        Formula: Header (~11 vB) + Inputs (P2WSH multisig ~ 105 + 72 * threshold vB) + Outputs (~32 vB each)
        """
        approx_input_vsize = 105 + (72 * threshold)
        approx_output_vsize = 32
        estimated_vsize = 11 + (inputs_count * approx_input_vsize) + (outputs_count * approx_output_vsize)
        estimated_fee = max(1000, estimated_vsize * fee_rate_sat_vb)
        return estimated_fee

    def create_multisig_psbt(
        self,
        multisig_address: str,
        redeem_script: str,
        descriptor: str,
        destination_address: str,
        amount_satoshis: int,
        fee_satoshis: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Constructs a Partially Signed Bitcoin Transaction (PSBT) with strict integer satoshi accounting,
        exact decimal string serialization, dynamic Bitcoin Core fee estimation, and dust protection.
        """
        # 1. Validate inputs and destination address format
        if amount_satoshis <= DUST_LIMIT_SATOSHIS:
            raise ValueError(f"Output amount ({amount_satoshis} sats) is below the Bitcoin dust threshold ({DUST_LIMIT_SATOSHIS} sats).")

        # Validate destination address via Bitcoin Core
        try:
            val_info = bitcoin_rpc.call("validateaddress", [destination_address])
            if not val_info.get("isvalid", False):
                raise ValueError(f"Invalid Bitcoin destination address: '{destination_address}'")
        except BitcoinRPCException as e:
            raise ValueError(f"Bitcoin address validation error: {e.message}")

        # 2. Fetch unspent UTXOs for the multisig address
        total_balance, utxos = wallet_service.get_address_balance_satoshis(multisig_address)
        if not utxos:
            raise ValueError(f"No spendable UTXOs found for treasury address '{multisig_address}'. Current balance: {total_balance} sats.")

        # 3. Dynamic fee calculation via Bitcoin Core fee estimation or smart fallback
        if fee_satoshis and fee_satoshis > 0:
            nominal_fee = fee_satoshis
        else:
            try:
                fee_est = bitcoin_rpc.call("estimatesmartfee", [2])
                feerate_btc_kvb = fee_est.get("feerate", 0.00002)
                feerate_sat_vb = max(1, int(round(Decimal(str(feerate_btc_kvb)) * Decimal(100_000_000) / Decimal(1000))))
            except Exception:
                feerate_sat_vb = 2
            nominal_fee = self.estimate_fee(len(utxos), 2, 2, 3, feerate_sat_vb)

        total_needed = amount_satoshis + nominal_fee

        if total_balance < total_needed:
            raise ValueError(
                f"Insufficient funds in treasury: balance is {total_balance} sats, but {total_needed} sats needed (including {nominal_fee} sats fee)."
            )

        # 4. Select UTXOs to cover total_needed (Largest-First Coin Selection)
        sorted_utxos = sorted(utxos, key=lambda u: u["amount_satoshis"], reverse=True)
        selected_utxos = []
        accumulated_sats = 0
        for utxo in sorted_utxos:
            selected_utxos.append(utxo)
            accumulated_sats += utxo["amount_satoshis"]
            if accumulated_sats >= total_needed:
                break

        if accumulated_sats < total_needed:
            raise ValueError(f"Selected UTXOs ({accumulated_sats} sats) cannot cover required {total_needed} sats.")

        # 5. Construct inputs
        inputs = []
        for u in selected_utxos:
            inputs.append({
                "txid": u["txid"],
                "vout": u["vout"],
                "sequence": 0xffffffff
            })

        # 6. Construct outputs with exact decimal string serialization (no binary float conversions)
        dest_btc_str = sats_to_btc_str(amount_satoshis)
        outputs = [{destination_address: dest_btc_str}]

        # Change output calculation
        change_sats = accumulated_sats - total_needed
        actual_fee_sats = nominal_fee

        if change_sats > DUST_LIMIT_SATOSHIS:
            change_btc_str = sats_to_btc_str(change_sats)
            outputs.append({multisig_address: change_btc_str})
        else:
            # Change is dust or zero; fold it into miner fee
            actual_fee_sats += change_sats
            change_sats = 0
            logger.info(f"Change output ({change_sats} sats) is below dust limit ({DUST_LIMIT_SATOSHIS} sats); folded into miner fee.")

        # 7. Create raw PSBT using Bitcoin Core
        unsigned_psbt = bitcoin_rpc.call("createpsbt", [inputs, outputs])

        # 8. Update PSBT with descriptor to populate witnessScript, redeemScript, and key origins
        try:
            descriptors = [descriptor] if descriptor else [f"addr({multisig_address})"]
            updated_psbt = bitcoin_rpc.call("utxoupdatepsbt", [unsigned_psbt, descriptors])
            unsigned_psbt = updated_psbt
        except BitcoinRPCException as e:
            logger.warning(f"utxoupdatepsbt note: {e.message}")

        # 9. Analyze initial PSBT and verify fee
        analysis = self.analyze_psbt(unsigned_psbt)
        verified_fee = analysis.get("fee")
        if verified_fee is not None:
            actual_fee_sats = int(round(Decimal(str(verified_fee)) * Decimal(100_000_000)))

        return {
            "psbt_base64": unsigned_psbt,
            "inputs_count": len(inputs),
            "outputs_count": len(outputs),
            "accumulated_sats": accumulated_sats,
            "amount_satoshis": amount_satoshis,
            "fee_satoshis": actual_fee_sats,
            "change_satoshis": change_sats,
            "analysis": analysis
        }

    def decode_psbt(self, psbt_base64: str) -> Dict[str, Any]:
        """Decodes PSBT to inspect human-readable inputs, outputs, scripts, and partial signatures."""
        return bitcoin_rpc.call("decodepsbt", [psbt_base64])

    def analyze_psbt(self, psbt_base64: str) -> Dict[str, Any]:
        """Analyzes PSBT to determine missing signatures, fee, estimated vsize, and completion status."""
        try:
            return bitcoin_rpc.call("analyzepsbt", [psbt_base64])
        except Exception as e:
            logger.warning(f"analyzepsbt error: {e}")
            return {"error": str(e), "is_final": False}

    def extract_partial_signatures(self, psbt_base64: str) -> List[Dict[str, str]]:
        """
        Extracts all partial signatures present in the PSBT inputs along with their public keys.
        Returns list of {'pubkey': '...', 'signature': '...'}
        """
        decoded = self.decode_psbt(psbt_base64)
        signatures = []
        for inp in decoded.get("inputs", []):
            partial_sigs = inp.get("partial_signatures", {})
            for pk, sig in partial_sigs.items():
                signatures.append({
                    "pubkey": pk.lower(),
                    "signature": sig
                })
        return signatures

    def verify_signer_signature_cryptographic(
        self,
        psbt_base64: str,
        expected_pubkey_hex: str
    ) -> Tuple[bool, str]:
        """
        Independently and cryptographically validates that the PSBT contains an authentic ECDSA DER signature
        matching the registered public key for all relevant inputs.
        Directly calculates the BIP-143 transaction signature hash and verifies the signature bytes.
        """
        norm_expected = expected_pubkey_hex.lower()
        try:
            decoded = self.decode_psbt(psbt_base64)
        except Exception as e:
            return False, f"Failed to decode PSBT: {str(e)}"

        inputs = decoded.get("inputs", [])
        if not inputs:
            return False, "PSBT contains no inputs"

        found_signature = False

        for idx, inp in enumerate(inputs):
            partial_sigs = inp.get("partial_signatures", {})
            matching_key = None
            for pk in partial_sigs.keys():
                if pk.lower() == norm_expected:
                    matching_key = pk
                    break

            if not matching_key:
                continue

            found_signature = True
            raw_sig_hex = partial_sigs[matching_key]

            # DER signature must have at least 16 hex chars (8 bytes) + sighash type byte (0x01)
            if len(raw_sig_hex) < 16:
                return False, f"Signature format too short in input {idx}"

            sig_der_hex = raw_sig_hex[:-2]
            sighash_type = int(raw_sig_hex[-2:], 16)
            if sighash_type != 1:  # SIGHASH_ALL
                return False, f"Unsupported sighash type 0x{sighash_type:02x} in input {idx} (expected SIGHASH_ALL 0x01)"

            try:
                sig_der_bytes = bytes.fromhex(sig_der_hex)
            except Exception:
                return False, f"Malformed DER hex string in input {idx}"

            # Compute BIP-143 sighash for this input
            try:
                sighash = compute_bip143_sighash_for_input(decoded, idx)
            except Exception as e:
                return False, f"Failed to compute BIP-143 sighash for input {idx}: {str(e)}"

            # Cryptographic ECDSA DER verification using secp256k1
            try:
                vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(norm_expected), curve=ecdsa.SECP256k1)
                vk.verify_digest(sig_der_bytes, sighash, sigdecode=ecdsa.util.sigdecode_der)
            except ecdsa.BadSignatureError:
                return False, f"Cryptographic ECDSA verification failed: signature does not match public key and sighash for input {idx}"
            except Exception as e:
                return False, f"Invalid signature format or decoding failure in input {idx}: {str(e)}"

        if not found_signature:
            return False, f"No partial signature found in PSBT matching registered public key {expected_pubkey_hex[:16]}..."

        return True, "Valid cryptographic signature verified against input sighash"

    def verify_signer_signature_present(
        self,
        psbt_base64: str,
        expected_pubkey_hex: str
    ) -> bool:
        """
        Cryptographically verifies that the PSBT contains a valid partial signature corresponding to the expected public key.
        """
        is_valid, _ = self.verify_signer_signature_cryptographic(psbt_base64, expected_pubkey_hex)
        return is_valid

    def combine_and_verify_signatures(
        self,
        current_psbt: str,
        submitted_signed_psbt: str,
        expected_pubkey_hex: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Combines incoming signer PSBT with master PSBT and verifies that new valid cryptographic
        signatures were provided.
        """
        # If expected pubkey is given, verify the submitted PSBT contains an authentic cryptographic signature
        if expected_pubkey_hex:
            is_valid, reason = self.verify_signer_signature_cryptographic(submitted_signed_psbt, expected_pubkey_hex)
            if not is_valid:
                raise ValueError(
                    f"Cryptographic signature verification failed: {reason}"
                )

        try:
            combined_psbt = bitcoin_rpc.call("combinepsbt", [[current_psbt, submitted_signed_psbt]])
            analysis = self.analyze_psbt(combined_psbt)
            return {
                "combined_psbt": combined_psbt,
                "analysis": analysis,
                "success": True
            }
        except BitcoinRPCException as e:
            logger.error(f"Failed to combine PSBT: {e.message}")
            raise ValueError(f"Bitcoin RPC combinepsbt failed: {e.message}")

    def finalize_and_broadcast(self, psbt_base64: str) -> Dict[str, Any]:
        """
        Finalizes a threshold-complete PSBT and broadcasts it to Bitcoin Core Regtest.
        """
        finalize_res = bitcoin_rpc.call("finalizepsbt", [psbt_base64, True])

        if not finalize_res.get("complete", False):
            raise ValueError(
                "PSBT cannot be finalized: Insufficient valid signatures collected to reach threshold"
            )

        hex_tx = finalize_res["hex"]

        # Broadcast transaction to the Bitcoin Regtest network
        txid = bitcoin_rpc.call("sendrawtransaction", [hex_tx])

        # Mine 1 block to confirm immediately on Regtest
        wallet_service.mine_blocks(1)

        return {
            "txid": txid,
            "hex": hex_tx,
            "broadcast": True,
            "confirmed": True
        }

psbt_service = PSBTService()
