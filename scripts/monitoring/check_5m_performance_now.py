"""
Check current 5m bot performance AFTER the consensus fix
"""
import pandas as pd
from datetime import datetime, timedelta

print("=" * 80)
print("5M BOT PERFORMANCE CHECK - AFTER CONSENSUS FIX")
print("=" * 80)
print()

# Check recent executions
try:
    df = pd.read_csv('paper_trading_outputs/executions_paper.csv')
    df['ts_ist'] = pd.to_datetime(df['ts_ist'])
    
    # Get today's trades
    today = datetime.now().date()
    today_trades = df[df['ts_ist'].dt.date == today]
    
    print(f"📊 Today's Trades ({today}):")
    print(f"   Total: {len(today_trades)}")
    
    if len(today_trades) > 0:
        buy_count = len(today_trades[today_trades['side'] == 'BUY'])
        sell_count = len(today_trades[today_trades['side'] == 'SELL'])
        
        print(f"   BUY: {buy_count}")
        print(f"   SELL: {sell_count}")
        print()
        
        if sell_count > 0:
            print("✅ SELL trades are working!")
        else:
            print("⚠️ Still no SELL trades")
        
        # Check if profitable
        if 'pnl' in today_trades.columns:
            total_pnl = today_trades['pnl'].sum()
            print(f"\n💰 P&L: ${total_pnl:.2f}")
            
            if total_pnl > 0:
                print("✅ PROFITABLE!")
            else:
                print("❌ STILL LOSING")
                print("\n🔍 This suggests the model may need retraining")
    
    # Get last 24 hours
    last_24h = df[df['ts_ist'] > datetime.now() - timedelta(hours=24)]
    
    print(f"\n📊 Last 24 Hours:")
    print(f"   Total: {len(last_24h)}")
    
    if len(last_24h) > 0:
        buy_count = len(last_24h[last_24h['side'] == 'BUY'])
        sell_count = len(last_24h[last_24h['side'] == 'SELL'])
        
        print(f"   BUY: {buy_count}")
        print(f"   SELL: {sell_count}")
        
        if 'pnl' in last_24h.columns:
            total_pnl = last_24h['pnl'].sum()
            wins = len(last_24h[last_24h['pnl'] > 0])
            losses = len(last_24h[last_24h['pnl'] < 0])
            
            print(f"\n💰 P&L: ${total_pnl:.2f}")
            print(f"   Wins: {wins}")
            print(f"   Losses: {losses}")
            
            if wins + losses > 0:
                win_rate = wins / (wins + losses) * 100
                print(f"   Win Rate: {win_rate:.1f}%")
                
                if win_rate < 40:
                    print("\n❌ LOW WIN RATE - Model may need retraining")
                elif total_pnl < 0:
                    print("\n⚠️ NEGATIVE P&L - Model may need retraining")
                else:
                    print("\n✅ Performance looks okay")

except FileNotFoundError:
    print("❌ No execution data found")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 80)
print("CONCLUSION:")
print("=" * 80)
print()
print("If bot is still losing AFTER consensus fix:")
print("  → Model predictions may be wrong")
print("  → Retraining IS needed")
print()
print("If bot is now profitable:")
print("  → Model is fine")
print("  → Just optimize parameters")
print()
print("=" * 80)
