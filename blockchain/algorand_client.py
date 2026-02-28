import os
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
from config import config

class AlgorandClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.network = os.getenv("ALGORAND_NETWORK", "testnet")
        
        if self.network == "testnet":
            self.algod_url = os.getenv("ALGORAND_NODE", "https://testnet-api.algonode.cloud")
            self.indexer_url = os.getenv("ALGORAND_INDEXER", "https://testnet-idx.algonode.cloud")
        elif self.network == "mainnet":
            self.algod_url = os.getenv("ALGORAND_NODE", "https://mainnet-api.algonode.cloud")
            self.indexer_url = os.getenv("ALGORAND_INDEXER", "https://mainnet-idx.algonode.cloud")
        else:
            self.algod_url = os.getenv("ALGORAND_NODE", "http://localhost:4001")
            self.indexer_url = os.getenv("ALGORAND_INDEXER", "http://localhost:8980")
        
        self.client = algod.AlgodClient("", self.algod_url)
        
        mnemonic_str = os.getenv("ALGORAND_MNEMONIC", "")
        if mnemonic_str:
            self.private_key = mnemonic.to_private_key(mnemonic_str)
            self.address = account.address_from_private_key(self.private_key)
        else:
            self.private_key = None
            self.address = None
        
        self._initialized = True
    
    def is_configured(self) -> bool:
        return self.private_key is not None and self.address is not None
    
    def get_account_info(self) -> dict:
        if not self.address:
            return {"error": "No account configured"}
        try:
            return self.client.account_info(self.address)
        except Exception as e:
            return {"error": str(e)}
    
    def get_balance(self) -> int:
        info = self.get_account_info()
        return info.get("amount", 0) if "error" not in info else 0
    
    def wait_for_confirmation(self, txid: str, timeout: int = 10) -> dict:
        try:
            status = self.client.status()
            last_round = status.get("last-round")
            current_round = last_round + 1
            
            for _ in range(timeout):
                try:
                    pending = self.client.pending_transaction_info(txid)
                    if pending.get("confirmed-round", 0) > 0:
                        return pending
                    if pending.get("pool-error", ""):
                        return {"error": pending["pool-error"]}
                except:
                    pass
                
                self.client.status_after_block(current_round)
                current_round += 1
            
            return {"error": "Timeout waiting for confirmation"}
        except Exception as e:
            return {"error": str(e)}
    
    def send_transaction(self, txn) -> dict:
        if not self.is_configured():
            return {"error": "Algorand not configured. Set ALGORAND_MNEMONIC in .env"}
        
        try:
            signed_txn = txn.sign(self.private_key)
            txid = self.client.send_transaction(signed_txn)
            
            result = self.wait_for_confirmation(txid)
            
            if "error" in result:
                return {"success": False, "error": result["error"], "txid": txid}
            
            return {
                "success": True,
                "txid": txid,
                "confirmed_round": result.get("confirmed-round"),
                "network": self.network
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_asset(self, name: str, unit: str, total: int, decimals: int = 0, 
                     metadata_hash: bytes = None, url: str = "") -> dict:
        if not self.is_configured():
            return {"error": "Algorand not configured"}
        
        try:
            params = self.client.suggested_params()
            
            txn = transaction.AssetConfigTxn(
                sender=self.address,
                sp=params,
                total=total,
                default_frozen=False,
                unit_name=unit,
                asset_name=name,
                manager=self.address,
                reserve=self.address,
                freeze=self.address,
                clawback=self.address,
                url=url,
                metadata_hash=metadata_hash,
                decimals=decimals
            )
            
            return self.send_transaction(txn)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def opt_in_asset(self, asset_id: int) -> dict:
        if not self.is_configured():
            return {"error": "Algorand not configured"}
        
        try:
            params = self.client.suggested_params()
            
            txn = transaction.AssetOptInTxn(
                sender=self.address,
                sp=params,
                index=asset_id
            )
            
            return self.send_transaction(txn)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def transfer_asset(self, asset_id: int, receiver: str, amount: int) -> dict:
        if not self.is_configured():
            return {"error": "Algorand not configured"}
        
        try:
            params = self.client.suggested_params()
            
            txn = transaction.AssetTransferTxn(
                sender=self.address,
                sp=params,
                receiver=receiver,
                amt=amount,
                index=asset_id
            )
            
            return self.send_transaction(txn)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_asset_info(self, asset_id: int) -> dict:
        try:
            return self.client.asset_info(asset_id)
        except Exception as e:
            return {"error": str(e)}
    
    def get_transaction_link(self, txid: str) -> str:
        if self.network == "testnet":
            return f"https://testnet.algoexplorer.io/tx/{txid}"
        elif self.network == "mainnet":
            return f"https://algoexplorer.io/tx/{txid}"
        else:
            return f"Local network - TXID: {txid}"


def generate_testnet_account() -> dict:
    private_key, address = account.generate_account()
    mnemonic_str = mnemonic.from_private_key(private_key)
    
    return {
        "address": address,
        "private_key": private_key,
        "mnemonic": mnemonic_str,
        "fund_url": f"https://bank.testnet.algorand.network/?account={address}"
    }


algorand_client = AlgorandClient()
