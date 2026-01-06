import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

# Jan 3 (when bot was working and profitable)
jan3 = df[(df['ts_dt'] >= '2026-01-03') & (df['ts_dt'] < '2026-01-04')].copy()
jan3['alpha'] = abs(jan3['p_up'] - jan3['p_down'])

# Jan 5 (today - not trading)
jan5 = df[df['ts_dt'] >= '2026-01-05'].copy()
jan5['alpha'] = abs(jan5['p_up'] - jan5['p_down'])

print("=" * 70)
print("MODEL PERFORMANCE COMPARISON: Jan 3 vs Jan 5")
print("=" * 70)

print("\nJAN 3 (When it was WORKING and PROFITABLE):")
print(f"  Total signals: {len(jan3)}")
print(f"  Avg alpha: {jan3['alpha'].mean():.4f}")
print(f"  Avg edge: {jan3['alpha'].mean() * 50:.2f} bps")
print(f"  Max alpha: {jan3['alpha'].max():.4f}")
print(f"  Signals with alpha > 0.16: {(jan3['alpha'] > 0.16).sum()}/{len(jan3)} ({(jan3['alpha'] > 0.16).sum()/len(jan3)*100:.1f}%)")
print(f"  Avg p_up: {jan3['p_up'].mean():.4f}")
print(f"  Avg p_down: {jan3['p_down'].mean():.4f}")
print(f"  Avg p_neutral: {jan3['p_neutral'].mean():.4f}")

print("\nJAN 5 (TODAY - Not trading):")
print(f"  Total signals: {len(jan5)}")
print(f"  Avg alpha: {jan5['alpha'].mean():.4f}")
print(f"  Avg edge: {jan5['alpha'].mean() * 50:.2f} bps")
print(f"  Max alpha: {jan5['alpha'].max():.4f}")
print(f"  Signals with alpha > 0.16: {(jan5['alpha'] > 0.16).sum()}/{len(jan5)} ({(jan5['alpha'] > 0.16).sum()/len(jan5)*100 if len(jan5) > 0 else 0:.1f}%)")
print(f"  Avg p_up: {jan5['p_up'].mean():.4f}")
print(f"  Avg p_down: {jan5['p_down'].mean():.4f}")
print(f"  Avg p_neutral: {jan5['p_neutral'].mean():.4f}")

print("\nCHANGE (Jan 5 vs Jan 3):")
alpha_change = (jan5['alpha'].mean() - jan3['alpha'].mean()) * 50
print(f"  Edge change: {alpha_change:+.2f} bps")
print(f"  Neutral probability change: {(jan5['p_neutral'].mean() - jan3['p_neutral'].mean())*100:+.1f}%")

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

if jan5['p_neutral'].mean() > 0.60:
    print("\nPROBLEM: Model is predicting NEUTRAL too often!")
    print(f"  - Jan 3: {jan3['p_neutral'].mean()*100:.1f}% neutral")
    print(f"  - Jan 5: {jan5['p_neutral'].mean()*100:.1f}% neutral")
    print("\nPOSSIBLE CAUSES:")
    print("  1. Market conditions changed (sideways/choppy)")
    print("  2. Model features are stale/broken")
    print("  3. Model weights were accidentally changed")
elif alpha_change < -2:
    print("\nPROBLEM: Model confidence DROPPED significantly!")
    print(f"  - Lost {abs(alpha_change):.2f} bps of edge")
else:
    print("\nModel looks similar - might just be market conditions")

print("=" * 70)
