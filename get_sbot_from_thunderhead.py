"""
Get S_bot addresses using thunderhead-labs Hyperliquid Stats API
This provides REAL trader PnL data for free!
"""
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

print("="*80)
print("GET S_BOT ADDRESSES FROM THUNDERHEAD-LABS API")
print("="*80)

# Step 1: Fetch cumulative PnL data
print("\n[1/5] FETCHING TRADER PNL DATA")
print("-"*80)

try:
    url = "https://api.thunderhead-labs.xyz/hyperliquid/cumulative_user_pnl"
    print(f"Fetching from: {url}")
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Fetched data for {len(data)} traders")
    
except Exception as e:
    print(f"[ERROR] Failed to fetch data: {e}")
    print("\nTrying alternative endpoint...")
    
    try:
        url = "https://api.thunderhead-labs.xyz/hyperliquid/user_pnl"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"[OK] Fetched data for {len(data)} traders")
    except Exception as e2:
        print(f"[ERROR] Alternative also failed: {e2}")
        print("\nAPI might be down or URL changed.")
        print("Check: https://github.com/thunderhead-labs/hyperliquid-stats")
        exit(1)

# Step 2: Convert to DataFrame and analyze
print("\n[2/5] ANALYZING TRADER PERFORMANCE")
print("-"*80)

df = pd.DataFrame(data)
print(f"Columns: {list(df.columns)}")

# Find PnL column
pnl_col = None
for col in df.columns:
    if 'pnl' in col.lower():
        pnl_col = col
        break

if not pnl_col:
    print("[ERROR] No PnL column found!")
    print(f"Available columns: {list(df.columns)}")
    exit(1)

print(f"Using PnL column: {pnl_col}")

# Find address column
addr_col = None
for col in df.columns:
    if 'address' in col.lower() or 'user' in col.lower() or 'wallet' in col.lower():
        addr_col = col
        break

if not addr_col:
    print("[ERROR] No address column found!")
    exit(1)

print(f"Using address column: {addr_col}")

# Sort by PnL
df_sorted = df.sort_values(pnl_col)

print(f"\nTrader PnL distribution:")
print(f"  Total traders: {len(df_sorted)}")
print(f"  Profitable: {(df_sorted[pnl_col] > 0).sum()}")
print(f"  Unprofitable: {(df_sorted[pnl_col] < 0).sum()}")
print(f"  Breakeven: {(df_sorted[pnl_col] == 0).sum()}")

print(f"\nTop 5 profitable traders:")
for i, row in df_sorted.tail(5).iterrows():
    print(f"  {row[addr_col]}: PnL = {row[pnl_col]}")

print(f"\nBottom 5 losing traders:")
for i, row in df_sorted.head(5).iterrows():
    print(f"  {row[addr_col]}: PnL = {row[pnl_col]}")

# Step 3: Create cohorts
print("\n[3/5] CREATING COHORTS")
print("-"*80)

# Top 20% = pros
# Bottom 20% = amateurs
top_count = max(20, int(len(df_sorted) * 0.2))
bottom_count = max(20, int(len(df_sorted) * 0.2))

top_traders = df_sorted.tail(top_count)
bottom_traders = df_sorted.head(bottom_count)

print(f"Top cohort: {len(top_traders)} traders")
print(f"  PnL range: {top_traders[pnl_col].min()} to {top_traders[pnl_col].max()}")

print(f"\nBottom cohort: {len(bottom_traders)} traders")
print(f"  PnL range: {bottom_traders[pnl_col].min()} to {bottom_traders[pnl_col].max()}")

# Step 4: Backup old files
print("\n[4/5] BACKING UP OLD COHORT FILES")
print("-"*80)

backup_dir = Path("live_demo/assets/backup")
backup_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

for filename in ['top_cohort.csv', 'bottom_cohort.csv']:
    old_path = Path(f"live_demo/assets/{filename}")
    if old_path.exists():
        backup_path = backup_dir / f"{filename.replace('.csv', '')}_{timestamp}.csv"
        shutil.copy(old_path, backup_path)
        print(f"[OK] Backed up {filename}")

# Step 5: Save new cohorts
print("\n[5/5] SAVING NEW COHORT FILES")
print("-"*80)

top_df = pd.DataFrame({'Account': top_traders[addr_col].values})
top_df.to_csv('live_demo/assets/top_cohort.csv', index=False)
print(f"[OK] Saved top_cohort.csv: {len(top_df)} addresses")

bottom_df = pd.DataFrame({'Account': bottom_traders[addr_col].values})
bottom_df.to_csv('live_demo/assets/bottom_cohort.csv', index=False)
print(f"[OK] Saved bottom_cohort.csv: {len(bottom_df)} addresses")

# Verification
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

top_verify = pd.read_csv('live_demo/assets/top_cohort.csv')
bot_verify = pd.read_csv('live_demo/assets/bottom_cohort.csv')

print(f"\nTop cohort: {len(top_verify)} addresses")
print(f"  Sample: {top_verify.iloc[0, 0]}")

print(f"\nBottom cohort: {len(bot_verify)} addresses")
print(f"  Sample: {bot_verify.iloc[0, 0]}")

print("\n" + "="*80)
print("COHORT GENERATION COMPLETE")
print("="*80)

print("""
SUCCESS! Cohorts generated from REAL trader PnL data!

These are ACTUAL traders ranked by performance:
- Top cohort: Most profitable traders
- Bottom cohort: Least profitable (losing) traders

NEXT STEPS:
1. Restart bot to load new cohort files
2. Monitor S_bot - should be active if these traders are currently trading
3. Update cohorts weekly/monthly to keep them fresh

These addresses are REAL and based on actual performance data!
""")

print("="*80)
