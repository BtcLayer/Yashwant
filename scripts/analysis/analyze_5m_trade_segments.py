"""
Phase 1: Detailed Trade Segmentation Analysis
Identify which trade cohorts are profitable vs unprofitable
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime

print("="*80)
print("PHASE 1: TRADE SEGMENTATION ANALYSIS")
print("="*80)

# Load data
print("\nLoading data...")
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print(f"Executions: {len(exec_df)}")
print(f"Signals: {len(signals_df)}")

# Extract PnL and metadata from executions
print("\nExtracting trade data...")
trades = []
for idx, row in exec_df.iterrows():
    try:
        raw_data = json.loads(row['raw'])
        
        # Parse timestamp
        ts = pd.to_datetime(row['ts_iso'], errors='coerce')
        
        trades.append({
            'ts': ts,
            'hour': ts.hour if pd.notna(ts) else None,
            'day_of_week': ts.dayofweek if pd.notna(ts) else None,
            'side': row['side'],
            'qty': float(row['qty']),
            'mid_price': float(row['mid_price']),
            'realized_pnl': float(raw_data.get('realized_pnl', 0)),
            'fee': float(raw_data.get('fee', 0)),
            'impact': float(raw_data.get('impact', 0)),
            'raw_signal': row.get('raw_signal', '{}')
        })
    except Exception as e:
        print(f"  Warning: Could not parse row {idx}: {e}")

trades_df = pd.DataFrame(trades)
print(f"Parsed {len(trades_df)} trades")

# Extract confidence and alpha from raw_signal
print("\nExtracting signal metadata...")
for idx, row in trades_df.iterrows():
    try:
        signal_data = json.loads(row['raw_signal']) if isinstance(row['raw_signal'], str) else {}
        trades_df.at[idx, 'confidence'] = signal_data.get('confidence', None)
        trades_df.at[idx, 'alpha'] = signal_data.get('alpha', None)
    except:
        trades_df.at[idx, 'confidence'] = None
        trades_df.at[idx, 'alpha'] = None

# SEGMENTATION 1: BY DIRECTION
print("\n" + "="*80)
print("SEGMENTATION 1: BY DIRECTION (LONG vs SHORT)")
print("="*80)

direction_stats = trades_df.groupby('side').agg({
    'realized_pnl': ['count', 'sum', 'mean', 'std'],
    'fee': 'sum',
    'impact': 'sum'
}).round(4)

print("\nPerformance by Direction:")
print(direction_stats)

# Calculate win rates by direction
for direction in trades_df['side'].unique():
    dir_trades = trades_df[trades_df['side'] == direction]
    wins = len(dir_trades[dir_trades['realized_pnl'] > 0])
    total = len(dir_trades)
    win_rate = wins / total if total > 0 else 0
    avg_pnl = dir_trades['realized_pnl'].mean()
    total_pnl = dir_trades['realized_pnl'].sum()
    
    print(f"\n{direction}:")
    print(f"  Trades: {total}")
    print(f"  Win Rate: {win_rate*100:.1f}%")
    print(f"  Avg PnL: ${avg_pnl:.4f}")
    print(f"  Total PnL: ${total_pnl:.2f}")
    print(f"  Expectancy: ${avg_pnl:.4f}")

# SEGMENTATION 2: BY CONFIDENCE BUCKETS
print("\n" + "="*80)
print("SEGMENTATION 2: BY CONFIDENCE BUCKETS")
print("="*80)

# Filter out null confidence values
trades_with_conf = trades_df[trades_df['confidence'].notna()].copy()

if len(trades_with_conf) > 0:
    # Create confidence buckets
    trades_with_conf['conf_bucket'] = pd.cut(
        trades_with_conf['confidence'], 
        bins=[0, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0],
        labels=['<50%', '50-55%', '55-60%', '60-65%', '65-70%', '>70%']
    )

    conf_stats = trades_with_conf.groupby('conf_bucket', observed=True).agg({
        'realized_pnl': ['count', 'sum', 'mean'],
        'confidence': 'mean'
    }).round(4)

    print("\nPerformance by Confidence Bucket:")
    print(conf_stats)

    # Calculate win rates by confidence
    for bucket in trades_with_conf['conf_bucket'].dropna().unique():
        bucket_trades = trades_with_conf[trades_with_conf['conf_bucket'] == bucket]
        wins = len(bucket_trades[bucket_trades['realized_pnl'] > 0])
        total = len(bucket_trades)
        win_rate = wins / total if total > 0 else 0
        avg_pnl = bucket_trades['realized_pnl'].mean()
        
        print(f"\n{bucket}:")
        print(f"  Trades: {total}")
        print(f"  Win Rate: {win_rate*100:.1f}%")
        print(f"  Avg PnL: ${avg_pnl:.4f}")
        print(f"  Expectancy: ${avg_pnl:.4f}")
else:
    print("\n⚠️  No confidence data available in trades")
    conf_stats = pd.DataFrame()
    trades_with_conf = trades_df.copy()
    trades_with_conf['conf_bucket'] = None

# SEGMENTATION 3: BY ALPHA BUCKETS
print("\n" + "="*80)
print("SEGMENTATION 3: BY ALPHA BUCKETS")
print("="*80)

# Filter out null alpha values
trades_with_alpha = trades_df[trades_df['alpha'].notna()].copy()

if len(trades_with_alpha) > 0:
    # Create alpha buckets
    trades_with_alpha['alpha_bucket'] = pd.cut(
        trades_with_alpha['alpha'], 
        bins=[0, 0.02, 0.03, 0.05, 0.10, 1.0],
        labels=['<2%', '2-3%', '3-5%', '5-10%', '>10%']
    )

    alpha_stats = trades_with_alpha.groupby('alpha_bucket', observed=True).agg({
        'realized_pnl': ['count', 'sum', 'mean'],
        'alpha': 'mean'
    }).round(4)

    print("\nPerformance by Alpha Bucket:")
    print(alpha_stats)
else:
    print("\n⚠️  No alpha data available in trades")
    alpha_stats = pd.DataFrame()

# SEGMENTATION 4: BY HOUR OF DAY
print("\n" + "="*80)
print("SEGMENTATION 4: BY HOUR OF DAY")
print("="*80)

hourly_stats = trades_df.groupby('hour').agg({
    'realized_pnl': ['count', 'sum', 'mean']
}).round(4)

print("\nTop 5 Most Profitable Hours:")
top_hours = hourly_stats.sort_values(('realized_pnl', 'sum'), ascending=False).head(5)
print(top_hours)

print("\nTop 5 Least Profitable Hours:")
bottom_hours = hourly_stats.sort_values(('realized_pnl', 'sum'), ascending=True).head(5)
print(bottom_hours)

# SEGMENTATION 5: BY DAY OF WEEK
print("\n" + "="*80)
print("SEGMENTATION 5: BY DAY OF WEEK")
print("="*80)

day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
trades_df['day_name'] = trades_df['day_of_week'].apply(lambda x: day_names[int(x)] if pd.notna(x) and 0 <= x < 7 else 'Unknown')

daily_stats = trades_df.groupby('day_name').agg({
    'realized_pnl': ['count', 'sum', 'mean']
}).round(4)

print("\nPerformance by Day of Week:")
print(daily_stats)

# KEY FINDINGS
print("\n" + "="*80)
print("KEY FINDINGS FROM SEGMENTATION")
print("="*80)

findings = []

# Finding 1: Direction bias
buy_pnl = trades_df[trades_df['side'] == 'BUY']['realized_pnl'].sum()
sell_pnl = trades_df[trades_df['side'] == 'SELL']['realized_pnl'].sum()

if abs(buy_pnl) > abs(sell_pnl) * 2 or abs(sell_pnl) > abs(buy_pnl) * 2:
    worse_direction = 'BUY' if buy_pnl < sell_pnl else 'SELL'
    findings.append(f"1. DIRECTIONAL BIAS DETECTED")
    findings.append(f"   {worse_direction} trades are significantly worse")
    findings.append(f"   Recommendation: Raise CONF_MIN for {worse_direction} trades")

# Finding 2: Confidence correlation
if len(trades_with_conf) > 0:
    conf_corr = trades_with_conf[['confidence', 'realized_pnl']].corr().iloc[0, 1]
else:
    conf_corr = None
    
if pd.notna(conf_corr):
    if conf_corr < 0:
        findings.append(f"2. NEGATIVE CONFIDENCE CORRELATION ({conf_corr:.3f})")
        findings.append(f"   Higher confidence trades perform WORSE")
        findings.append(f"   🔴 CRITICAL: Model calibration is broken")
    elif conf_corr < 0.1:
        findings.append(f"2. NO CONFIDENCE CORRELATION ({conf_corr:.3f})")
        findings.append(f"   Confidence is not predictive of performance")
        findings.append(f"   Recommendation: Recalibrate model or use different threshold")
    else:
        findings.append(f"2. POSITIVE CONFIDENCE CORRELATION ({conf_corr:.3f})")
        findings.append(f"   Higher confidence trades perform better")
        findings.append(f"   Recommendation: Implement confidence bands")
else:
    findings.append(f"2. NO CONFIDENCE DATA AVAILABLE")
    findings.append(f"   Cannot analyze confidence correlation")
    conf_corr = None

# Finding 3: Best confidence bucket
if len(conf_stats) > 0:
    best_bucket = conf_stats[('realized_pnl', 'mean')].idxmax()
    best_expectancy = conf_stats.loc[best_bucket, ('realized_pnl', 'mean')]
    findings.append(f"3. BEST CONFIDENCE BUCKET: {best_bucket}")
    findings.append(f"   Expectancy: ${best_expectancy:.4f}")
    if best_expectancy > 0:
        findings.append(f"   ✓ POSITIVE EXPECTANCY FOUND")
        findings.append(f"   Recommendation: Only trade in this bucket")

# Finding 4: Time of day patterns
if len(hourly_stats) > 0:
    best_hour = hourly_stats[('realized_pnl', 'sum')].idxmax()
    worst_hour = hourly_stats[('realized_pnl', 'sum')].idxmin()
    findings.append(f"4. TIME OF DAY PATTERNS")
    findings.append(f"   Best hour: {int(best_hour):02d}:00")
    findings.append(f"   Worst hour: {int(worst_hour):02d}:00")

for finding in findings:
    print(finding)

# RECOMMENDATIONS
print("\n" + "="*80)
print("IMMEDIATE RECOMMENDATIONS")
print("="*80)

recommendations = []

# Rec 1: Confidence threshold
if pd.notna(conf_corr) and conf_corr > 0.1:
    # Find minimum confidence for positive expectancy
    positive_buckets = conf_stats[conf_stats[('realized_pnl', 'mean')] > 0]
    if len(positive_buckets) > 0:
        # Get the lower bound of the best bucket
        best_bucket_str = str(best_bucket)
        if '>' in best_bucket_str:
            min_conf = 0.70
        elif '65-70' in best_bucket_str:
            min_conf = 0.65
        elif '60-65' in best_bucket_str:
            min_conf = 0.60
        else:
            min_conf = 0.55
        
        recommendations.append(f"1. RAISE CONF_MIN to {min_conf:.2f}")
        recommendations.append(f"   Current: 0.55")
        recommendations.append(f"   Reason: Only trades with conf > {min_conf:.2f} have positive expectancy")
    else:
        recommendations.append(f"1. 🔴 NO CONFIDENCE LEVEL HAS POSITIVE EXPECTANCY")
        recommendations.append(f"   Model needs retraining - no amount of filtering will help")

# Rec 2: Direction-specific thresholds
if 'BUY' in trades_df['side'].values and 'SELL' in trades_df['side'].values:
    buy_exp = trades_df[trades_df['side'] == 'BUY']['realized_pnl'].mean()
    sell_exp = trades_df[trades_df['side'] == 'SELL']['realized_pnl'].mean()
    
    if buy_exp < 0 and sell_exp > 0:
        recommendations.append(f"2. DISABLE BUY TRADES or raise CONF_MIN_BUY to 0.70")
        recommendations.append(f"   BUY expectancy: ${buy_exp:.4f} (negative)")
        recommendations.append(f"   SELL expectancy: ${sell_exp:.4f} (positive)")
    elif sell_exp < 0 and buy_exp > 0:
        recommendations.append(f"2. DISABLE SELL TRADES or raise CONF_MIN_SELL to 0.70")
        recommendations.append(f"   SELL expectancy: ${sell_exp:.4f} (negative)")
        recommendations.append(f"   BUY expectancy: ${buy_exp:.4f} (positive)")

# Rec 3: Time filters
if len(hourly_stats) > 0:
    worst_hours = hourly_stats[hourly_stats[('realized_pnl', 'sum')] < -10].index.tolist()
    if len(worst_hours) > 0:
        recommendations.append(f"3. AVOID TRADING IN HOURS: {[int(h) for h in worst_hours]}")
        recommendations.append(f"   These hours consistently lose money")

for rec in recommendations:
    print(rec)

# Save results
results = {
    'direction_performance': {
        'BUY': {
            'count': int(len(trades_df[trades_df['side'] == 'BUY'])),
            'total_pnl': float(buy_pnl),
            'avg_pnl': float(trades_df[trades_df['side'] == 'BUY']['realized_pnl'].mean())
        },
        'SELL': {
            'count': int(len(trades_df[trades_df['side'] == 'SELL'])),
            'total_pnl': float(sell_pnl),
            'avg_pnl': float(trades_df[trades_df['side'] == 'SELL']['realized_pnl'].mean())
        }
    },
    'confidence_correlation': float(conf_corr) if pd.notna(conf_corr) else None,
    'best_confidence_bucket': str(best_bucket) if len(conf_stats) > 0 else None,
    'recommendations': recommendations
}

with open('5m_trade_segmentation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "="*80)
print("Analysis complete. Results saved to: 5m_trade_segmentation_results.json")
print("="*80)
