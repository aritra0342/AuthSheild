import hashlib
import numpy as np
from typing import List, Dict
from datetime import datetime

def normalize_ip(ip_address: str) -> List[float]:
    octets = ip_address.split(".")
    if len(octets) != 4:
        octets = ["0", "0", "0", "0"]
    return [int(o) / 255.0 for o in octets]

def normalize_user_agent(user_agent: str) -> List[float]:
    features = [0.0] * 5
    ua_lower = user_agent.lower()
    features[0] = 1.0 if "chrome" in ua_lower else 0.0
    features[1] = 1.0 if "firefox" in ua_lower else 0.0
    features[2] = 1.0 if "safari" in ua_lower else 0.0
    features[3] = 1.0 if "mobile" in ua_lower or "android" in ua_lower else 0.0
    features[4] = 1.0 if "bot" in ua_lower or "crawler" in ua_lower else 0.0
    return features

def normalize_screen(resolution: str) -> List[float]:
    try:
        w, h = map(int, resolution.lower().split("x"))
        aspect_ratio = w / h if h > 0 else 1.0
        normalized_w = min(w / 3840.0, 1.0)
        normalized_h = min(h / 2160.0, 1.0)
        return [normalized_w, normalized_h, aspect_ratio]
    except:
        return [0.5, 0.5, 1.0]

def normalize_timezone(timezone: str) -> float:
    try:
        offset = int(timezone.replace("UTC", "").replace("+", ""))
        return (offset + 12) / 24.0
    except:
        return 0.5

def normalize_typing_latency(latency_array: List[float]) -> List[float]:
    if not latency_array:
        return [0.0, 0.0, 0.0]
    arr = np.array(latency_array)
    mean_latency = float(np.mean(arr) / 500.0)
    std_latency = float(np.std(arr) / 200.0)
    range_latency = float((np.max(arr) - np.min(arr)) / 1000.0) if len(arr) > 1 else 0.0
    return [float(min(mean_latency, 1.0)), float(min(std_latency, 1.0)), float(min(range_latency, 1.0))]

def calculate_ip_entropy(ip_address: str) -> float:
    octets = ip_address.split(".")
    entropy = 0.0
    for o in octets:
        try:
            val = int(o)
            if val > 0:
                p = val / 255.0
                if p > 0:
                    entropy -= p * np.log2(p)
        except:
            pass
    return float(min(entropy / 8.0, 1.0))

def calculate_timing_entropy(timestamps: List[str]) -> float:
    if len(timestamps) < 2:
        return 0.0
    try:
        hours = []
        for ts in timestamps:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hours.append(dt.hour)
        hour_counts = np.bincount(hours, minlength=24)
        probs = hour_counts / len(hours)
        entropy = -np.sum(probs[probs > 0] * np.log2(probs[probs > 0]))
        return min(entropy / np.log2(24), 1.0)
    except:
        return 0.0

def calculate_device_entropy(webgl_hash: str, canvas_hash: str) -> float:
    combined = (webgl_hash or "") + (canvas_hash or "")
    if not combined:
        return 0.0
    unique_chars = len(set(combined))
    return min(unique_chars / 32.0, 1.0)

def generate_behavior_hash(features: Dict) -> str:
    normalized = {
        "ip": normalize_ip(features.get("ip_address", "0.0.0.0")),
        "ua": normalize_user_agent(features.get("user_agent", "")),
        "screen": normalize_screen(features.get("screen_resolution", "1920x1080")),
        "tz": normalize_timezone(features.get("timezone", "UTC+0")),
        "typing": normalize_typing_latency(features.get("typing_latency_array", [])),
        "webgl": features.get("webgl_hash", ""),
        "canvas": features.get("canvas_hash", "")
    }
    
    feature_str = f"{normalized['ip']}{normalized['ua']}{normalized['screen']}{normalized['tz']}"
    return hashlib.sha256(feature_str.encode()).hexdigest()

def generate_fingerprint(login_event: Dict) -> Dict:
    ip_features = normalize_ip(login_event.get("ip_address", "0.0.0.0"))
    ua_features = normalize_user_agent(login_event.get("user_agent", ""))
    screen_features = normalize_screen(login_event.get("screen_resolution", "1920x1080"))
    tz_feature = normalize_timezone(login_event.get("timezone", "UTC+0"))
    typing_features = normalize_typing_latency(login_event.get("typing_latency_array", []))
    
    feature_vector = ip_features + ua_features + screen_features + [tz_feature] + typing_features
    
    ip_entropy = calculate_ip_entropy(login_event.get("ip_address", "0.0.0.0"))
    device_entropy = calculate_device_entropy(
        login_event.get("webgl_hash", ""),
        login_event.get("canvas_hash", "")
    )
    
    entropy_score = (ip_entropy * 0.4 + device_entropy * 0.6)
    
    behavior_hash = generate_behavior_hash(login_event)
    
    return {
        "user_id": login_event.get("user_id"),
        "behavior_hash": behavior_hash,
        "entropy_score": round(entropy_score, 4),
        "feature_vector": feature_vector,
        "ip_entropy": round(ip_entropy, 4),
        "device_entropy": round(device_entropy, 4)
    }
