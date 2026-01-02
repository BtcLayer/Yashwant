import pandas as pd
import json

# Check config
with open('live_demo/config.json') as f:
    config = json.load(f)
    require_consensus = config['thresholds'].get('require_consensus', 'NOT FOUND')

# Check signals
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
down_preds = (df['s_model'] < 0).sum()
sell_signals = (df['dir'] == -1).sum()

# Check executions
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
sell_trades = (exec_df['side'] == 'SELL').sum()

print("="*80)
print("DIAGNOSTIC CHECK")
print("="*80)
print(f"\n1. CONFIG:")
print(f"   require_consensus = {require_consensus}")
print(f"   Status: {'✅ Fix applied' if require_consensus == False else '❌ Fix not applied'}")

print(f"\n2. MODEL PREDICTIONS:")
print(f"   DOWN predictions (s_model < 0): {down_preds}")

print(f"\n3. DECISION SIGNALS:")
print(f"   SELL signals (dir = -1): {sell_signals}")

print(f"\n4. EXECUTIONS:")
print(f"   SELL trades: {sell_trades}")

print(f"\n5. DIAGNOSIS:")
if sell_trades > 0:
    print(f"   ✅ FIX IS WORKING! {sell_trades} SELL trades executed")
elif sell_signals > 0:
    print(f"   ⚠️  SELL signals exist but not executing - check execution logic")
elif down_preds > 0:
    print(f"   ⚠️  Model predicts DOWN but no SELL signals - consensus still blocking?")
else:
    print(f"   ⏳ Model hasn't predicted DOWN yet - market conditions")
    print(f"   ℹ️  This is NORMAL - BTC may be in uptrend")

print("="*80)
