import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("bitfortress.bitcoin.rpc")

class BitcoinRPCException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Bitcoin RPC Error [{code}]: {message}")

class BitcoinRPCClient:
    def __init__(
        self,
        host: str = settings.BITCOIN_RPC_HOST,
        port: int = settings.BITCOIN_RPC_PORT,
        user: str = settings.BITCOIN_RPC_USER,
        password: str = settings.BITCOIN_RPC_PASSWORD,
        wallet_name: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.wallet_name = wallet_name

    @property
    def url(self) -> str:
        if self.wallet_name:
            return f"http://{self.host}:{self.port}/wallet/{self.wallet_name}"
        return f"http://{self.host}:{self.port}/"

    def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        if params is None:
            params = []
        payload = {
            "jsonrpc": "2.0",
            "id": "bitfortress",
            "method": method,
            "params": params
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.url,
                    json=payload,
                    auth=(self.user, self.password),
                    headers={"Content-Type": "application/json"}
                )
                
            if response.status_code == 401:
                raise BitcoinRPCException(-1, "Unauthorized Bitcoin RPC credentials")
                
            res_data = response.json()
            if res_data.get("error") is not None:
                err = res_data["error"]
                raise BitcoinRPCException(err.get("code", -1), err.get("message", "Unknown RPC error"))
                
            return res_data.get("result")
        except httpx.ConnectError:
            raise BitcoinRPCException(-1001, f"Failed to connect to Bitcoin Core node at {self.host}:{self.port}")
        except json.JSONDecodeError:
            raise BitcoinRPCException(-1002, "Invalid JSON response from Bitcoin node")

    # High-level RPC methods
    def getblockchaininfo(self) -> Dict[str, Any]:
        return self.call("getblockchaininfo")

    def getnetworkinfo(self) -> Dict[str, Any]:
        return self.call("getnetworkinfo")

    def generatetoaddress(self, nblocks: int, address: str) -> List[str]:
        return self.call("generatetoaddress", [nblocks, address])

    def listwallets(self) -> List[str]:
        return self.call("listwallets")

    def createwallet(self, wallet_name: str, disable_private_keys: bool = False, blank: bool = False, descriptors: bool = True) -> Dict[str, Any]:
        try:
            return self.call("createwallet", [wallet_name, disable_private_keys, blank, "", False, descriptors])
        except BitcoinRPCException as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                try:
                    return self.call("loadwallet", [wallet_name])
                except Exception:
                    pass
            raise e

    def loadwallet(self, wallet_name: str) -> Dict[str, Any]:
        return self.call("loadwallet", [wallet_name])

    def getnewaddress(self, label: str = "", address_type: str = "bech32") -> str:
        return self.call("getnewaddress", [label, address_type])

    def sendtoaddress(self, address: str, amount_btc: float, comment: str = "") -> str:
        return self.call("sendtoaddress", [address, amount_btc, comment])

    def createmultisig(self, nrequired: int, keys: List[str], address_type: str = "p2sh-segwit") -> Dict[str, Any]:
        return self.call("createmultisig", [nrequired, keys, address_type])

    def decodepsbt(self, psbt_base64: str) -> Dict[str, Any]:
        return self.call("decodepsbt", [psbt_base64])

    def analyzepsbt(self, psbt_base64: str) -> Dict[str, Any]:
        return self.call("analyzepsbt", [psbt_base64])

    def combinepsbt(self, txs: List[str]) -> str:
        return self.call("combinepsbt", [txs])

    def finalizepsbt(self, psbt_base64: str, extract: bool = True) -> Dict[str, Any]:
        return self.call("finalizepsbt", [psbt_base64, extract])

    def sendrawtransaction(self, hexstring: str) -> str:
        return self.call("sendrawtransaction", [hexstring])

    def getrawtransaction(self, txid: str, verbose: bool = True) -> Any:
        return self.call("getrawtransaction", [txid, verbose])

    def scantxoutset(self, action: str, scanobjects: List[str]) -> Dict[str, Any]:
        return self.call("scantxoutset", [action, scanobjects])

# Shared client instance
bitcoin_rpc = BitcoinRPCClient()
