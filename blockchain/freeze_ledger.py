import json
import hashlib
from datetime import datetime
from typing import Optional
from .algorand_client import algorand_client
from algosdk import transaction, encoding

class FreezeLedger:
    def __init__(self):
        self.client = algorand_client
    
    def log_freeze(self, user_id: str, risk_score: float, cluster_id: str = None,
                   reason: str = "auto_freeze") -> dict:
        if not self.client.is_configured():
            return {
                "success": False,
                "error": "Algorand not configured",
                "blockchain_logged": False
            }
        
        try:
            note_data = {
                "type": "FREEZE",
                "user_id": user_id,
                "risk_score": risk_score,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            note = json.dumps(note_data).encode()
            
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
                    "blockchain_logged": True,
                    "txid": result["txid"],
                    "explorer_link": self.client.get_transaction_link(result["txid"]),
                    "confirmed_round": result.get("confirmed_round"),
                    "network": result.get("network")
                }
            else:
                return {
                    "success": False,
                    "blockchain_logged": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "blockchain_logged": False,
                "error": str(e)
            }
    
    def log_unfreeze(self, user_id: str, admin_id: str = None, reason: str = "manual_unfreeze") -> dict:
        if not self.client.is_configured():
            return {
                "success": False,
                "error": "Algorand not configured",
                "blockchain_logged": False
            }
        
        try:
            note_data = {
                "type": "UNFREEZE",
                "user_id": user_id,
                "admin_id": admin_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "system": "AuthShield AI"
            }
            
            note = json.dumps(note_data).encode()
            
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
                    "blockchain_logged": True,
                    "txid": result["txid"],
                    "explorer_link": self.client.get_transaction_link(result["txid"]),
                    "confirmed_round": result.get("confirmed_round"),
                    "network": result.get("network")
                }
            else:
                return {
                    "success": False,
                    "blockchain_logged": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "blockchain_logged": False,
                "error": str(e)
            }
    
    def log_cluster_detection(self, cluster_size: int, flagged_count: int,
                              avg_risk_score: float) -> dict:
        if not self.client.is_configured():
            return {
                "success": False,
                "error": "Algorand not configured",
                "blockchain_logged": False
            }
        
        try:
            note_data = {
                "type": "CLUSTER_DETECTION",
                "cluster_size": cluster_size,
                "flagged_count": flagged_count,
                "avg_risk_score": avg_risk_score,
                "timestamp": datetime.utcnow().isoformat(),
                "system": "AuthShield AI"
            }
            
            note = json.dumps(note_data).encode()
            
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
                    "blockchain_logged": True,
                    "txid": result["txid"],
                    "explorer_link": self.client.get_transaction_link(result["txid"])
                }
            else:
                return {
                    "success": False,
                    "blockchain_logged": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "blockchain_logged": False,
                "error": str(e)
            }


freeze_ledger = FreezeLedger()
