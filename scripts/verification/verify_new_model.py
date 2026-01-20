import pandas as pd
import time

# Wait a moment to ensure file is flushed if bot just wrote to it
time.sleep(1)

try:
    df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms')

    # Get the very latest signals
    recent = df.tail(5).copy()
    recent['alpha'] = abs(recent['p_up'] - recent['p_down'])
    recent['edge_bps'] = recent['alpha'] * 50.0
    
    # Calculate Gate Pass
    # Net Edge Gate: edge > 8.0 bps (alpha > 0.16)
    recent['pass_net_edge'] = recent['edge_bps'] > 8.0

    print("=" * 70)
    print("NEW MODEL VERIFICATION REPORT")
    print("=" * 70)

    print("\nLATEST 5 SIGNALS:")
    cols = ['ts_dt', 'p_up', 'p_down', 'p_neutral', 'alpha', 'edge_bps', 'pass_net_edge']
    print(recent[cols].to_string(index=False))

    print("\n" + "-" * 70)
    
    # Stats
    avg_edge = recent['edge_bps'].mean()
    avg_neutral = recent['p_neutral'].mean()
    max_edge = recent['edge_bps'].max()

    print(f"\nSTATS (Last 5 bars):")
    print(f"  Average Edge:    {avg_edge:.2f} bps  (Target > 8.0)")
    print(f"  Max Edge:        {max_edge:.2f} bps")
    print(f"  Average Neutral: {avg_neutral*100:.1f}%")

    print("\n" + "-" * 70)
    
    # Verdict
    print("VERDICT:")
    if avg_edge > 4.0:
        print("✅ HUGE IMPROVEMENT! Edge is significantly higher.")
    elif avg_edge > 2.0:
        print("⚠️ Slight improvement, but still below 8bps hurdle.")
    else:
        print("❌ EDGE STILL WEAK. Model might need more time or tuning.")
        
    if avg_neutral < 0.50:
        print("✅ NEUTRALITY DROPPED. Model is taking a stance!")
    else:
        print(f"⚠️ STILL NEUTRAL ({avg_neutral*100:.1f}%). Model is uncertain.")

    print("=" * 70)

except Exception as e:
    print(f"Error reading signals: {e}")
