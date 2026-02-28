import json
import hashlib
from datetime import datetime
from typing import Optional
from .algorand_client import algorand_client
from algosdk import transaction

class NFTBadge:
    def __init__(self):
        self.client = algorand_client
        self.badge_asset_id = None
    
    def create_badge_collection(self) -> dict:
        if not self.client.is_configured():
            return {"success": False, "error": "Algorand not configured"}
        
        try:
            metadata = {
                "name": "AuthShield Verified User",
                "description": "NFT Badge for verified secure users",
                "standard": "ARC69",
                "properties": {
                    "system": "AuthShield AI",
                    "type": "security_verification",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            result = self.client.create_asset(
                name="AuthShield Verified Badge",
                unit="ASHIELD",
                total=10000,
                decimals=0,
                url="ipfs://QmExample",
                metadata_hash=hashlib.sha256(json.dumps(metadata).encode()).digest()
            )
            
            if result.get("success"):
                self.badge_asset_id = result.get("confirmed-round")
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mint_badge(self, user_id: str, wallet_address: str, risk_score: float,
                   user_agent: str = "") -> dict:
        if not self.client.is_configured():
            return {
                "success": False,
                "error": "Algorand not configured",
                "minted": False
            }
        
        if risk_score > 0.3:
            return {
                "success": False,
                "error": "User risk score too high for badge",
                "minted": False,
                "risk_score": risk_score
            }
        
        try:
            metadata = {
                "name": f"AuthShield Badge - {user_id}",
                "description": "Verified secure user on AuthShield AI",
                "standard": "ARC69",
                "properties": {
                    "user_id": user_id,
                    "risk_score": risk_score,
                    "verification_date": datetime.utcnow().isoformat(),
                    "system": "AuthShield AI"
                }
            }
            
            note = json.dumps(metadata).encode()
            
            result = self.client.create_asset(
                name=f"Verified: {user_id[:20]}",
                unit="VBADGE",
                total=1,
                decimals=0,
                url="ipfs://QmVerifiedBadge"
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "minted": False
                }
            
            return {
                "success": True,
                "minted": True,
                "txid": result["txid"],
                "explorer_link": self.client.get_transaction_link(result["txid"]),
                "asset_name": f"Verified: {user_id[:20]}",
                "metadata": metadata,
                "network": result.get("network")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "minted": False
            }
    
    def verify_badge(self, asset_id: int) -> dict:
        if not self.client.is_configured():
            return {"verified": False, "error": "Algorand not configured"}
        
        try:
            asset_info = self.client.get_asset_info(asset_id)
            
            if "error" in asset_info:
                return {"verified": False, "error": asset_info["error"]}
            
            params = asset_info.get("params", {})
            
            is_verified = (
                params.get("unit-name") == "VBADGE" or
                "Verified" in params.get("name", "")
            )
            
            return {
                "verified": is_verified,
                "asset_id": asset_id,
                "name": params.get("name"),
                "creator": params.get("creator"),
                "total": params.get("total")
            }
            
        except Exception as e:
            return {"verified": False, "error": str(e)}


nft_badge = NFTBadge()
