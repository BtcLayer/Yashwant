import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def safe_ts_format(ts):
    """Safely format timestamp, handling None values"""
    try:
        if ts is None:
            return 'N/A'
        return datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return 'N/A'

print("=" * 100)
print("5M BOT DETAILED ANALYSIS - CURRENT STATUS")
print("=" * 100)

# 1. Order Intents Analysis
print("\n📋 ORDER INTENTS ANALYSIS")
print("-" * 100)
intent_path = Path('paper_trading_outputs/5m/logs/order_intent/date=2026-01-14/order_intent.jsonl')
if intent_path.exists():
    with open(intent_path) as f:
        intents = [json.loads(line) for line in f]
    
    print(f"Total order intents on Jan 14: {len(intents)}")
    
    if len(intents) > 0:
        df_intent = pd.DataFrame(intents)
        
        # Decision breakdown
        if 'decision' in df_intent.columns:
            print(f"\n🚦 Decision Breakdown:")
            for decision, count in df_intent['decision'].value_counts().items():
                print(f"  {decision}: {count} ({count/len(df_intent)*100:.1f}%)")
        
        # Veto reasons
        if 'veto_reason_primary' in df_intent.columns:
            vetoed = df_intent[df_intent['decision'] == 'VETO']
            if len(vetoed) > 0:
                print(f"\n🛑 Veto Reasons (Top 10):")
                for reason, count in vetoed['veto_reason_primary'].value_counts().head(10).items():
                    print(f"  {reason}: {count} ({count/len(vetoed)*100:.1f}%)")
        
        # Guard details
        if 'guard_details' in df_intent.columns:
            print(f"\n🛡️ Guard Details Sample (last 5):")
            for i, guard in enumerate(df_intent['guard_details'].tail(5)):
                print(f"  [{i+1}] {guard}")
        
        # Latest intents
        print(f"\n📊 Latest 5 Order Intents:")
        for i, intent in enumerate(intents[-5:]):
            ts = safe_ts_format(intent.get('ts'))
            decision = intent.get('decision', 'N/A')
            alpha = intent.get('alpha', 0)
            veto = intent.get('veto_reason_primary', 'N/A')
            print(f"  [{i+1}] {ts} | Decision: {decision} | Alpha: {alpha:.4f} | Veto: {veto}")
else:
    print("❌ No order intent logs found for Jan 14")

# 2. Signals Analysis
print("\n\n📈 SIGNALS ANALYSIS")
print("-" * 100)
signals_path = Path('paper_trading_outputs/5m/logs/signals/date=2026-01-14/signals.jsonl')
if signals_path.exists():
    with open(signals_path) as f:
        signals = [json.loads(line) for line in f]
    
    print(f"Total signals on Jan 14: {len(signals)}")
    
    if len(signals) > 0:
        df_sig = pd.DataFrame(signals)
        
        # Alpha distribution
        if 'alpha' in df_sig.columns:
            print(f"\n📊 Alpha Distribution:")
            print(f"  Mean: {df_sig['alpha'].mean():.6f}")
            print(f"  Std: {df_sig['alpha'].std():.6f}")
            print(f"  Min: {df_sig['alpha'].min():.6f}")
            print(f"  Max: {df_sig['alpha'].max():.6f}")
            print(f"  Median: {df_sig['alpha'].median():.6f}")
            
            # Direction counts
            df_sig['direction'] = df_sig['alpha'].apply(
                lambda x: 'LONG' if x > 0.001 else ('SHORT' if x < -0.001 else 'NEUTRAL')
            )
            print(f"\n📍 Signal Direction:")
            for dir, count in df_sig['direction'].value_counts().items():
                print(f"  {dir}: {count} ({count/len(df_sig)*100:.1f}%)")
        
        # Model confidence
        if 's_model' in df_sig.columns:
            print(f"\n🎯 Model Confidence (s_model):")
            print(f"  Mean: {df_sig['s_model'].mean():.6f}")
            print(f"  Std: {df_sig['s_model'].std():.6f}")
            print(f"  Min: {df_sig['s_model'].min():.6f}")
            print(f"  Max: {df_sig['s_model'].max():.6f}")
        
        # Latest signals
        print(f"\n📊 Latest 5 Signals:")
        for i, sig in enumerate(signals[-5:]):
            ts = safe_ts_format(sig.get('ts'))
            alpha = sig.get('alpha', 0)
            s_model = sig.get('s_model', 0)
            close = sig.get('close', 0)
            print(f"  [{i+1}] {ts} | Close: ${close:.2f} | Alpha: {alpha:.6f} | S_model: {s_model:.6f}")
else:
    print("❌ No signals logs found for Jan 14")

# 3. Executions Analysis
print("\n\n💰 EXECUTIONS ANALYSIS")
print("-" * 100)
exec_path = Path('paper_trading_outputs/5m/logs/default/repro/repro.jsonl')
if exec_path.exists():
    with open(exec_path) as f:
        execs = [json.loads(line) for line in f]
    
    print(f"Total executions: {len(execs)}")
    
    if len(execs) > 0:
        df_exec = pd.DataFrame([e['repro'] for e in execs])
        
        # Side breakdown
        if 'side' in df_exec.columns:
            print(f"\n📊 Side Breakdown:")
            for side, count in df_exec['side'].value_counts().items():
                print(f"  {side}: {count} ({count/len(df_exec)*100:.1f}%)")
        
        # PnL analysis
        if 'realized_pnl' in df_exec.columns:
            print(f"\n💵 PnL Analysis:")
            print(f"  Total Realized PnL: ${df_exec['realized_pnl'].sum():.2f}")
            if 'unrealized_pnl' in df_exec.columns:
                print(f"  Last Unrealized PnL: ${df_exec['unrealized_pnl'].iloc[-1]:.2f}")
                print(f"  Total PnL: ${df_exec['realized_pnl'].sum() + df_exec['unrealized_pnl'].iloc[-1]:.2f}")
        
        # Equity tracking
        if 'equity' in df_exec.columns:
            initial_equity = df_exec['equity'].iloc[0]
            current_equity = df_exec['equity'].iloc[-1]
            total_return = (current_equity / initial_equity - 1) * 100
            print(f"\n💰 Equity:")
            print(f"  Initial: ${initial_equity:.2f}")
            print(f"  Current: ${current_equity:.2f}")
            print(f"  Return: {total_return:.2f}%")
        
        # Latest executions
        print(f"\n📊 Latest 5 Executions:")
        for i, exec in enumerate(execs[-5:]):
            repro = exec.get('repro', {})
            ts = safe_ts_format(exec.get('ts'))
            side = repro.get('side', 'N/A')
            qty = repro.get('qty', 0)
            price = repro.get('fill_price', 0)
            pnl = repro.get('realized_pnl', 0)
            print(f"  [{i+1}] {ts} | {side} {qty:.4f} @ ${price:.2f} | PnL: ${pnl:.2f}")
else:
    print("❌ No execution logs found")

# 4. Market Data Check
print("\n\n📊 MARKET DATA CHECK")
print("-" * 100)
market_path = Path('paper_trading_outputs/5m/logs/market_ingest/date=2026-01-14/market_ingest.jsonl')
if market_path.exists():
    with open(market_path) as f:
        market_data = [json.loads(line) for line in f]
    print(f"Market data entries on Jan 14: {len(market_data)}")
    
    if len(market_data) > 0:
        latest = market_data[-1]
        print(f"\n📈 Latest Market Data:")
        print(f"  Timestamp: {safe_ts_format(latest.get('ts'))}")
        print(f"  Close: ${latest.get('close', 0):.2f}")
        print(f"  Volume: {latest.get('volume', 0):.2f}")
else:
    print("❌ No market data logs found for Jan 14")

# 5. Health Check
print("\n\n🏥 HEALTH CHECK")
print("-" * 100)
health_path = Path('paper_trading_outputs/5m/logs/health/date=2026-01-14/health.jsonl')
if health_path.exists():
    with open(health_path) as f:
        health_data = [json.loads(line) for line in f]
    print(f"Health snapshots on Jan 14: {len(health_data)}")
    
    if len(health_data) > 0:
        latest = health_data[-1]
        print(f"\n📊 Latest Health Snapshot:")
        for key in ['recent_bars', 'mean_s_model', 'exec_count_recent', 'equity', 
                    'Sharpe_roll_1w', 'max_dd_to_date', 'turnover_bps_day']:
            if key in latest:
                print(f"  {key}: {latest[key]}")
else:
    print("❌ No health logs found for Jan 14")

# 6. Root Cause Summary
print("\n\n" + "=" * 100)
print("ROOT CAUSE SUMMARY")
print("=" * 100)

# Calculate key metrics
if intent_path.exists() and signals_path.exists():
    signal_count = len(signals) if signals_path.exists() else 0
    intent_count = len(intents) if intent_path.exists() else 0
    exec_count = len(execs) if exec_path.exists() else 0
    
    print(f"\n📊 Funnel Analysis:")
    print(f"  Signals Generated: {signal_count}")
    print(f"  Order Intents Created: {intent_count}")
    print(f"  Executions: {exec_count}")
    
    if signal_count > 0:
        print(f"\n  Signal → Intent Conversion: {(intent_count/signal_count*100):.2f}%")
    if intent_count > 0:
        print(f"  Intent → Execution Conversion: {(exec_count/intent_count*100):.2f}%")
    if signal_count > 0:
        print(f"  Overall Signal → Execution: {(exec_count/signal_count*100):.2f}%")
    
    # Veto analysis
    if intent_path.exists() and len(intents) > 0:
        df_intent = pd.DataFrame(intents)
        if 'decision' in df_intent.columns:
            vetoed = (df_intent['decision'] == 'VETO').sum()
            approved = (df_intent['decision'] == 'APPROVE').sum()
            
            print(f"\n🚦 Approval Analysis:")
            print(f"  Approved Intents: {approved} ({approved/intent_count*100:.1f}%)")
            print(f"  Vetoed Intents: {vetoed} ({vetoed/intent_count*100:.1f}%)")
            
            if vetoed > 0:
                print(f"\n🛑 PRIMARY ISSUE: {vetoed} intents vetoed!")
                print(f"   This is blocking {vetoed/intent_count*100:.1f}% of potential trades")

print("\n" + "=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
