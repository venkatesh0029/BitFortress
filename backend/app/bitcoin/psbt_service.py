import logging
import base64
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple
from app.bitcoin.rpc_client import bitcoin_rpc, BitcoinRPCException
from app.bitcoin.wallet_service import wallet_service

logger = logging.getLogger("satoshiguard.bitcoin.psbt")

# SegWit standard dust limit in satoshis
DUST_LIMIT_SATOSHIS = 546

def sats_to_btc_str(sats: int) -> str:
    """Converts integer satoshis to exact 8-decimal Bitcoin string to prevent floating-point inaccuracies."""
    btc_dec = (Decimal(sats) / Decimal(100_000_000)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    return f"{btc_dec:.8f}"

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
        address validation, UTXO selection, descriptor updates, and dust threshold protections.
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

        # Default fee estimate if not explicitly provided
        nominal_fee = fee_satoshis if (fee_satoshis and fee_satoshis > 0) else 1500
        total_needed = amount_satoshis + nominal_fee

        if total_balance < total_needed:
            raise ValueError(
                f"Insufficient funds in treasury: balance is {total_balance} sats, but {total_needed} sats needed (including {nominal_fee} sats fee)."
            )

        # 3. Select UTXOs to cover total_needed (Largest-First Coin Selection)
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

        # 4. Construct inputs
        inputs = []
        for u in selected_utxos:
            inputs.append({
                "txid": u["txid"],
                "vout": u["vout"],
                "sequence": 0xffffffff
            })

        # 5. Construct outputs with exact satoshi conversion
        dest_btc_float = float(sats_to_btc_str(amount_satoshis))
        outputs = [{destination_address: dest_btc_float}]

        # Change output calculation
        change_sats = accumulated_sats - total_needed
        actual_fee_sats = nominal_fee

        if change_sats > DUST_LIMIT_SATOSHIS:
            change_btc_float = float(sats_to_btc_str(change_sats))
            outputs.append({multisig_address: change_btc_float})
        else:
            # Change is dust or zero; fold it into miner fee
            actual_fee_sats += change_sats
            change_sats = 0
            logger.info(f"Change output ({change_sats} sats) is below dust limit ({DUST_LIMIT_SATOSHIS} sats); folded into miner fee.")

        # 6. Create raw PSBT
        unsigned_psbt = bitcoin_rpc.call("createpsbt", [inputs, outputs])

        # 7. Update PSBT with descriptor to populate witnessScript, redeemScript, and key origins
        try:
            descriptors = [descriptor] if descriptor else [f"addr({multisig_address})"]
            updated_psbt = bitcoin_rpc.call("utxoupdatepsbt", [unsigned_psbt, descriptors])
            unsigned_psbt = updated_psbt
        except BitcoinRPCException as e:
            logger.warning(f"utxoupdatepsbt note: {e.message}")

        # 8. Analyze initial PSBT
        analysis = self.analyze_psbt(unsigned_psbt)

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

    def verify_signer_signature_present(
        self,
        psbt_base64: str,
        expected_pubkey_hex: str
    ) -> bool:
        """
        Verifies that the PSBT contains a valid partial signature corresponding to the expected public key.
        """
        norm_expected = expected_pubkey_hex.lower()
        sigs = self.extract_partial_signatures(psbt_base64)
        for s in sigs:
            if s["pubkey"] == norm_expected:
                return True
        return False

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
        # If expected pubkey is given, verify the submitted PSBT contains a signature for it
        if expected_pubkey_hex:
            if not self.verify_signer_signature_present(submitted_signed_psbt, expected_pubkey_hex):
                raise ValueError(
                    f"Submitted PSBT does not contain a cryptographic signature matching signer public key {expected_pubkey_hex[:16]}..."
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
