import traceback
import sys

try:
    print("Starting test...", flush=True)
    
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    print("FastAPI imported", flush=True)
    
    import main
    print("Main imported", flush=True)
    
    client = TestClient(main.app)
    print("TestClient created", flush=True)
    
    response = client.post('/api/simulate', json={
        'user_id': 'test123',
        'ip_address': '192.168.1.1',
        'user_agent': 'Chrome',
        'webgl_hash': 'abc',
        'canvas_hash': 'def'
    })
    
    print(f"Status: {response.status_code}", flush=True)
    print(f"Response: {response.text[:500]}", flush=True)
    
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    traceback.print_exc()
