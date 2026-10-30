from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from app.bitcoin.rpc_client import bitcoin_rpc
from app.bitcoin.wallet_service import wallet_service
from app.schemas.schemas import MineRequest

router = APIRouter(prefix="/node", tags=["Bitcoin Node"])

@router.get("/info")
def get_node_info() -> Dict[str, Any]:
    try:
        chain_info = bitcoin_rpc.getblockchaininfo()
        net_info = bitcoin_rpc.getnetworkinfo()
        return {
            "status": "ONLINE",
            "chain": chain_info.get("chain", "regtest"),
            "blocks": chain_info.get("blocks", 0),
            "headers": chain_info.get("headers", 0),
            "bestblockhash": chain_info.get("bestblockhash"),
            "difficulty": chain_info.get("difficulty"),
            "subversion": net_info.get("subversion", "Bitcoin Core v28.0"),
            "connections": net_info.get("connections", 0),
            "protocolversion": net_info.get("protocolversion")
        }
    except Exception as e:
        return {
            "status": "OFFLINE_OR_ERROR",
            "error": str(e)
        }

@router.post("/mine")
def mine_blocks(req: MineRequest) -> Dict[str, Any]:
    try:
        blocks = wallet_service.mine_blocks(req.blocks)
        info = bitcoin_rpc.getblockchaininfo()
        return {
            "mined_blocks": len(blocks),
            "new_height": info.get("blocks"),
            "bestblockhash": info.get("bestblockhash")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
