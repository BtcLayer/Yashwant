import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Analyze 5m bot current status
print("=" * 80)
print("5M BOT COMPREHENSIVE ANALYSIS")
print("=" * 80)

# 1. Check order intents
order_intent_path = Path('paper_trading_outputs/5m/logs/order_intent/date=2026-01-14/order_intent.jsonl')
if order_intent_path.exists():
    lines = [json.loads(l) for l in open(order_intent_path)]
    df_intent = pd.DataFrame(lines)
    print(f"\n📊 ORDER INTENTS (Jan 14): {len(df_intent)} total")
    
    if 'decision' in df_intent.columns:
        print(f"\nDecision breakdown:")
        print(df_intent['decision'].value_counts())
    
    if 'veto_reason_primary' in df_intent.columns:
        print(f"\nVeto reasons (primary):")
        print(df_intent['veto_reason_primary'].value_counts())
    
    if 'guard_details' in df_intent.columns:
        print(f"\nGuard details sample:")
        print(df_intent['guard_details'].head(10))
else:
    print("\n❌ No order intent logs found for Jan 14")

# 2. Check signals
signals_path = Path('paper_trading_outputs/5m/logs/signals/date=2026-01-14/signals.jsonl')
if signals_path.exists():
    lines = [json.loads(l) for l in open(signals_path)]
    df_signals = pd.DataFrame(lines)
    print(f"\n📈 SIGNALS (Jan 14): {len(df_signals)} total")
    
    if 'alpha' in df_signals.columns:
        print(f"\nAlpha stats:")
        print(f"  Mean: {df_signals['alpha'].mean():.4f}")
        print(f"  Std: {df_signals['alpha'].std():.4f}")
        print(f"  Min: {df_signals['alpha'].min():.4f}")
        print(f"  Max: {df_signals['alpha'].max():.4f}")
        
        # Count signals by direction
        df_signals['dir_label'] = df_signals['alpha'].apply(
            lambda x: 'LONG' if x > 0.001 else ('SHORT' if x < -0.001 else 'NEUTRAL')
        )
        print(f"\nSignal direction:")
        print(df_signals['dir_label'].value_counts())
    
    if 's_model' in df_signals.columns:
        print(f"\nModel confidence (s_model) stats:")
        print(f"  Mean: {df_signals['s_model'].mean():.4f}")
        print(f"  Std: {df_signals['s_model'].std():.4f}")
else:
    print("\n❌ No signals logs found for Jan 14")

# 3. Check executions
exec_path = Path('paper_trading_outputs/5m/logs/default/repro/repro.jsonl')
if exec_path.exists():
    lines = [json.loads(l) for l in open(exec_path)]
    df_exec = pd.DataFrame(lines)
    print(f"\n💰 EXECUTIONS: {len(df_exec)} total")
    
    if 'side' in df_exec.columns:
        print(f"\nSide breakdown:")
        print(df_exec['side'].value_counts())
    
    if 'realized_pnl' in df_exec.columns and 'unrealized_pnl' in df_exec.columns:
        total_realized = df_exec['realized_pnl'].sum()
        last_unrealized = df_exec['unrealized_pnl'].iloc[-1] if len(df_exec) > 0 else 0
        print(f"\nPnL Summary:")
        print(f"  Total Realized PnL: ${total_realized:.2f}")
        print(f"  Last Unrealized PnL: ${last_unrealized:.2f}")
        print(f"  Total PnL: ${total_realized + last_unrealized:.2f}")
    
    if 'equity' in df_exec.columns:
        print(f"\nEquity:")
        print(f"  Initial: ${df_exec['equity'].iloc[0]:.2f}" if len(df_exec) > 0 else "  N/A")
        print(f"  Current: ${df_exec['equity'].iloc[-1]:.2f}" if len(df_exec) > 0 else "  N/A")
        print(f"  Return: {((df_exec['equity'].iloc[-1] / df_exec['equity'].iloc[0] - 1) * 100):.2f}%" if len(df_exec) > 0 else "  N/A")
else:
    print("\n❌ No execution logs found")

# 4. Check health
health_path = Path('paper_trading_outputs/5m/logs/health/date=2026-01-14/health.jsonl')
if health_path.exists():
    lines = [json.loads(l) for l in open(health_path)]
    df_health = pd.DataFrame(lines)
    print(f"\n🏥 HEALTH SNAPSHOTS (Jan 14): {len(df_health)} total")
    
    if len(df_health) > 0:
        latest = df_health.iloc[-1]
        print(f"\nLatest health snapshot:")
        for key in ['recent_bars', 'mean_s_model', 'exec_count_recent', 'equity', 'Sharpe_roll_1w', 'max_dd_to_date']:
            if key in latest:
                print(f"  {key}: {latest[key]}")
else:
    print("\n❌ No health logs found for Jan 14")

# 5. Check costs
costs_path = Path('paper_trading_outputs/5m/logs/costs/date=2026-01-14/costs.jsonl')
if costs_path.exists():
    lines = [json.loads(l) for l in open(costs_path)]
    df_costs = pd.DataFrame(lines)
    print(f"\n💸 COSTS (Jan 14): {len(df_costs)} total")
    
    if 'total_cost_usd' in df_costs.columns:
        print(f"  Total costs: ${df_costs['total_cost_usd'].sum():.4f}")
else:
    print("\n❌ No costs logs found for Jan 14")

# 6. Root cause analysis
print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)

# Check if bot is generating signals but not trading
if signals_path.exists() and order_intent_path.exists():
    signals_count = len(df_signals)
    intent_count = len(df_intent)
    
    print(f"\n📊 Signal to Intent Conversion:")
    print(f"  Signals generated: {signals_count}")
    print(f"  Order intents created: {intent_count}")
    print(f"  Conversion rate: {(intent_count / signals_count * 100):.2f}%" if signals_count > 0 else "  N/A")
    
    # Check if intents are being vetoed
    if 'decision' in df_intent.columns:
        vetoed = (df_intent['decision'] == 'VETO').sum()
        approved = (df_intent['decision'] == 'APPROVE').sum()
        print(f"\n🚦 Intent Approval:")
        print(f"  Approved: {approved}")
        print(f"  Vetoed: {vetoed}")
        print(f"  Approval rate: {(approved / intent_count * 100):.2f}%" if intent_count > 0 else "  N/A")
        
        # Analyze veto reasons
        if vetoed > 0 and 'veto_reason_primary' in df_intent.columns:
            print(f"\n🛑 Top Veto Reasons:")
            veto_df = df_intent[df_intent['decision'] == 'VETO']
            for reason, count in veto_df['veto_reason_primary'].value_counts().head(5).items():
                print(f"  {reason}: {count} ({count/vetoed*100:.1f}%)")

# Check trading frequency
if exec_path.exists() and len(df_exec) > 0:
    print(f"\n⏱️ Trading Frequency:")
    print(f"  Total trades: {len(df_exec)}")
    
    # Calculate time between trades
    if 'ts' in df_exec.columns:
        df_exec['ts_dt'] = pd.to_datetime(df_exec['ts'], unit='ms')
        time_diffs = df_exec['ts_dt'].diff()
        print(f"  Average time between trades: {time_diffs.mean()}")
        print(f"  Min time between trades: {time_diffs.min()}")
        print(f"  Max time between trades: {time_diffs.max()}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
