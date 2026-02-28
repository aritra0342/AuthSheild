#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AuthShield AI - Botnet Attack Simulation
==========================================

This script simulates a real botnet attack for demonstration purposes.

Usage:
    python test_botnet.py [options]
    
Options:
    --url=URL    - Override API URL (default: http://localhost:8000)
    --no-mock    - Disable mock mode (use real Auth0)
    --quick      - Run quick simulation (fewer users)
    
Author: AuthShield AI Team
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import random
import time
import argparse
from datetime import datetime

# Configuration
class Config:
    def __init__(self):
        parser = argparse.ArgumentParser(description='AuthShield AI Botnet Simulation')
        parser.add_argument('--url', default='http://localhost:8000', help='API base URL')
        parser.add_argument('--no-mock', action='store_true', help='Disable mock mode')
        parser.add_argument('--quick', action='store_true', help='Quick simulation')
        parser.add_argument('--phase', type=int, help='Run specific phase only (1-5)')
        
        args = parser.parse_args()
        
        self.base_url = args.url.rstrip('/')
        self.quick_mode = args.quick
        self.specific_phase = args.phase
        
        # Detect mock mode from server
        try:
            health = requests.get(f"{self.base_url}/api/health", timeout=5)
            self.server_online = health.status_code == 200
        except:
            self.server_online = False
        
        # Simulation parameters
        if self.quick_mode:
            self.normal_users = 3
            self.botnet_users = 6
            self.botnet_devices = 2
        else:
            self.normal_users = 5
            self.botnet_users = 15
            self.botnet_devices = 3

config = Config()

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(title):
    """Print formatted section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_subheader(title):
    """Print formatted subsection header"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  {'-'*50}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.OKGREEN}  ✓ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.WARNING}  ⚠ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.FAIL}  ✗ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.OKBLUE}  ℹ {message}{Colors.ENDC}")

def print_botnet(message):
    print(f"{Colors.FAIL}  🚨 {message}{Colors.ENDC}")

def check_server():
    """Check if server is online"""
    print_header("Server Health Check")
    
    try:
        response = requests.get(f"{config.base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print_success(f"Server online: {config.base_url}")
            print_info(f"Timestamp: {response.json().get('timestamp', 'N/A')}")
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server")
        print_info(f"Make sure server is running: python main.py")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def simulate_normal_users():
    """Phase 1: Simulate legitimate users with unique fingerprints"""
    print_header("Phase 1: Normal Users (Legitimate Traffic)")
    print_info(f"Simulating {config.normal_users} users with unique fingerprints...\n")
    
    normal_count = 0
    
    for i in range(config.normal_users):
        user_id = f"legitimate_user_{i+1:03d}"
        
        # Each normal user has unique device fingerprint
        payload = {
            "user_id": user_id,
            "ip_address": f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "user_agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0"
            ]),
            "webgl_hash": f"webgl_unique_{random.randint(100000, 999999)}",
            "canvas_hash": f"canvas_unique_{random.randint(100000, 999999)}",
            "screen_resolution": random.choice(["1920x1080", "1366x768", "2560x1440"]),
            "timezone": f"UTC{'+' if random.random() > 0.5 else '-'}{random.randint(0,12)}"
        }
        
        try:
            response = requests.post(
                f"{config.base_url}/api/simulate",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                risk = data.get('risk_score', 0)
                suspicious = data.get('is_suspicious', False)
                
                status_icon = "🟢" if not suspicious else "🟡"
                print(f"  {status_icon} {user_id}: Risk={risk:.3f} | Fingerprint=UNIQUE")
                normal_count += 1
            else:
                print_error(f"{user_id}: Failed (status {response.status_code})")
                
        except Exception as e:
            print_error(f"{user_id}: Error - {str(e)[:50]}")
        
        time.sleep(0.1)
    
    print()
    print_success(f"Successfully registered {normal_count}/{config.normal_users} legitimate users")
    return normal_count

def simulate_botnet_attack():
    """Phase 2: Simulate botnet with shared device fingerprints"""
    print_header("Phase 2: Botnet Attack (Coordinated Attack)")
    print_warning("DETECTED: Multiple users sharing same device fingerprints!")
    print_info(f"Simulating {config.botnet_users} bot users on {config.botnet_devices} shared devices...\n")
    
    # Shared device fingerprints (classic botnet pattern)
    botnet_devices = [
        {
            "webgl": "BOT_DEVICE_ALPHA_001",
            "canvas": "BOT_CANVAS_ALPHA_001",
            "location": "Data Center A"
        },
        {
            "webgl": "BOT_DEVICE_BETA_002", 
            "canvas": "BOT_CANVAS_BETA_002",
            "location": "Data Center B"
        },
        {
            "webgl": "BOT_DEVICE_GAMMA_003",
            "canvas": "BOT_CANVAS_GAMMA_003",
            "location": "VPN Cluster C"
        }
    ][:config.botnet_devices]
    
    botnet_count = 0
    suspicious_count = 0
    
    for i in range(config.botnet_users):
        # Rotate through shared devices
        device = botnet_devices[i % len(botnet_devices)]
        user_id = f"bot_suspect_{i+1:03d}"
        
        payload = {
            "user_id": user_id,
            "ip_address": f"45.{random.randint(33,47)}.{random.randint(1,255)}.{random.randint(1,255)}",  # Suspicious IP range
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",  # Same UA
            "webgl_hash": device["webgl"],
            "canvas_hash": device["canvas"],
            "screen_resolution": "1920x1080",  # Same resolution
            "timezone": "UTC+5",  # Same timezone
            "typing_latency_array": [100, 105, 100, 105, 100]  # Pattern (non-human)
        }
        
        try:
            response = requests.post(
                f"{config.base_url}/api/simulate",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                risk = data.get('risk_score', 0)
                suspicious = data.get('is_suspicious', False)
                
                if suspicious:
                    suspicious_count += 1
                    print_botnet(f"{user_id}: Risk={risk:.3f} | Device={device['location']} | FLAGGED")
                else:
                    print_warning(f"{user_id}: Risk={risk:.3f} | Device={device['location']}")
                
                botnet_count += 1
            else:
                print_error(f"{user_id}: Failed (status {response.status_code})")
                
        except Exception as e:
            print_error(f"{user_id}: Error - {str(e)[:50]}")
        
        time.sleep(0.1)
    
    print()
    print_success(f"Registered {botnet_count}/{config.botnet_users} botnet users")
    print_warning(f"⚠️  {suspicious_count} users automatically flagged as suspicious")
    return botnet_count, suspicious_count

def detect_clusters():
    """Phase 3: Detect user clusters based on shared fingerprints"""
    print_header("Phase 3: Cluster Detection & Analysis")
    
    try:
        response = requests.get(f"{config.base_url}/api/clusters", timeout=10)
        
        if response.status_code == 200:
            clusters = response.json()
            
            if not clusters:
                print_warning("No clusters detected yet")
                print_info("Clusters form when users share fingerprints")
                return 0
            
            print_success(f"Detected {len(clusters)} cluster(s)\n")
            
            total_clustered_users = 0
            
            for i, cluster in enumerate(clusters, 1):
                members = cluster.get('members', [])
                size = cluster.get('size', len(members))
                behavior_hash = cluster.get('behavior_hash', 'N/A')
                
                total_clustered_users += size
                
                print(f"  {Colors.BOLD}Cluster #{i}:{Colors.ENDC}")
                print(f"    Size: {size} users")
                print(f"    Behavior Hash: {behavior_hash[:40]}...")
                
                if members:
                    member_preview = ', '.join(members[:3])
                    if len(members) > 3:
                        member_preview += f", and {len(members)-3} more..."
                    print(f"    Members: {member_preview}")
                print()
            
            print_info(f"Total users in clusters: {total_clustered_users}")
            return len(clusters)
        else:
            print_error(f"Failed to fetch clusters (status {response.status_code})")
            return 0
            
    except Exception as e:
        print_error(f"Cluster detection error: {e}")
        return 0

def auto_freeze_suspicious():
    """Phase 4: Automatically freeze suspicious clustered users"""
    print_header("Phase 4: Auto-Freeze Suspicious Users")
    
    print_info("Scanning for users matching freeze criteria:")
    print("    • Cluster size > 2 users")
    print("    • Risk score > 0.3")
    print("    • Shared device fingerprint\n")
    
    try:
        response = requests.post(f"{config.base_url}/api/check-clusters", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            flagged = result.get('flagged_count', 0)
            frozen = result.get('frozen_count', 0)
            frozen_users = result.get('frozen_users', [])
            
            print_success(f"Scan complete:")
            print(f"    • Users flagged: {flagged}")
            print(f"    • Users frozen: {frozen}\n")
            
            if frozen_users:
                print(f"  {Colors.BOLD}Frozen User Accounts:{Colors.ENDC}")
                for user_id in frozen_users[:10]:
                    print(f"    ❄ {user_id}")
                
                if len(frozen_users) > 10:
                    print(f"    ... and {len(frozen_users)-10} more")
            
            return frozen
        else:
            print_error(f"Auto-freeze failed (status {response.status_code})")
            print_info(f"Response: {response.text[:200]}")
            return 0
            
    except Exception as e:
        print_error(f"Auto-freeze error: {e}")
        return 0

def show_freeze_log():
    """Phase 5: Display audit trail of freeze actions"""
    print_header("Phase 5: Audit Trail (Freeze Log)")
    
    try:
        response = requests.get(f"{config.base_url}/api/freeze-log", timeout=10)
        
        if response.status_code == 200:
            logs = response.json()
            
            if not logs:
                print_warning("No freeze actions recorded yet")
                return
            
            print_success(f"Found {len(logs)} freeze action(s)\n")
            
            print(f"  {'Timestamp':<25} {'User ID':<25} {'Action':<10} {'Reason'}")
            print(f"  {'-'*25} {'-'*25} {'-'*10} {'-'*40}")
            
            for log in logs[:10]:
                timestamp = log.get('timestamp', 'N/A')
                if isinstance(timestamp, str):
                    timestamp = timestamp[:19]
                
                user_id = log.get('user_id', 'N/A')
                action = log.get('action', 'N/A')
                reason = log.get('reason', 'N/A')
                
                print(f"  {timestamp:<25} {user_id:<25} {action:<10} {reason}")
            
            if len(logs) > 10:
                print(f"\n  ... and {len(logs)-10} more entries")
                
        else:
            print_error(f"Failed to fetch freeze log (status {response.status_code})")
            
    except Exception as e:
        print_error(f"Freeze log error: {e}")

def show_summary(normal, botnet, suspicious, clusters, frozen):
    """Display final summary"""
    print_header("Simulation Summary")
    
    total_users = normal + botnet
    
    print(f"  {Colors.BOLD}Statistics:{Colors.ENDC}")
    print(f"    • Total users simulated: {total_users}")
    print(f"    • Legitimate users: {normal}")
    print(f"    • Botnet users: {botnet}")
    print(f"    • Suspicious flags: {suspicious}")
    print(f"    • Clusters detected: {clusters}")
    print(f"    • Accounts frozen: {frozen}")
    
    print(f"\n  {Colors.BOLD}Effectiveness:{Colors.ENDC}")
    if botnet > 0:
        detection_rate = (suspicious / botnet) * 100
        freeze_rate = (frozen / botnet) * 100 if frozen > 0 else 0
        
        print(f"    • Detection rate: {detection_rate:.1f}%")
        print(f"    • Freeze rate: {freeze_rate:.1f}%")
    
    print(f"\n  {Colors.BOLD}Dashboard URLs:{Colors.ENDC}")
    dashboard_url = config.base_url.replace('/api', '')
    print(f"    • Dashboard: {dashboard_url}")
    print(f"    • Live Events: {dashboard_url} (Events tab)")
    print(f"    • Clusters: {dashboard_url} (Clusters tab)")
    print(f"    • Flagged Users: {dashboard_url} (Flagged tab)")
    print(f"    • Freeze Log: {dashboard_url} (Freeze Log tab)")
    print(f"    • Blockchain: {dashboard_url} (Blockchain tab)")

def main():
    """Main execution function"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("  " + "="*67)
    print("  |                                                               |")
    print("  |           AuthShield AI - Botnet Attack Simulation            |")
    print("  |                                                               |")
    print("  |  Detecting coordinated attacks through fingerprint analysis   |")
    print("  |                                                               |")
    print("  " + "="*67)
    print(f"{Colors.ENDC}")
    
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Target: {config.base_url}")
    print(f"  Mode: {'Quick' if config.quick_mode else 'Full'} simulation")
    
    # Check server
    if not check_server():
        print_error("\nServer is not reachable. Exiting.")
        sys.exit(1)
    
    # Track statistics
    stats = {
        'normal': 0,
        'botnet': 0,
        'suspicious': 0,
        'clusters': 0,
        'frozen': 0
    }
    
    # Run phases
    if not config.specific_phase or config.specific_phase == 1:
        stats['normal'] = simulate_normal_users()
    
    if not config.specific_phase or config.specific_phase == 2:
        stats['botnet'], stats['suspicious'] = simulate_botnet_attack()
    
    if not config.specific_phase or config.specific_phase == 3:
        stats['clusters'] = detect_clusters()
    
    if not config.specific_phase or config.specific_phase == 4:
        stats['frozen'] = auto_freeze_suspicious()
    
    if not config.specific_phase or config.specific_phase == 5:
        show_freeze_log()
    
    # Final summary
    show_summary(**stats)
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Simulation Complete{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Simulation interrupted by user{Colors.ENDC}\n")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
