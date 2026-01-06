import pandas as pd

try:
    eq = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/equity.csv').tail(1).iloc[0]
    initial_balance = 10000.0  # Assumed start
    current_balance = eq['equity']
    unrealized = eq['unrealized']
    realized = eq['realized']
    position = eq['paper_qty']
    
    print(f"📊 LIVE STATUS REPORT (Model V2)")
    print(f"--------------------------------")
    print(f"💰 Balance:    ${current_balance:,.2f} (Started: ${initial_balance:,.0f})")
    print(f"📈 Net Change: {current_balance - initial_balance:+.2f} USD")
    print(f"--------------------------------")
    print(f"🟢 Active Position: {position:.4f} BTC")
    print(f"📝 Unrealized PnL: ${unrealized:+.2f}")
    print(f"💵 Realized PnL:   ${realized:+.2f} (Fees/Closed)")
    
    if position > 0:
        print(f"\n🚀 STATUS: IN TRADE (LONG)")
    elif position < 0:
        print(f"\n🔻 STATUS: IN TRADE (SHORT)")
    else:
        print(f"\n💤 STATUS: FLAT (Searching...)")

except Exception as e:
    print(f"Error: {e}")
