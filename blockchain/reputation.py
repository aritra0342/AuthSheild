import json
import hashlib
from datetime import datetime
from typing import Optional
from .algorand_client import algorand_client
from algosdk import transaction

class ReputationManager:
    def __init__(self):
        self.client = algorand_client
        self.reputation_asset_id = None
    
    def create_reputation_token(self) -> dict:
        if not self.client.is_configured():
            return {"success": False, "error": "Algorand not configured"}
        
        try:
            result = self.client.create_asset(
                name="AuthShield Reputation",
                unit="REP",
                total=1000000,
                decimals=2,
                url="https://authshield.ai/reputation"
            )
            
            if result.get("success"):
                self.reputation_asset_id = result.get("confirmed-round")
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_reputation(self, user_id: str, wallet_address: str,
                          risk_score: float, trust_score: float) -> dict:
        if not self.client.is_configured():
            return {
                "success": False,
                "error": "Algorand not configured",
                "updated": False
            }
        
        try:
            rep_data = {
                "type": "REPUTATION_UPDATE",
                "user_id": user_id,
                "risk_score": risk_score,
                "trust_score": trust_score,
                "timestamp": datetime.utcnow().isoformat(),
                "system": "AuthShield AI"
            }
            
            note = json.dumps(rep_data).encode()
            
            params = self.client.client.suggested_params()
            
            txn = transaction.PaymentTxn(
                sender=self.client.address,
                sp=params,
                receiver=self.client.address,
                amt=0,
                note=note
            )
            
            result = self.client.send_transaction(txn)
            
            if result.get("success"):
                return {
                    "success": True,
                    "updated": True,
                    "txid": result["txid"],
                    "explorer_link": self.client.get_transaction_link(result["txid"]),
                    "risk_score": risk_score,
                    "trust_score": trust_score,
                    "network": result.get("network")
                }
            else:
                return {
                    "success": False,
                    "updated": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "updated": False,
                "error": str(e)
            }
    
    def get_reputation_history(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "message": "Query indexer for transaction history with user_id in note field",
            "indexer_query": f"/v2/transactions?note-prefix={user_id}"
        }
    
    def calculate_trust_score(self, risk_score: float) -> float:
        trust_score = 100 - (risk_score * 50)
        return max(0, min(100, trust_score))


reputation_manager = ReputationManager()
