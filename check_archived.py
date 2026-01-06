import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper_ARCHIVED_20260103.csv')
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

print("=" * 70)
print("ARCHIVED TRADES (Before Jan 3 Restart)")
print("=" * 70)

print(f"\nTotal trades: {len(df)}")
print(f"Total realized PnL: ${df['realized_pnl'].sum():.2f}")
print(f"Date range: {df['ts_dt'].min()} to {df['ts_dt'].max()}")

print(f"\nWin rate: {(df['realized_pnl'] > 0).sum()}/{len(df)} ({(df['realized_pnl'] > 0).sum()/len(df)*100:.1f}%)")
print(f"Average PnL per trade: ${df['realized_pnl'].mean():.2f}")

print(f"\nLast 10 trades:")
print(df[['ts_dt', 'side', 'realized_pnl']].tail(10).to_string(index=False))

print("\n" + "=" * 70)
