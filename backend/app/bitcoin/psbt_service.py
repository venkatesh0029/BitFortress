import logging
import base64
from typing import Dict, Any, List, Optional, Tuple
from app.bitcoin.rpc_client import bitcoin_rpc, BitcoinRPCException
from app.bitcoin.wallet_service import wallet_service

logger = logging.getLogger("satoshiguard.bitcoin.psbt")

class PSBTService:
    def create_multisig_psbt(
        self,
        multisig_address: str,
        redeem_script: str,
        destination_address: str,
        amount_satoshis: int,
        fee_satoshis: int = 1000
    ) -> Dict[str, Any]:
        """
        Builds a Partially Signed Bitcoin Transaction (PSBT) for spending from a multisig address.
        """
        # 1. Fetch unspent UTXOs for the multisig address
        total_balance, utxos = wallet_service.get_address_balance_satoshis(multisig_address)
        total_needed = amount_satoshis + fee_satoshis

        if total_balance < total_needed:
            raise ValueError(
                f"Insufficient funds in treasury: balance is {total_balance} sats, but {total_needed} sats needed (including {fee_satoshis} sats fee)"
            )

        # 2. Select UTXOs to cover total_needed
        selected_utxos = []
        accumulated_sats = 0
        for utxo in utxos:
            selected_utxos.append(utxo)
            accumulated_sats += utxo["amount_satoshis"]
            if accumulated_sats >= total_needed:
                break

        # 3. Construct inputs
        inputs = []
        for u in selected_utxos:
            inputs.append({
                "txid": u["txid"],
                "vout": u["vout"],
                "sequence": 0xffffffff
            })

        # 4. Construct outputs (amount in BTC as float with 8 decimals)
        destination_btc = round(amount_satoshis / 100_000_000, 8)
        outputs = [{destination_address: destination_btc}]

        # Change output back to treasury multisig address if above dust (546 sats)
        change_sats = accumulated_sats - total_needed
        if change_sats > 546:
            change_btc = round(change_sats / 100_000_000, 8)
            outputs.append({multisig_address: change_btc})

        # 5. Create raw PSBT
        unsigned_psbt = bitcoin_rpc.call("createpsbt", [inputs, outputs])

        # 6. Populate witness script / redeem script in the PSBT inputs
        # We use decodepsbt and wallet/descriptor helpers or utxoedit
        # In Bitcoin Core, utxoupdatepsbt or descriptor wallets update this.
        # We can also call utxoupdatepsbt to update witness scripts from descriptors if available
        try:
            # Try updating utxos in PSBT
            updated = bitcoin_rpc.call("utxoupdatepsbt", [unsigned_psbt, [f"addr({multisig_address})"]])
            unsigned_psbt = updated
        except Exception:
            pass

        # 7. Analyze initial PSBT
        analysis = self.analyze_psbt(unsigned_psbt)

        return {
            "psbt_base64": unsigned_psbt,
            "inputs_count": len(inputs),
            "outputs_count": len(outputs),
            "accumulated_sats": accumulated_sats,
            "amount_satoshis": amount_satoshis,
            "fee_satoshis": fee_satoshis,
            "change_satoshis": change_sats,
            "analysis": analysis
        }

    def decode_psbt(self, psbt_base64: str) -> Dict[str, Any]:
        """Decodes PSBT to inspect human-readable inputs, outputs, scripts."""
        return bitcoin_rpc.decodepsbt(psbt_base64)

    def analyze_psbt(self, psbt_base64: str) -> Dict[str, Any]:
        """Analyzes PSBT to determine missing signatures, fee, estimated vsize, completeness."""
        try:
            return bitcoin_rpc.analyzepsbt(psbt_base64)
        except Exception as e:
            logger.warning(f"analyzepsbt error: {e}")
            return {"error": str(e), "is_final": False}

    def combine_and_verify_signatures(
        self,
        current_psbt: str,
        submitted_signed_psbt: str
    ) -> Dict[str, Any]:
        """
        Combines incoming signer PSBT with existing PSBT and verifies signature count.
        """
        try:
            combined_psbt = bitcoin_rpc.combinepsbt([current_psbt, submitted_signed_psbt])
            analysis = self.analyze_psbt(combined_psbt)
            return {
                "combined_psbt": combined_psbt,
                "analysis": analysis,
                "success": True
            }
        except BitcoinRPCException as e:
            logger.error(f"Failed to combine PSBT: {e}")
            raise ValueError(f"Invalid signed PSBT: {e.message}")

    def finalize_and_broadcast(self, psbt_base64: str) -> Dict[str, Any]:
        """
        Finalizes a threshold-complete PSBT and broadcasts it to Bitcoin Core Regtest.
        """
        finalize_res = bitcoin_rpc.finalizepsbt(psbt_base64, True)
        
        if not finalize_res.get("complete", False):
            raise ValueError(
                "PSBT cannot be finalized: Insufficient valid signatures collected to reach threshold"
            )

        hex_tx = finalize_res["hex"]
        
        # Broadcast transaction to the Bitcoin Regtest network
        txid = bitcoin_rpc.sendrawtransaction(hex_tx)
        
        # Mine 1 block to confirm immediately on Regtest
        wallet_service.mine_blocks(1)
        
        return {
            "txid": txid,
            "hex": hex_tx,
            "broadcast": True,
            "confirmed": True
        }

psbt_service = PSBTService()
