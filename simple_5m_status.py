import json
import pandas as pd
from pathlib import Path

print("5M BOT STATUS REPORT")
print("=" * 80)

# 1. Order Intents
intent_path = Path('paper_trading_outputs/5m/logs/order_intent/date=2026-01-14/order_intent.jsonl')
if intent_path.exists():
    with open(intent_path) as f:
        intents = [json.loads(line) for line in f]
    
    df_intent = pd.DataFrame(intents)
    print(f"\n1. ORDER INTENTS: {len(intents)} total")
    
    if 'decision' in df_intent.columns:
        print("\nDecision Breakdown:")
        print(df_intent['decision'].value_counts())
    
    if 'veto_reason_primary' in df_intent.columns:
        vetoed = df_intent[df_intent['decision'] == 'VETO']
        if len(vetoed) > 0:
            print(f"\nTop 5 Veto Reasons:")
            print(vetoed['veto_reason_primary'].value_counts().head(5))

# 2. Signals
signals_path = Path('paper_trading_outputs/5m/logs/signals/date=2026-01-14/signals.jsonl')
if signals_path.exists():
    with open(signals_path) as f:
        signals = [json.loads(line) for line in f]
    
    df_sig = pd.DataFrame(signals)
    print(f"\n2. SIGNALS: {len(signals)} total")
    
    if 'alpha' in df_sig.columns:
        print(f"\nAlpha Stats:")
        print(f"  Mean: {df_sig['alpha'].mean():.6f}")
        print(f"  Std: {df_sig['alpha'].std():.6f}")
        print(f"  Min: {df_sig['alpha'].min():.6f}")
        print(f"  Max: {df_sig['alpha'].max():.6f}")

# 3. Executions
exec_path = Path('paper_trading_outputs/5m/logs/default/repro/repro.jsonl')
if exec_path.exists():
    with open(exec_path) as f:
        execs = [json.loads(line) for line in f]
    
    df_exec = pd.DataFrame([e['repro'] for e in execs])
    print(f"\n3. EXECUTIONS: {len(execs)} total")
    
    if 'side' in df_exec.columns:
        print("\nSide Breakdown:")
        print(df_exec['side'].value_counts())
    
    if 'equity' in df_exec.columns:
        initial = df_exec['equity'].iloc[0]
        current = df_exec['equity'].iloc[-1]
        ret = (current / initial - 1) * 100
        print(f"\nEquity: ${initial:.2f} -> ${current:.2f} ({ret:.2f}%)")

# 4. Root Cause
print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)

if intent_path.exists() and signals_path.exists():
    signal_count = len(signals)
    intent_count = len(intents)
    exec_count = len(execs) if exec_path.exists() else 0
    
    print(f"\nFunnel:")
    print(f"  Signals: {signal_count}")
    print(f"  Intents: {intent_count} ({intent_count/signal_count*100:.1f}%)")
    print(f"  Executions: {exec_count} ({exec_count/intent_count*100:.1f}% of intents)")
    
    if 'decision' in df_intent.columns:
        vetoed = (df_intent['decision'] == 'VETO').sum()
        approved = (df_intent['decision'] == 'APPROVE').sum()
        
        print(f"\nApproval:")
        print(f"  Approved: {approved} ({approved/intent_count*100:.1f}%)")
        print(f"  Vetoed: {vetoed} ({vetoed/intent_count*100:.1f}%)")
        
        if vetoed > 0:
            print(f"\n⚠️ ISSUE: {vetoed} intents vetoed ({vetoed/intent_count*100:.1f}%)")

print("\n" + "=" * 80)
