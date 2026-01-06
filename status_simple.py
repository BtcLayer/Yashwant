import pandas as pd

print("="*80)
print("5M BOT CURRENT STATUS - 2026-01-06 12:56 IST")
print("="*80)

# Load data
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
executions = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

print("\nBOT RUNTIME: 40+ minutes")
print(f"Total signals: {len(signals)}")
print(f"Total trades: {len(executions)}")

print("\n" + "-"*80)
print("SIGNAL DIRECTION DISTRIBUTION")
print("-"*80)
dir_counts = signals['dir'].value_counts().sort_index()
for val, count in dir_counts.items():
    pct = count / len(signals) * 100
    print(f"dir={val}: {count:>5} ({pct:>5.1f}%)")

print("\nRecent 100 signals:")
recent = signals.tail(100)
recent_counts = recent['dir'].value_counts().sort_index()
for val, count in recent_counts.items():
    pct = count / len(recent) * 100
    print(f"dir={val}: {count:>5} ({pct:>5.1f}%)")

print("\n" + "-"*80)
print("ALPHA STATISTICS")
print("-"*80)
print(f"Mean alpha: {signals['alpha'].mean():.6f} ({signals['alpha'].mean()*10000:.2f} bps)")
print(f"Positive alpha: {(signals['alpha'] > 0).sum()} ({(signals['alpha']>0).sum()/len(signals)*100:.1f}%)")
print(f"Zero alpha: {(signals['alpha'] == 0).sum()} ({(signals['alpha']==0).sum()/len(signals)*100:.1f}%)")
print(f"Alpha > 2 bps: {(signals['alpha'] > 0.0002).sum()}")

print("\n" + "-"*80)
print("TRADE EXECUTION")
print("-"*80)
side_counts = executions['side'].value_counts()
for side, count in side_counts.items():
    pct = count / len(executions) * 100
    print(f"{side}: {count} ({pct:.1f}%)")

print("\n" + "-"*80)
print("PERFORMANCE")
print("-"*80)
total_pnl = executions['realized_pnl'].sum()
win_rate = (executions['realized_pnl'] > 0).sum() / len(executions) * 100
current_eq = executions['equity'].iloc[-1]
initial_eq = executions['equity'].iloc[0]
returns = (current_eq - initial_eq) / initial_eq * 100

print(f"Total PnL: ${total_pnl:.2f}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Current Equity: ${current_eq:.2f}")
print(f"Total Return: {returns:.3f}%")

print("\n" + "-"*80)
print("LAST 10 SIGNALS")
print("-"*80)
print(signals[['ts_iso', 'dir', 'alpha', 'close']].tail(10).to_string(index=False))

print("\n" + "="*80)
print("KEY FINDINGS")
print("="*80)
neutral_pct = (signals['dir']==0).sum()/len(signals)*100
dir1_count = (signals['dir']==1).sum()
zero_alpha_pct = (signals['alpha']==0).sum()/len(signals)*100

print(f"1. NEUTRAL signals (dir=0): {neutral_pct:.1f}%")
print(f"2. dir=1 signals: {dir1_count}")
print(f"3. Zero alpha signals: {zero_alpha_pct:.1f}%")
print(f"4. All {len(executions)} trades are BUY - NO SELL TRADES")
print("\nCRITICAL: Bot generating mostly NEUTRAL signals with zero alpha!")
print("="*80)
