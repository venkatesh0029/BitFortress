import logging
from typing import Dict, Any, List, Tuple
from app.bitcoin.rpc_client import BitcoinRPCClient, bitcoin_rpc, BitcoinRPCException

logger = logging.getLogger("bitfortress.bitcoin.wallet")

MINER_WALLET_NAME = "sg_miner_funder"

class BitcoinWalletService:
    def __init__(self):
        self.miner_rpc = BitcoinRPCClient(wallet_name=MINER_WALLET_NAME)

    def ensure_miner_wallet_ready(self) -> str:
        """Ensures a funding/miner wallet exists and has mature coinbase funds in regtest."""
        wallets = bitcoin_rpc.listwallets()
        if MINER_WALLET_NAME not in wallets:
            try:
                bitcoin_rpc.createwallet(MINER_WALLET_NAME)
                logger.info(f"Created miner wallet '{MINER_WALLET_NAME}'")
            except BitcoinRPCException:
                try:
                    bitcoin_rpc.loadwallet(MINER_WALLET_NAME)
                except Exception:
                    pass

        # Check block height
        info = bitcoin_rpc.getblockchaininfo()
        blocks = info.get("blocks", 0)
        
        # Mine initial 101 blocks if network is fresh so coinbase matures (100 block maturity rule)
        miner_addr = self.miner_rpc.getnewaddress("miner_reward", "bech32")
        if blocks < 101:
            needed = 101 - blocks
            logger.info(f"Mining {needed} initial regtest blocks to mature coinbase rewards...")
            bitcoin_rpc.generatetoaddress(needed, miner_addr)
            
        return miner_addr

    def create_multisig_config(self, threshold: int, public_keys: List[str]) -> Dict[str, Any]:
        """
        Creates an M-of-N multisig address via Bitcoin Core.
        Uses p2sh-segwit (P2WSH wrapped in P2SH) or native segwit (P2WSH) for maximal compatibility.
        """
        if threshold < 1 or threshold > len(public_keys):
            raise ValueError(f"Threshold must be between 1 and {len(public_keys)}")
            
        # createmultisig returns address, redeemScript, and descriptor
        res = bitcoin_rpc.createmultisig(threshold, public_keys, "p2sh-segwit")
        
        address = res["address"]
        redeem_script = res.get("redeemScript", "")
        descriptor = res.get("descriptor", "")
        
        return {
            "address": address,
            "redeem_script": redeem_script,
            "descriptor": descriptor,
            "threshold": threshold,
            "total_signers": len(public_keys)
        }

    def fund_address(self, destination_address: str, amount_btc: float = 5.0) -> Dict[str, Any]:
        """Funds an address from the local miner wallet and mines a block to confirm it."""
        self.ensure_miner_wallet_ready()
        
        # Send funds
        txid = self.miner_rpc.sendtoaddress(destination_address, amount_btc, "Treasury Initial Funding")
        
        # Mine 1 block to confirm immediately
        miner_addr = self.miner_rpc.getnewaddress("confirm_block", "bech32")
        bitcoin_rpc.generatetoaddress(1, miner_addr)
        
        return {
            "txid": txid,
            "amount_btc": amount_btc,
            "amount_satoshis": int(amount_btc * 100_000_000),
            "destination": destination_address,
            "confirmed": True
        }

    def get_address_balance_satoshis(self, address: str) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Uses scantxoutset to query all active UTXOs for an address without needing watch-only wallet sync.
        """
        try:
            scan_res = bitcoin_rpc.scantxoutset("start", [f"addr({address})"])
            total_btc = scan_res.get("total_amount", 0.0)
            total_satoshis = int(round(total_btc * 100_000_000))
            
            utxos = []
            for unspent in scan_res.get("unspents", []):
                utxos.append({
                    "txid": unspent["txid"],
                    "vout": unspent["vout"],
                    "scriptPubKey": unspent["scriptPubKey"],
                    "amount_btc": unspent["amount"],
                    "amount_satoshis": int(round(unspent["amount"] * 100_000_000)),
                    "height": unspent.get("height", 0)
                })
            return total_satoshis, utxos
        except Exception as e:
            logger.warning(f"scantxoutset error for {address}: {e}")
            return 0, []

    def mine_blocks(self, nblocks: int = 1) -> List[str]:
        """Mines n blocks to the local miner address."""
        self.ensure_miner_wallet_ready()
        miner_addr = self.miner_rpc.getnewaddress("regtest_mine", "bech32")
        block_hashes = bitcoin_rpc.generatetoaddress(nblocks, miner_addr)
        return block_hashes

wallet_service = BitcoinWalletService()
