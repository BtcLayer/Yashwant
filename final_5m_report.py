#!/usr/bin/env python3
"""
5M BOT COMPREHENSIVE STATUS REPORT
Analyzes trading activity, profitability, and root causes
"""

import json
import pandas as pd
from pathlib import Path

def main():
    print("\n" + "="*100)
    print(" 5M BOT COMPREHENSIVE STATUS ANALYSIS ".center(100, "="))
    print("="*100 + "\n")
    
    # Paths
    base_path = Path('paper_trading_outputs/5m/logs')
    order_intent_file = base_path / 'order_intent/date=2026-01-14/order_intent.jsonl'
    signals_file = base_path / 'signals/date=2026-01-14/signals.jsonl'
    repro_file = base_path / 'default/repro/repro.jsonl'
    
    # 1. LOAD DATA
    print("[*] LOADING DATA...")
    
    # Order intents
    intents = []
    if order_intent_file.exists():
        with open(order_intent_file) as f:
            for line in f:
                try:
                    intents.append(json.loads(line))
                except:
                    pass
    
    # Signals
    signals = []
    if signals_file.exists():
        with open(signals_file) as f:
            for line in f:
                try:
                    signals.append(json.loads(line))
                except:
                    pass
    
    # Executions
    executions = []
    if repro_file.exists():
        with open(repro_file) as f:
            for line in f:
                try:
                    executions.append(json.loads(line))
                except:
                    pass
    
    print(f"[+] Loaded {len(intents)} intents, {len(signals)} signals, {len(executions)} executions\n")
    
    # 2. ORDER INTENTS ANALYSIS
    print("="*100)
    print(" ORDER INTENTS ANALYSIS ".center(100, "="))
    print("="*100)
    
    if intents:
        df_intent = pd.DataFrame(intents)
        print(f"\n[*] Total Order Intents: {len(intents)}")
        
        # Decision breakdown
        if 'decision' in df_intent.columns:
            print(f"\n[*] DECISION BREAKDOWN:")
            decisions = df_intent['decision'].value_counts()
            for decision, count in decisions.items():
                pct = (count / len(intents)) * 100
                print(f"   {decision:15s}: {count:4d} ({pct:5.1f}%)")
        
        # Veto reasons
        if 'veto_reason_primary' in df_intent.columns:
            vetoed_df = df_intent[df_intent['decision'] == 'VETO']
            if len(vetoed_df) > 0:
                print(f"\n[!] TOP VETO REASONS:")
                veto_reasons = vetoed_df['veto_reason_primary'].value_counts().head(10)
                for reason, count in veto_reasons.items():
                    pct = (count / len(vetoed_df)) * 100
                    print(f"   {reason:40s}: {count:4d} ({pct:5.1f}%)")
    else:
        print("\n[X] No order intent data found")
    
    # 3. SIGNALS ANALYSIS
    print("\n" + "="*100)
    print(" SIGNALS ANALYSIS ".center(100, "="))
    print("="*100)
    
    if signals:
        df_sig = pd.DataFrame(signals)
        print(f"\n[*] Total Signals: {len(signals)}")
        
        if 'alpha' in df_sig.columns:
            print(f"\n[*] ALPHA DISTRIBUTION:")
            print(f"   Mean:   {df_sig['alpha'].mean():10.6f}")
            print(f"   Std:    {df_sig['alpha'].std():10.6f}")
            print(f"   Min:    {df_sig['alpha'].min():10.6f}")
            print(f"   Max:    {df_sig['alpha'].max():10.6f}")
            print(f"   Median: {df_sig['alpha'].median():10.6f}")
            
            # Direction distribution
            df_sig['direction'] = df_sig['alpha'].apply(
                lambda x: 'LONG' if x > 0.001 else ('SHORT' if x < -0.001 else 'NEUTRAL')
            )
            print(f"\n[*] SIGNAL DIRECTION:")
            for direction, count in df_sig['direction'].value_counts().items():
                pct = (count / len(signals)) * 100
                print(f"   {direction:10s}: {count:4d} ({pct:5.1f}%)")
        
        if 's_model' in df_sig.columns:
            print(f"\n[*] MODEL CONFIDENCE (s_model):")
            print(f"   Mean: {df_sig['s_model'].mean():10.6f}")
            print(f"   Std:  {df_sig['s_model'].std():10.6f}")
            print(f"   Min:  {df_sig['s_model'].min():10.6f}")
            print(f"   Max:  {df_sig['s_model'].max():10.6f}")
    else:
        print("\n[X] No signals data found")
    
    # 4. EXECUTIONS & PNL ANALYSIS
    print("\n" + "="*100)
    print(" EXECUTIONS & PNL ANALYSIS ".center(100, "="))
    print("="*100)
    
    if executions:
        repros = [e.get('repro', {}) for e in executions]
        df_exec = pd.DataFrame(repros)
        print(f"\n[*] Total Executions: {len(executions)}")
        
        if 'side' in df_exec.columns:
            print(f"\n[*] SIDE BREAKDOWN:")
            for side, count in df_exec['side'].value_counts().items():
                pct = (count / len(executions)) * 100
                print(f"   {side:10s}: {count:4d} ({pct:5.1f}%)")
        
        if 'realized_pnl' in df_exec.columns and 'unrealized_pnl' in df_exec.columns:
            total_realized = df_exec['realized_pnl'].sum()
            last_unrealized = df_exec['unrealized_pnl'].iloc[-1] if len(df_exec) > 0 else 0
            total_pnl = total_realized + last_unrealized
            
            print(f"\n[*] PNL SUMMARY:")
            print(f"   Total Realized PnL:   ${total_realized:10.2f}")
            print(f"   Last Unrealized PnL:  ${last_unrealized:10.2f}")
            print(f"   Total PnL:            ${total_pnl:10.2f}")
        
        if 'equity' in df_exec.columns and len(df_exec) > 0:
            initial_equity = df_exec['equity'].iloc[0]
            current_equity = df_exec['equity'].iloc[-1]
            total_return = ((current_equity / initial_equity) - 1) * 100
            
            print(f"\n[*] EQUITY TRACKING:")
            print(f"   Initial Equity:  ${initial_equity:10.2f}")
            print(f"   Current Equity:  ${current_equity:10.2f}")
            print(f"   Total Return:    {total_return:10.2f}%")
    else:
        print("\n[X] No execution data found")
    
    # 5. ROOT CAUSE ANALYSIS
    print("\n" + "="*100)
    print(" ROOT CAUSE ANALYSIS ".center(100, "="))
    print("="*100)
    
    signal_count = len(signals)
    intent_count = len(intents)
    exec_count = len(executions)
    
    print(f"\n[*] TRADING FUNNEL:")
    print(f"   Signals Generated:     {signal_count:5d}")
    print(f"   Order Intents Created: {intent_count:5d} ({(intent_count/signal_count*100) if signal_count > 0 else 0:5.1f}% of signals)")
    print(f"   Executions:            {exec_count:5d} ({(exec_count/intent_count*100) if intent_count > 0 else 0:5.1f}% of intents)")
    print(f"   Overall Conversion:              ({(exec_count/signal_count*100) if signal_count > 0 else 0:5.1f}% of signals)")
    
    if intents:
        df_intent = pd.DataFrame(intents)
        if 'decision' in df_intent.columns:
            vetoed = (df_intent['decision'] == 'VETO').sum()
            approved = (df_intent['decision'] == 'APPROVE').sum()
            
            print(f"\n[*] APPROVAL RATE:")
            print(f"   Approved Intents: {approved:5d} ({(approved/intent_count*100):5.1f}%)")
            print(f"   Vetoed Intents:   {vetoed:5d} ({(vetoed/intent_count*100):5.1f}%)")
            
            if vetoed > 0:
                print(f"\n[!] PRIMARY ISSUE IDENTIFIED:")
                print(f"   {vetoed} order intents are being VETOED ({(vetoed/intent_count*100):.1f}%)")
                print(f"   This is preventing trades from executing!")
                
                # Show top veto reasons
                if 'veto_reason_primary' in df_intent.columns:
                    vetoed_df = df_intent[df_intent['decision'] == 'VETO']
                    top_reason = vetoed_df['veto_reason_primary'].value_counts().iloc[0]
                    top_reason_name = vetoed_df['veto_reason_primary'].value_counts().index[0]
                    print(f"\n   Top Veto Reason: {top_reason_name} ({top_reason} occurrences)")
    
    # 6. PROFITABILITY ANALYSIS
    print("\n" + "="*100)
    print(" PROFITABILITY ANALYSIS ".center(100, "="))
    print("="*100)
    
    if executions and len(executions) > 0:
        repros = [e.get('repro', {}) for e in executions]
        df_exec = pd.DataFrame(repros)
        
        if 'equity' in df_exec.columns:
            initial = df_exec['equity'].iloc[0]
            current = df_exec['equity'].iloc[-1]
            ret_pct = ((current / initial) - 1) * 100
            
            print(f"\n[*] PERFORMANCE:")
            print(f"   Starting Balance:  ${initial:10.2f}")
            print(f"   Current Balance:   ${current:10.2f}")
            print(f"   Profit/Loss:       ${(current - initial):10.2f}")
            print(f"   Return:            {ret_pct:10.2f}%")
            
            if ret_pct < 0:
                print(f"\n[X] BOT IS UNPROFITABLE")
                print(f"   Reason: Only {exec_count} trades executed with {ret_pct:.2f}% return")
                print(f"   Root Cause: High veto rate preventing profitable trades")
            elif ret_pct < 0.1:
                print(f"\n[!] BOT IS BARELY PROFITABLE")
                print(f"   Low trading activity: Only {exec_count} executions")
    else:
        print(f"\n[X] NO TRADING ACTIVITY")
        print(f"   No executions found - bot is not trading!")
    
    # 7. SUMMARY & RECOMMENDATIONS
    print("\n" + "="*100)
    print(" SUMMARY & RECOMMENDATIONS ".center(100, "="))
    print("="*100)
    
    print(f"\n[*] KEY FINDINGS:")
    print(f"   1. Bot is generating {signal_count} signals")
    print(f"   2. Creating {intent_count} order intents ({(intent_count/signal_count*100) if signal_count > 0 else 0:.1f}% conversion)")
    print(f"   3. Only {exec_count} trades executed ({(exec_count/intent_count*100) if intent_count > 0 else 0:.1f}% of intents)")
    
    if intents:
        df_intent = pd.DataFrame(intents)
        if 'decision' in df_intent.columns:
            vetoed = (df_intent['decision'] == 'VETO').sum()
            if vetoed > intent_count * 0.5:
                print(f"\n[!] CRITICAL ISSUE:")
                print(f"   {vetoed} intents ({(vetoed/intent_count*100):.1f}%) are being vetoed!")
                print(f"   This is the PRIMARY reason for low trading activity and poor profitability")
                
                if 'veto_reason_primary' in df_intent.columns:
                    vetoed_df = df_intent[df_intent['decision'] == 'VETO']
                    top_reasons = vetoed_df['veto_reason_primary'].value_counts().head(3)
                    print(f"\n   Top 3 Veto Reasons to Fix:")
                    for i, (reason, count) in enumerate(top_reasons.items(), 1):
                        print(f"   {i}. {reason}: {count} times ({(count/vetoed*100):.1f}%)")
    
    print("\n" + "="*100)
    print(" END OF REPORT ".center(100, "="))
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
