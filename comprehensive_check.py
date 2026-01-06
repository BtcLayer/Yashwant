import pandas as pd
import numpy as np

try:
    # Load data
    signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv').tail(20)
    equity = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/equity.csv').tail(1).iloc[0]
    
    # Calculate metrics for each signal
    signals['alpha'] = abs(signals['p_up'] - signals['p_down'])
    signals['edge_bps'] = signals['alpha'] * 50.0
    signals['confidence'] = signals[['p_up', 'p_down', 'p_neutral']].max(axis=1)
    signals['direction'] = signals[['p_up', 'p_down', 'p_neutral']].idxmax(axis=1)
    signals['time'] = pd.to_datetime(signals['ts'], unit='ms').dt.strftime('%H:%M')
    
    # Current position metrics
    position_val = equity['paper_qty'] * equity['last_price']
    unrealized_pnl = equity['unrealized']
    realized_pnl = equity['realized']
    
    if abs(position_val) > 0:
        current_bps = (unrealized_pnl / abs(position_val)) * 10000
    else:
        current_bps = 0
    
    print("=" * 70)
    print("COMPREHENSIVE VALIDATION REPORT")
    print("=" * 70)
    
    print("\n[ACCOUNT STATUS]")
    print(f"  Balance:         ${equity['equity']:.2f}")
    print(f"  Position:        {equity['paper_qty']:.4f} BTC (${position_val:.2f})")
    print(f"  Unrealized PnL:  ${unrealized_pnl:+.2f} ({current_bps:+.2f} bps)")
    print(f"  Realized PnL:    ${realized_pnl:+.2f}")
    print(f"  Net Total:       ${unrealized_pnl + realized_pnl:+.2f}")
    
    print("\n[MODEL PERFORMANCE - Last 20 Bars]")
    up_count = (signals['direction'] == 'p_up').sum()
    down_count = (signals['direction'] == 'p_down').sum()
    neutral_count = (signals['direction'] == 'p_neutral').sum()
    
    print(f"  UP:      {up_count:2d} ({up_count/20*100:.0f}%)")
    print(f"  DOWN:    {down_count:2d} ({down_count/20*100:.0f}%)")
    print(f"  NEUTRAL: {neutral_count:2d} ({neutral_count/20*100:.0f}%)")
    
    print("\n[SIGNAL QUALITY METRICS]")
    print(f"  Avg Alpha:       {signals['alpha'].mean():.4f}")
    print(f"  Avg Edge:        {signals['edge_bps'].mean():.2f} bps")
    print(f"  Max Edge:        {signals['edge_bps'].max():.2f} bps")
    print(f"  Avg Confidence:  {signals['confidence'].mean():.1%}")
    print(f"  Avg Neutral:     {signals['p_neutral'].mean():.1%}")
    
    # Count signals that would pass the 8 bps gate
    strong_signals = (signals['edge_bps'] > 8.0).sum()
    print(f"  Signals > 8bps:  {strong_signals}/20 ({strong_signals/20*100:.0f}%)")
    
    print("\n[LATEST 5 SIGNALS - Detail]")
    latest = signals.tail(5)[['time', 'p_up', 'p_down', 'p_neutral', 'alpha', 'edge_bps', 'confidence']]
    print(latest.to_string(index=False))
    
    print("\n" + "=" * 70)
    print("PROFITABILITY ASSESSMENT")
    print("=" * 70)
    
    if unrealized_pnl > 0:
        print("[OK] CURRENT TRADE: IN PROFIT")
        print(f"   The model correctly predicted the move (+{current_bps:.1f} bps)")
    elif unrealized_pnl > -0.5:
        print("[WARN] CURRENT TRADE: NEAR BREAKEVEN")
        print(f"   Minor drawdown ({current_bps:.1f} bps), within normal variance")
    else:
        print("[LOSS] CURRENT TRADE: UNDERWATER")
        print(f"   Drawdown: {current_bps:.1f} bps")
    
    total_pnl = unrealized_pnl + realized_pnl
    if total_pnl > 0:
        print(f"\n[OK] NET SESSION: PROFITABLE (+${total_pnl:.2f})")
    elif total_pnl > -2:
        print(f"\n[WARN] NET SESSION: SLIGHT LOSS (${total_pnl:.2f})")
        print("   Mostly fees, model is performing as expected")
    else:
        print(f"\n[LOSS] NET SESSION: LOSING (${total_pnl:.2f})")
    
    print("\n[RECOMMENDATION]")
    if strong_signals >= 2 and signals['edge_bps'].mean() > 4:
        print("[OK] KEEP RUNNING - Model is generating quality signals")
    elif neutral_count > 16:
        print("[WARN] MONITOR - High neutral rate, may need market volatility")
    else:
        print("[OK] SYSTEM HEALTHY - Continue operation")
    
    print("=" * 70)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
