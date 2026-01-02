"""
Quick Status Check - Run this anytime to see current progress
"""

import pandas as pd
from datetime import datetime

print("="*80)
print(f"QUICK STATUS CHECK - {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

try:
    # Load data
    exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    
    # Execution stats
    total_exec = len(exec_df)
    buy_count = (exec_df['side'] == 'BUY').sum()
    sell_count = (exec_df['side'] == 'SELL').sum()
    
    # Signal stats
    dir_counts = signals_df['dir'].value_counts()
    dir_sell = dir_counts.get(-1, 0)
    
    # Model predictions
    s_model_neg = (signals_df['s_model'] < 0).sum()
    
    print(f"\n📊 CURRENT STATUS:")
    print(f"   Total executions: {total_exec}")
    print(f"   BUY trades:  {buy_count}")
    print(f"   SELL trades: {sell_count} {'✅ FIX WORKING!' if sell_count > 0 else '⏳'}")
    
    print(f"\n📡 SIGNALS:")
    print(f"   SELL signals (dir=-1): {dir_sell}")
    print(f"   DOWN predictions (s_model<0): {s_model_neg}")
    
    # Recent activity
    recent_signals = signals_df.tail(5)
    print(f"\n📈 LAST 5 SIGNALS:")
    for idx, row in recent_signals.iterrows():
        direction = "BUY" if row['dir'] == 1 else ("SELL" if row['dir'] == -1 else "NEUT")
        s_model = row['s_model']
        print(f"   {row['ts_iso'][-8:]}: s_model={s_model:+.4f} → {direction}")
    
    if sell_count > 0:
        print(f"\n✅ SUCCESS! SELL trades are happening!")
        sell_trades = exec_df[exec_df['side'] == 'SELL'].tail(3)
        print(f"\n   Recent SELL trades:")
        for idx, row in sell_trades.iterrows():
            print(f"   {row['ts_iso'][-8:]}: SELL {row['qty']:.6f}")
    elif dir_sell > 0:
        print(f"\n⏳ SELL signals exist but not executed yet")
    elif s_model_neg > 0:
        print(f"\n⏳ Model predicting DOWN but consensus may be blocking")
        print(f"   (This shouldn't happen with fix - check config)")
    else:
        print(f"\n⏳ Waiting for model to predict DOWN...")
    
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("   Bot may not be running")

print("\nRun again anytime: python quick_status.py")
print("="*80)
