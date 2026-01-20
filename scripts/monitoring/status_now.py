import pandas as pd
from datetime import datetime

print("="*80)
print(f"CURRENT STATUS - {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

try:
    exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    
    # Execution stats
    total_exec = len(exec_df)
    buy_count = (exec_df['side'] == 'BUY').sum()
    sell_count = (exec_df['side'] == 'SELL').sum()
    
    # Signal stats
    dir_counts = signals_df['dir'].value_counts()
    total_signals = len(signals_df)
    dir_buy = dir_counts.get(1, 0)
    dir_sell = dir_counts.get(-1, 0)
    dir_neutral = dir_counts.get(0, 0)
    
    # Model predictions
    s_model_pos = (signals_df['s_model'] > 0).sum()
    s_model_neg = (signals_df['s_model'] < 0).sum()
    
    print(f"\n📊 EXECUTIONS:")
    print(f"   Total: {total_exec}")
    print(f"   BUY:   {buy_count} ({buy_count/max(1,total_exec)*100:.1f}%)")
    print(f"   SELL:  {sell_count} ({sell_count/max(1,total_exec)*100:.1f}%) {'✅ FIX WORKING!' if sell_count > 0 else '⏳ Waiting...'}")
    
    print(f"\n📡 SIGNALS:")
    print(f"   Total: {total_signals}")
    print(f"   dir = +1 (BUY):  {dir_buy} ({dir_buy/max(1,total_signals)*100:.1f}%)")
    print(f"   dir = -1 (SELL): {dir_sell} ({dir_sell/max(1,total_signals)*100:.1f}%) {'✅ Generating!' if dir_sell > 0 else '⏳ Waiting...'}")
    print(f"   dir = 0 (NEUT):  {dir_neutral} ({dir_neutral/max(1,total_signals)*100:.1f}%)")
    
    print(f"\n🤖 MODEL PREDICTIONS:")
    print(f"   UP (s_model > 0):   {s_model_pos} ({s_model_pos/max(1,total_signals)*100:.1f}%)")
    print(f"   DOWN (s_model < 0): {s_model_neg} ({s_model_neg/max(1,total_signals)*100:.1f}%)")
    
    print(f"\n📈 LAST 5 SIGNALS:")
    recent = signals_df.tail(5)
    for idx, row in recent.iterrows():
        direction = "BUY" if row['dir'] == 1 else ("SELL" if row['dir'] == -1 else "NEUT")
        s_model = row['s_model']
        ts = row['ts_iso'][-8:] if len(row['ts_iso']) > 8 else row['ts_iso']
        print(f"   {ts}: s_model={s_model:+.4f} → {direction}")
    
    print(f"\n🎯 STATUS:")
    if sell_count > 0:
        print(f"   ✅ SUCCESS! SELL trades are happening!")
        print(f"   ✅ Fix is confirmed working!")
    elif dir_sell > 0:
        print(f"   ⏳ SELL signals generated but not executed yet")
        print(f"   ⚠️  May need to check execution logic")
    elif s_model_neg > 0:
        print(f"   ⏳ Model predicting DOWN but no SELL signals")
        print(f"   ⚠️  Consensus may still be blocking (check config)")
    else:
        print(f"   ⏳ Waiting for model to predict DOWN...")
        print(f"   ℹ️  This is normal - model hasn't seen DOWN conditions yet")
    
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
