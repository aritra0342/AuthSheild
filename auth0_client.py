import httpx
import time
from typing import Optional, Dict
from config import config

_token_cache = {"token": None, "expires_at": 0}

async def get_auth0_token() -> str:
    if _token_cache["token"] and _token_cache["expires_at"] > time.time() + 60:
        return _token_cache["token"]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{config.AUTH0_DOMAIN}/oauth/token",
            json={
                "client_id": config.AUTH0_CLIENT_ID,
                "client_secret": config.AUTH0_CLIENT_SECRET,
                "audience": config.AUTH0_AUDIENCE,
                "grant_type": "client_credentials"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Auth0 token error: {response.text}")
        
        data = response.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 86400)
        
        return _token_cache["token"]

async def freeze_user(user_id: str, reason: str = "cluster_flagged") -> Dict:
    token = await get_auth0_token()
    
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                response = await client.patch(
                    f"https://{config.AUTH0_DOMAIN}/api/v2/users/{user_id}",
                    json={
                        "blocked": True,
                        "app_metadata": {
                            "risk_level": "critical",
                            "cluster_flagged": True,
                            "freeze_reason": reason
                        }
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "user_id": user_id}
                elif response.status_code == 401:
                    _token_cache["token"] = None
                    token = await get_auth0_token()
                    continue
                else:
                    return {"success": False, "error": response.text, "status": response.status_code}
                    
            except httpx.RequestError as e:
                if attempt == 2:
                    return {"success": False, "error": str(e)}
                time.sleep(2 ** attempt)
        
        return {"success": False, "error": "Max retries exceeded"}

async def unfreeze_user(user_id: str) -> Dict:
    token = await get_auth0_token()
    
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                response = await client.patch(
                    f"https://{config.AUTH0_DOMAIN}/api/v2/users/{user_id}",
                    json={
                        "blocked": False,
                        "app_metadata": {
                            "risk_level": "low",
                            "cluster_flagged": False
                        }
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "user_id": user_id}
                elif response.status_code == 401:
                    _token_cache["token"] = None
                    token = await get_auth0_token()
                    continue
                else:
                    return {"success": False, "error": response.text, "status": response.status_code}
                    
            except httpx.RequestError as e:
                if attempt == 2:
                    return {"success": False, "error": str(e)}
                time.sleep(2 ** attempt)
        
        return {"success": False, "error": "Max retries exceeded"}

async def get_user(user_id: str) -> Optional[Dict]:
    token = await get_auth0_token()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{config.AUTH0_DOMAIN}/api/v2/users/{user_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        return None

async def get_all_users() -> list:
    token = await get_auth0_token()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{config.AUTH0_DOMAIN}/api/v2/users",
            params={"per_page": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("users", [])
        return []
