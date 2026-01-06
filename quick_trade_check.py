import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

print("Last 5 trades:")
print(df[['ts_dt', 'side', 'realized_pnl']].tail(5))
print(f"\nTotal trades: {len(df)}")
print(f"Date range: {df['ts_dt'].min()} to {df['ts_dt'].max()}")
