import pandas as pd
import json
from datetime import datetime

print("="*80)
print(f"STATUS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

try:
    exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    
    # Basic counts
    total_exec = len(exec_df)
    buy_count = (exec_df['side'] == 'BUY').sum()
    sell_count = (exec_df['side'] == 'SELL').sum()
    
    dir_sell = (signals_df['dir'] == -1).sum()
    s_model_neg = (signals_df['s_model'] < 0).sum()
    
    # P&L
    total_pnl = 0
    wins = 0
    losses = 0
    for _, row in exec_df.iterrows():
        try:
            raw = json.loads(row['raw'])
            pnl = raw.get('realized_pnl', 0)
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        except:
            pass
    
    win_rate = (wins / total_exec * 100) if total_exec > 0 else 0
    
    print(f"\n📊 EXECUTIONS:")
    print(f"   Total: {total_exec}")
    print(f"   BUY:   {buy_count}")
    print(f"   SELL:  {sell_count}")
    
    print(f"\n📡 SIGNALS:")
    print(f"   SELL signals (dir=-1): {dir_sell}")
    print(f"   DOWN predictions: {s_model_neg}")
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Win rate: {win_rate:.1f}%")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Total P&L: ${total_pnl:.2f}")
    
    print(f"\n🎯 STATUS:")
    if sell_count > 0:
        print(f"   ✅ SUCCESS! {sell_count} SELL trades executed!")
        print(f"   ✅ Fix is confirmed working!")
    elif dir_sell > 0:
        print(f"   ⏳ {dir_sell} SELL signals generated but not executed")
    elif s_model_neg > 0:
        print(f"   ⏳ Model predicted DOWN {s_model_neg} times but no SELL signals")
    else:
        print(f"   ⏳ Waiting for DOWN predictions")
    
    print("\n" + "="*80)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
