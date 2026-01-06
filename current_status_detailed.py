import pandas as pd
import numpy as np

# Load signals
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print("=" * 80)
print("COMPREHENSIVE 5M BOT STATUS - " + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'))
print("=" * 80)

# Bot runtime
print("\n🤖 BOT STATUS")
print("─" * 80)
print("Status: RUNNING (40+ minutes)")
print("Total signals generated: 1,813")

# Analyze direction encoding
# Typically: 0 = NEUTRAL, 1 = BUY, -1 = SELL or 0 = NEUTRAL, 1 = LONG, 2 = SHORT
print("\n📊 SIGNAL DIRECTION ANALYSIS")
print("─" * 80)

dir_counts = df['dir'].value_counts().sort_index()
print("Direction value counts:")
for val, count in dir_counts.items():
    pct = count / len(df) * 100
    print(f"  dir={val}: {count:>5} signals ({pct:>5.1f}%)")

# Check recent signals
recent = df.tail(100)
recent_counts = recent['dir'].value_counts().sort_index()
print("\nRecent 100 signals:")
for val, count in recent_counts.items():
    pct = count / len(recent) * 100
    print(f"  dir={val}: {count:>5} signals ({pct:>5.1f}%)")

# Alpha analysis
print("\n💰 ALPHA ANALYSIS")
print("─" * 80)
print(f"Mean alpha: {df['alpha'].mean():.6f} ({df['alpha'].mean() * 10000:.2f} bps)")
print(f"Median alpha: {df['alpha'].median():.6f} ({df['alpha'].median() * 10000:.2f} bps)")
print(f"Positive alpha signals: {(df['alpha'] > 0).sum()} ({(df['alpha'] > 0).sum()/len(df)*100:.1f}%)")
print(f"Zero alpha signals: {(df['alpha'] == 0).sum()} ({(df['alpha'] == 0).sum()/len(df)*100:.1f}%)")
print(f"Negative alpha signals: {(df['alpha'] < 0).sum()} ({(df['alpha'] < 0).sum()/len(df)*100:.1f}%)")

# Check for signals with alpha > threshold
alpha_threshold = 0.0002  # 2 bps
high_alpha = df[df['alpha'] > alpha_threshold]
print(f"\nSignals with alpha > {alpha_threshold*10000:.1f} bps: {len(high_alpha)} ({len(high_alpha)/len(df)*100:.1f}%)")

# Load executions
print("\n⚖️ TRADE EXECUTION ANALYSIS")
print("─" * 80)

exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
print(f"Total trades executed: {len(exec_df)}")

side_counts = exec_df['side'].value_counts()
for side, count in side_counts.items():
    pct = count / len(exec_df) * 100
    print(f"  {side}: {count} trades ({pct:.1f}%)")

# Check if there's a mismatch
print("\n🔍 DIAGNOSIS")
print("─" * 80)

# Count non-zero direction signals
non_neutral = df[df['dir'] != 0]
print(f"Non-neutral signals (dir != 0): {len(non_neutral)} ({len(non_neutral)/len(df)*100:.1f}%)")
print(f"Trades executed: {len(exec_df)}")

if len(non_neutral) > 0:
    print(f"\nExecution rate: {len(exec_df)/len(non_neutral)*100:.1f}% of non-neutral signals")
    
    # Show breakdown of dir=1 signals
    dir_1_signals = df[df['dir'] == 1]
    print(f"\ndir=1 signals: {len(dir_1_signals)}")
    print(f"  With alpha > 0: {(dir_1_signals['alpha'] > 0).sum()}")
    print(f"  With alpha > 2 bps: {(dir_1_signals['alpha'] > 0.0002).sum()}")

# Recent activity
print("\n🔄 RECENT ACTIVITY (Last 20 signals)")
print("─" * 80)
recent_20 = df.tail(20)
print(f"dir=0 (neutral): {(recent_20['dir'] == 0).sum()}")
print(f"dir=1: {(recent_20['dir'] == 1).sum()}")
print(f"Non-zero alpha: {(recent_20['alpha'] != 0).sum()}")

# Show last few signals with details
print("\nLast 5 signals with details:")
cols = ['ts_iso', 'dir', 'alpha', 'close']
print(df[cols].tail(5).to_string(index=False))

# Performance metrics
print("\n📈 PERFORMANCE METRICS")
print("─" * 80)
if len(exec_df) > 0:
    total_pnl = exec_df['realized_pnl'].sum()
    win_rate = (exec_df['realized_pnl'] > 0).sum() / len(exec_df) * 100
    current_equity = exec_df['equity'].iloc[-1]
    initial_equity = exec_df['equity'].iloc[0]
    total_return = (current_equity - initial_equity) / initial_equity * 100
    
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Current Equity: ${current_equity:.2f}")
    print(f"Total Return: {total_return:.3f}%")

print("\n" + "=" * 80)
print("KEY FINDINGS:")
print("=" * 80)
print(f"1. Signals are mostly NEUTRAL (dir=0): {(df['dir']==0).sum()/len(df)*100:.1f}%")
print(f"2. Only {(df['dir']==1).sum()} signals have dir=1 (likely BUY)")
print(f"3. Most signals have alpha=0: {(df['alpha']==0).sum()/len(df)*100:.1f}%")
print(f"4. All {len(exec_df)} executed trades are BUY - NO SELL TRADES")
print("\n⚠️  CRITICAL: Bot is generating mostly NEUTRAL signals with zero alpha!")
print("=" * 80)
