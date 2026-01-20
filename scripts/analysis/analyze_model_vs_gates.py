"""
Analyze model predictions to see if the model is working or if gates are blocking it
"""
import pandas as pd
import json
from datetime import datetime

print("=" * 70)
print("MODEL PREDICTION ANALYSIS - Is the model working?")
print("=" * 70)

# Load signals (model predictions)
try:
    signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    signals['ts_dt'] = pd.to_datetime(signals['ts'], unit='ms')
    
    # Focus on recent data (last 24 hours)
    recent_cutoff = pd.to_datetime('2026-01-04 15:00:00')
    recent = signals[signals['ts_dt'] >= recent_cutoff].copy()
    
    print(f"\n📊 SIGNAL DATA:")
    print(f"   Total signals in file: {len(signals)}")
    print(f"   Recent signals (since Jan 4, 15:00): {len(recent)}")
    
    if len(recent) > 0:
        print(f"\n📈 MODEL PREDICTIONS (Recent):")
        print(f"   Average p_up: {recent['p_up'].mean():.4f}")
        print(f"   Average p_down: {recent['p_down'].mean():.4f}")
        print(f"   Average p_neutral: {recent['p_neutral'].mean():.4f}")
        
        # Calculate alpha (signal strength)
        recent['alpha'] = abs(recent['p_up'] - recent['p_down'])
        recent['conf'] = recent[['p_up', 'p_down', 'p_neutral']].max(axis=1)
        
        print(f"\n🎯 SIGNAL STRENGTH:")
        print(f"   Average alpha (|p_up - p_down|): {recent['alpha'].mean():.4f}")
        print(f"   Max alpha: {recent['alpha'].max():.4f}")
        print(f"   Min alpha: {recent['alpha'].min():.4f}")
        print(f"   Average confidence: {recent['conf'].mean():.4f}")
        
        # Check against our gates
        print(f"\n🚪 GATE ANALYSIS:")
        
        # Net Edge Gate (alpha * 50.0 > 8.0)
        recent['edge_bps'] = recent['alpha'] * 50.0
        recent['net_edge'] = recent['edge_bps'] - 8.0  # 8 bps hurdle
        pass_net_edge = (recent['net_edge'] > 0).sum()
        
        print(f"   Net Edge Gate (need alpha > 0.16):")
        print(f"     - Signals passing: {pass_net_edge}/{len(recent)} ({pass_net_edge/len(recent)*100:.1f}%)")
        print(f"     - Average edge: {recent['edge_bps'].mean():.2f} bps")
        print(f"     - Average net edge: {recent['net_edge'].mean():.2f} bps")
        
        # Confidence Gate (CONF_MIN = 0.60)
        pass_conf = (recent['conf'] >= 0.60).sum()
        print(f"\n   Confidence Gate (need conf >= 0.60):")
        print(f"     - Signals passing: {pass_conf}/{len(recent)} ({pass_conf/len(recent)*100:.1f}%)")
        
        # Combined (both gates)
        pass_both = ((recent['net_edge'] > 0) & (recent['conf'] >= 0.60)).sum()
        print(f"\n   BOTH Gates (Net Edge AND Confidence):")
        print(f"     - Signals passing: {pass_both}/{len(recent)} ({pass_both/len(recent)*100:.1f}%)")
        
        # Show some examples
        print(f"\n📋 RECENT SIGNAL EXAMPLES (Last 10):")
        display_cols = ['ts_dt', 'p_up', 'p_down', 'alpha', 'edge_bps', 'net_edge', 'conf']
        print(recent[display_cols].tail(10).to_string(index=False))
        
        # Check if model changed on Jan 3
        print(f"\n🔄 MODEL CHANGE ANALYSIS:")
        jan3 = pd.to_datetime('2026-01-03 00:00:00')
        before_jan3 = signals[signals['ts_dt'] < jan3]
        after_jan3 = signals[signals['ts_dt'] >= jan3]
        
        if len(before_jan3) > 0 and len(after_jan3) > 0:
            before_jan3['alpha'] = abs(before_jan3['p_up'] - before_jan3['p_down'])
            after_jan3['alpha'] = abs(after_jan3['p_up'] - after_jan3['p_down'])
            
            print(f"   Before Jan 3 (old model):")
            print(f"     - Avg alpha: {before_jan3['alpha'].mean():.4f}")
            print(f"     - Avg edge: {before_jan3['alpha'].mean() * 50:.2f} bps")
            
            print(f"   After Jan 3 (new model):")
            print(f"     - Avg alpha: {after_jan3['alpha'].mean():.4f}")
            print(f"     - Avg edge: {after_jan3['alpha'].mean() * 50:.2f} bps")
            
            improvement = (after_jan3['alpha'].mean() - before_jan3['alpha'].mean()) * 50
            print(f"   Change: {improvement:+.2f} bps")
        
    else:
        print("   ⚠️  No recent signals found!")
        
except FileNotFoundError:
    print("\n❌ signals.csv not found!")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)

if len(recent) > 0:
    avg_net_edge = recent['net_edge'].mean()
    pass_rate = pass_both / len(recent) * 100 if len(recent) > 0 else 0
    
    if avg_net_edge < 0:
        print("\n❌ MODEL IS TOO WEAK:")
        print(f"   - Average net edge is NEGATIVE ({avg_net_edge:.2f} bps)")
        print(f"   - The model cannot beat the 8 bps cost hurdle")
        print(f"   - Only {pass_rate:.1f}% of signals would pass both gates")
        print("\n   RECOMMENDATION: The model needs retraining or the scaler needs adjustment")
    elif pass_rate < 10:
        print("\n⚠️  GATES ARE TOO STRICT:")
        print(f"   - Model has positive edge ({avg_net_edge:.2f} bps)")
        print(f"   - But only {pass_rate:.1f}% of signals pass both gates")
        print("\n   RECOMMENDATION: Relax the Net Edge scaler from 50.0 to 40.0")
    else:
        print("\n✅ MODEL IS WORKING:")
        print(f"   - Average net edge: {avg_net_edge:.2f} bps")
        print(f"   - {pass_rate:.1f}% of signals pass both gates")
        print("\n   RECOMMENDATION: Wait for the next strong signal")

print("\n" + "=" * 70)
