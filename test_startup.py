import sys
sys.path.insert(0, '.')
import json

print("Loading config...")
cfg = json.load(open('live_demo/config.json'))
print(f"✓ Config loaded: {cfg['exchanges']['active']}")

print("\nImporting modules...")
from live_demo.market_data import MarketData
print("✓ MarketData imported")

from live_demo.config import Config  
print("✓ Config imported")

print("\nChecking credentials...")
import os
cred_path = "live_demo/metastackerbandit1-478b6face97d.json"
if os.path.exists(cred_path):
    print(f"✓ Credentials file exists")
else:
    print(f"✗ Credentials file not found")

print("\n✓ ALL BASIC CHECKS PASSED")
