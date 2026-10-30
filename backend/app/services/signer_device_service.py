import logging
from typing import Dict, Any, Optional
from app.bitcoin.rpc_client import BitcoinRPCClient, bitcoin_rpc, BitcoinRPCException

logger = logging.getLogger("bitfortress.signer.device")

class SignerDeviceService:
    """
    Manages isolated custodian signing devices (HSMs / Hardware Wallets).
    In Bitcoin Regtest development, each custodian's private key is stored exclusively
    in an isolated, dedicated Bitcoin Core wallet (sg_custodian_{signer_id}) that represents
    an independent hardware signing device. The treasury coordinator/server never accesses
    these private keys directly and strictly consumes BIP-174 signed PSBTs.
    """

    def get_custodian_wallet_name(self, signer_id: int) -> str:
        return f"sg_custodian_{signer_id}"

    def ensure_custodian_wallet(self, signer_id: int) -> BitcoinRPCClient:
        wallet_name = self.get_custodian_wallet_name(signer_id)
        wallets = bitcoin_rpc.call("listwallets")
        if wallet_name not in wallets:
            try:
                bitcoin_rpc.call("createwallet", [wallet_name, False, False, "", False, True])
                logger.info(f"Initialized isolated custodian signing device wallet '{wallet_name}'")
            except BitcoinRPCException:
                try:
                    bitcoin_rpc.call("loadwallet", [wallet_name])
                except Exception as e:
                    logger.warning(f"Note on loading custodian wallet '{wallet_name}': {e}")
        return BitcoinRPCClient(wallet_name=wallet_name)

    def get_device_public_key(self, signer_id: int) -> str:
        """Retrieves the stable secp256k1 compressed public key for this custodian device."""
        rpc = self.ensure_custodian_wallet(signer_id)
        try:
            labels = rpc.call("getaddressesbylabel", ["custodian_master"])
            addr = list(labels.keys())[0]
        except BitcoinRPCException:
            addr = rpc.call("getnewaddress", ["custodian_master", "bech32"])

        info = rpc.call("getaddressinfo", [addr])
        pubkey = info.get("pubkey")
        if not pubkey:
            raise ValueError(f"Could not retrieve public key from custodian device #{signer_id}")
        return pubkey

    def sign_psbt_with_device(self, signer_id: int, psbt_base64: str) -> Dict[str, Any]:
        """
        Executes cryptographic signing on the isolated custodian device for a given PSBT.
        Returns the partially signed PSBT containing the custodian's ECDSA DER signature.
        """
        rpc = self.ensure_custodian_wallet(signer_id)
        try:
            sign_res = rpc.call("walletprocesspsbt", [psbt_base64])
            signed_psbt = sign_res.get("psbt")
            is_complete = sign_res.get("complete", False)
            if not signed_psbt:
                raise ValueError("Custodian device failed to produce a signed PSBT")

            return {
                "signed_psbt": signed_psbt,
                "complete": is_complete,
                "signer_id": signer_id
            }
        except BitcoinRPCException as e:
            logger.error(f"Custodian device #{signer_id} signing error: {e.message}")
            raise ValueError(f"Hardware signer #{signer_id} rejected PSBT: {e.message}")

signer_device_service = SignerDeviceService()
