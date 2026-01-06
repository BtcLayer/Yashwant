import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

# Recent data (last 36 hours)
recent = df[df['ts_dt'] >= '2026-01-04'].copy()
recent['alpha'] = abs(recent['p_up'] - recent['p_down'])
recent['edge_bps'] = recent['alpha'] * 50.0
recent['net_edge'] = recent['edge_bps'] - 8.0

print("=" * 60)
print("MODEL ANALYSIS - New Model Performance")
print("=" * 60)

print(f"\nRecent signals (since Jan 4): {len(recent)}")
print(f"\nAVERAGE PREDICTIONS:")
print(f"  p_up:      {recent['p_up'].mean():.4f}")
print(f"  p_down:    {recent['p_down'].mean():.4f}")
print(f"  p_neutral: {recent['p_neutral'].mean():.4f}")

print(f"\nSIGNAL STRENGTH:")
print(f"  Average alpha: {recent['alpha'].mean():.4f}")
print(f"  Max alpha:     {recent['alpha'].max():.4f}")
print(f"  Min alpha:     {recent['alpha'].min():.4f}")

print(f"\nEDGE ANALYSIS:")
print(f"  Average edge:     {recent['edge_bps'].mean():.2f} bps")
print(f"  Average net edge: {recent['net_edge'].mean():.2f} bps")
print(f"  Max edge:         {recent['edge_bps'].max():.2f} bps")

print(f"\nGATE PASS RATES:")
net_edge_pass = (recent['net_edge'] > 0).sum()
print(f"  Net Edge (>0):    {net_edge_pass}/{len(recent)} ({net_edge_pass/len(recent)*100:.1f}%)")

conf_pass = (recent[['p_up', 'p_down']].max(axis=1) >= 0.60).sum()
print(f"  Confidence (>=0.60): {conf_pass}/{len(recent)} ({conf_pass/len(recent)*100:.1f}%)")

both_pass = ((recent['net_edge'] > 0) & (recent[['p_up', 'p_down']].max(axis=1) >= 0.60)).sum()
print(f"  BOTH gates:       {both_pass}/{len(recent)} ({both_pass/len(recent)*100:.1f}%)")

print(f"\nLAST 10 SIGNALS:")
print(recent[['ts_dt', 'p_up', 'p_down', 'alpha', 'edge_bps', 'net_edge']].tail(10).to_string(index=False))

print("\n" + "=" * 60)
if recent['net_edge'].mean() < 0:
    print("VERDICT: Model is TOO WEAK - cannot beat 8bps hurdle")
elif both_pass / len(recent) < 0.10:
    print("VERDICT: Gates are TOO STRICT - model has edge but blocked")
else:
    print("VERDICT: System is working - waiting for strong signal")
print("=" * 60)
