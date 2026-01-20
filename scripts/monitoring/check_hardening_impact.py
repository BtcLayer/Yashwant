import pandas as pd
from datetime import datetime

# Load execution data
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

# Convert timestamp
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

# Define restart time (when new logic went live)
restart_time = pd.to_datetime('2026-01-05 12:17:00')

# Split into before/after
before_restart = df[df['ts_dt'] < restart_time]
after_restart = df[df['ts_dt'] >= restart_time]

print("=" * 60)
print("TRADING ACTIVITY ANALYSIS - Before vs After Logic Hardening")
print("=" * 60)

print("\n📊 BEFORE RESTART (Old Logic):")
print(f"   Total Trades: {len(before_restart)}")
if len(before_restart) > 0:
    print(f"   Avg PnL per trade: ${before_restart['realized_pnl'].mean():.2f}")
    print(f"   Total PnL: ${before_restart['realized_pnl'].sum():.2f}")
    print(f"   Win Rate: {(before_restart['realized_pnl'] > 0).sum() / len(before_restart) * 100:.1f}%")

print("\n📊 AFTER RESTART (New Logic - Hardened):")
print(f"   Total Trades: {len(after_restart)}")
if len(after_restart) > 0:
    print(f"   Avg PnL per trade: ${after_restart['realized_pnl'].mean():.2f}")
    print(f"   Total PnL: ${after_restart['realized_pnl'].sum():.2f}")
    print(f"   Win Rate: {(after_restart['realized_pnl'] > 0).sum() / len(after_restart) * 100:.1f}%")
    print("\n   Recent Trades:")
    print(after_restart[['ts_iso', 'side', 'realized_pnl', 'qty']].tail(5).to_string(index=False))
else:
    print("   ⚠️  NO TRADES YET since restart")
    print(f"   Time elapsed: {(datetime.now() - restart_time).total_seconds() / 60:.1f} minutes")
    print("   This could mean:")
    print("   1. Market conditions don't meet new strict criteria (GOOD - protecting capital)")
    print("   2. Bot is still warming up / waiting for next bar close")

print("\n" + "=" * 60)
