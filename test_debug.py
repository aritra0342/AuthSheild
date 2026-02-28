print("Step 1")
import fingerprint
print("Step 2")
fp = fingerprint.generate_fingerprint({'user_id': 'test', 'ip_address': '1.1.1.1', 'user_agent': 'test'})
print("Step 3")
print("Result:", fp.get('behavior_hash', '')[:10] if fp.get('behavior_hash') else 'None')
