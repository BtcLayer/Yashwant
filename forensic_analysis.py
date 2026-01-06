"""
FORENSIC ANALYSIS: Current Model State Across All Timeframes
Objective: Identify exact failure modes per timeframe
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime

print("="*80)
print("FORENSIC ANALYSIS: MULTI-TIMEFRAME MODEL QUALITY")
print("="*80)

timeframes = ['5m', '1h', '12h', '24h']
results = {}

for tf in timeframes:
    print(f"\n{'='*80}")
    print(f"TIMEFRAME: {tf}")
    print(f"{'='*80}")
    
    # Check if signals exist
    signals_path = Path(f"paper_trading_outputs/{tf}/sheets_fallback/signals.csv")
    
    if not signals_path.exists():
        print(f"  [ERROR] No signals file found at {signals_path}")
        results[tf] = {'status': 'MISSING', 'error': 'No signals file'}
        continue
    
    try:
        df = pd.read_csv(signals_path)
        
        # Basic stats
        print(f"\n--- BASIC STATS ---")
        print(f"Total signals: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Check for required columns
        required_cols = ['p_up', 'p_down', 'p_neutral', 'dir', 'alpha']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            print(f"  [ERROR] Missing columns: {missing_cols}")
            results[tf] = {'status': 'INCOMPLETE', 'error': f'Missing: {missing_cols}'}
            continue
        
        # Class distribution
        print(f"\n--- CLASS DISTRIBUTION ---")
        dir_counts = df['dir'].value_counts().sort_index()
        for val, count in dir_counts.items():
            pct = count / len(df) * 100
            print(f"  dir={val}: {count:>6} ({pct:>5.1f}%)")
        
        # Probability distribution
        print(f"\n--- PROBABILITY DISTRIBUTION ---")
        print(f"  p_up:      mean={df['p_up'].mean():.4f}, std={df['p_up'].std():.4f}")
        print(f"  p_down:    mean={df['p_down'].mean():.4f}, std={df['p_down'].std():.4f}")
        print(f"  p_neutral: mean={df['p_neutral'].mean():.4f}, std={df['p_neutral'].std():.4f}")
        
        # Check if probabilities sum to 1
        prob_sum = df[['p_up', 'p_down', 'p_neutral']].sum(axis=1)
        prob_sum_ok = ((prob_sum - 1.0).abs() < 0.01).all()
        print(f"  Probabilities sum to 1: {prob_sum_ok}")
        if not prob_sum_ok:
            print(f"    [WARNING] Probability sum range: [{prob_sum.min():.4f}, {prob_sum.max():.4f}]")
        
        # Confidence analysis
        print(f"\n--- CONFIDENCE ANALYSIS ---")
        df['conf'] = df[['p_up', 'p_down']].max(axis=1)
        print(f"  Mean confidence: {df['conf'].mean():.4f}")
        print(f"  Median confidence: {df['conf'].median():.4f}")
        print(f"  Std confidence: {df['conf'].std():.4f}")
        print(f"  Min confidence: {df['conf'].min():.4f}")
        print(f"  Max confidence: {df['conf'].max():.4f}")
        
        # Threshold analysis
        thresholds = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
        print(f"\n  Signals meeting confidence thresholds:")
        for thresh in thresholds:
            count = (df['conf'] >= thresh).sum()
            pct = count / len(df) * 100
            print(f"    >= {thresh:.2f}: {count:>6} ({pct:>5.1f}%)")
        
        # Alpha analysis
        print(f"\n--- ALPHA / BPS ANALYSIS ---")
        df['alpha_calc'] = (df['p_up'] - df['p_down']).abs()
        print(f"  Alpha (|p_up - p_down|):")
        print(f"    Mean: {df['alpha_calc'].mean():.4f}")
        print(f"    Median: {df['alpha_calc'].median():.4f}")
        print(f"    Std: {df['alpha_calc'].std():.4f}")
        
        print(f"\n  Signals meeting alpha thresholds:")
        alpha_thresholds = [0.02, 0.05, 0.10, 0.15, 0.20]
        for thresh in alpha_thresholds:
            count = (df['alpha_calc'] >= thresh).sum()
            pct = count / len(df) * 100
            print(f"    >= {thresh:.2f}: {count:>6} ({pct:>5.1f}%)")
        
        # Combined eligibility
        print(f"\n--- ELIGIBILITY (CONF >= 0.60 AND ALPHA >= 0.10) ---")
        eligible = (df['conf'] >= 0.60) & (df['alpha_calc'] >= 0.10)
        print(f"  Eligible signals: {eligible.sum()} ({eligible.sum()/len(df)*100:.1f}%)")
        
        # Actual alpha column
        if 'alpha' in df.columns:
            print(f"\n  Actual 'alpha' column:")
            print(f"    Mean: {df['alpha'].mean():.6f}")
            print(f"    Non-zero: {(df['alpha'] != 0).sum()} ({(df['alpha']!=0).sum()/len(df)*100:.1f}%)")
            print(f"    Positive: {(df['alpha'] > 0).sum()}")
            print(f"    Negative: {(df['alpha'] < 0).sum()}")
        
        # Model source
        if 'model_source' in df.columns:
            print(f"\n--- MODEL SOURCE ---")
            print(df['model_source'].value_counts())
        
        # Bandit arm
        if 'bandit_arm' in df.columns:
            print(f"\n--- BANDIT ARM SELECTION ---")
            print(df['bandit_arm'].value_counts())
        
        # Store results
        results[tf] = {
            'status': 'ANALYZED',
            'total_signals': len(df),
            'neutral_pct': (df['dir']==0).sum()/len(df)*100,
            'mean_conf': df['conf'].mean(),
            'mean_alpha': df['alpha_calc'].mean(),
            'eligible_pct': eligible.sum()/len(df)*100,
            'p_neutral_mean': df['p_neutral'].mean()
        }
        
    except Exception as e:
        print(f"  [ERROR] Failed to analyze: {str(e)}")
        import traceback
        traceback.print_exc()
        results[tf] = {'status': 'ERROR', 'error': str(e)}

# Summary comparison
print(f"\n{'='*80}")
print("CROSS-TIMEFRAME COMPARISON")
print(f"{'='*80}")

print(f"\n{'Timeframe':<10} {'Status':<12} {'Signals':<10} {'Neutral%':<10} {'Conf':<8} {'Alpha':<8} {'Eligible%':<10}")
print("-"*80)
for tf in timeframes:
    r = results.get(tf, {})
    status = r.get('status', 'UNKNOWN')
    if status == 'ANALYZED':
        print(f"{tf:<10} {status:<12} {r['total_signals']:<10} {r['neutral_pct']:<10.1f} {r['mean_conf']:<8.3f} {r['mean_alpha']:<8.3f} {r['eligible_pct']:<10.1f}")
    else:
        print(f"{tf:<10} {status:<12} {r.get('error', 'N/A')}")

# Save results
with open('forensic_analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n{'='*80}")
print("Analysis complete. Results saved to forensic_analysis_results.json")
print(f"{'='*80}")
