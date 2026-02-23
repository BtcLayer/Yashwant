import pandas as pd
from pathlib import Path
import json

print("\n" + "="*80)
print("  5M BOT - COMPLETE TRADE STATUS & BALANCE REPORT")
print("="*80 + "\n")

# Read equity data
equity_file = Path('paper_trading_outputs/5m/sheets_fallback/equity.csv')
if equity_file.exists():
    df = pd.read_csv(equity_file, header=None)
    df.columns = ['timestamp', 'timestamp_ms', 'btc_price', 'paper_qty', 'paper_avg_px', 'realized_pnl', 'unrealized_pnl', 'equity']
    
    # Convert numeric columns
    numeric_cols = ['btc_price', 'paper_qty', 'paper_avg_px', 'realized_pnl', 'unrealized_pnl', 'equity']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Get latest data
    latest = df.iloc[-1]
    first = df.iloc[0]
    
    print("💰 ACCOUNT BALANCE")
    print("-" * 80)
    print(f"Starting Balance:     ${first['equity']:,.2f} USD")
    print(f"Current Balance:      ${latest['equity']:,.2f} USD")
    print(f"Total PnL:            ${latest['equity'] - first['equity']:+,.2f} USD")
    print()
    
    print("📊 POSITION STATUS")
    print("-" * 80)
    print(f"Current BTC Price:    ${latest['btc_price']:,.2f}")
    print(f"Position Size:        {latest['paper_qty']:.8f} BTC")
    
    if abs(latest['paper_qty']) > 0.0001:
        print(f"Entry Price:          ${latest['paper_avg_px']:,.2f}")
        print(f"Position Value:       ${latest['paper_qty'] * latest['btc_price']:,.2f} USD")
        print()
        print(f"Realized PnL:         ${latest['realized_pnl']:+,.2f} USD")
        print(f"Unrealized PnL:       ${latest['unrealized_pnl']:+,.2f} USD")
        print(f"Total PnL:            ${latest['realized_pnl'] + latest['unrealized_pnl']:+,.2f} USD")
        
        # Position P&L percentage
        entry_value = latest['paper_qty'] * latest['paper_avg_px']
        pnl_pct = ((latest['realized_pnl'] + latest['unrealized_pnl']) / first['equity']) * 100
        print(f"Return on Capital:    {pnl_pct:+.2f}%")
    else:
        print("Position Value:       $0.00 USD (NO POSITION)")
        print()
        print(f"Realized PnL:         ${latest['realized_pnl']:+,.2f} USD")
        print(f"Unrealized PnL:       $0.00 USD")
        print(f"Total PnL:            ${latest['realized_pnl']:+,.2f} USD")
    
    print()
    
    # Summary stats
    print("📈 TRADING SUMMARY")
    print("-" * 80)
    
    # Count position changes
    position_changes = (df['paper_qty'].diff() != 0).sum()
    print(f"Position Updates:     {position_changes}")
    
    # Max/Min equity
    max_equity = df['equity'].max()
    min_equity = df['equity'].min()
    print(f"Peak Equity:          ${max_equity:,.2f} USD")
    print(f"Lowest Equity:        ${min_equity:,.2f} USD")
    
    # Max drawdown
    df['cummax'] = df['equity'].cummax()
    df['drawdown'] = (df['equity'] - df['cummax']) / df['cummax'] * 100
    max_dd = df['drawdown'].min()
    print(f"Max Drawdown:         {max_dd:.2f}%")
    
    # Win rate calculation
    trades_with_pnl = df[df['realized_pnl'] != 0]
    if len(trades_with_pnl) > 0:
        wins = len(df[df['realized_pnl'] > 0])
        losses = len(df[df['realized_pnl'] < 0])
        total_trades = wins + losses
        if total_trades > 0:
            win_rate = (wins / total_trades) * 100
            print(f"Win Rate:             {win_rate:.1f}% ({wins}W / {losses}L)")
    
    print()
    
    # Last 10 entries
    print("📋 RECENT EQUITY HISTORY (Last 10 Bars)")
    print("-" * 80)
    recent = df.tail(10)[['timestamp', 'btc_price', 'paper_qty', 'realized_pnl', 'unrealized_pnl', 'equity']]
    for idx, row in recent.iterrows():
        ts = row['timestamp'].split('T')[0] + ' ' + row['timestamp'].split('T')[1].split('+')[0]
        print(f"{ts} | BTC: ${row['btc_price']:>8,.0f} | Pos: {row['paper_qty']:>12.8f} | " +
              f"RPnL: ${row['realized_pnl']:>8.2f} | UPnL: ${row['unrealized_pnl']:>7.2f} | " +
              f"Equity: ${row['equity']:>10,.2f}")
    print()

# Read executions data
exec_file = Path('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
if exec_file.exists():
    try:
        exec_df = pd.read_csv(exec_file, header=None)
        exec_df.columns = ['timestamp', 'timestamp_ms', 'side', 'qty', 'mid_price', 'exec_price', 
                          'target_notional', 'base_notional', 'position_fraction', 
                          'paper_qty', 'paper_avg_px', 'realized_pnl', 'unrealized_pnl', 
                          'fee', 'impact', 'equity', 'details']
        
        print("💼 EXECUTION HISTORY")
        print("-" * 80)
        print(f"Total Executions:     {len(exec_df)}")
        
        # Count by side
        buys = len(exec_df[exec_df['side'] == 'BUY'])
        sells = len(exec_df[exec_df['side'] == 'SELL'])
        print(f"Buys:                 {buys}")
        print(f"Sells:                {sells}")
        
        # Total fees and impact
        total_fees = exec_df['fee'].sum()
        total_impact = exec_df['impact'].sum()
        print(f"Total Fees:           ${total_fees:,.2f} USD")
        print(f"Total Slippage:       ${total_impact:,.2f} USD")
        print(f"Total Costs:          ${total_fees + total_impact:,.2f} USD")
        print()
        
        # Recent executions
        print("📊 RECENT EXECUTIONS (Last 10)")
        print("-" * 80)
        recent_exec = exec_df.tail(10)[['timestamp', 'side', 'qty', 'exec_price', 'realized_pnl', 'equity']]
        for idx, row in recent_exec.iterrows():
            ts = row['timestamp'].split('T')[0] + ' ' + row['timestamp'].split('T')[1].split('+')[0]
            print(f"{ts} | {row['side']:>4} | {row['qty']:>10.6f} BTC @ ${row['exec_price']:>10,.2f} | " +
                  f"RPnL: ${row['realized_pnl']:>8,.2f} | Equity: ${row['equity']:>10,.2f}")
        print()
    except Exception as e:
        print(f"⚠️  Could not parse executions: {e}\n")

# Overall assessment
print("="*80)
print("🎯 TRADE STATUS ASSESSMENT")
print("="*80)

if abs(latest['paper_qty']) > 0.0001:
    print(f"\n✅ ACTIVE POSITION: {latest['paper_qty']:.6f} BTC")
    print(f"   Entry: ${latest['paper_avg_px']:,.2f} | Current: ${latest['btc_price']:,.2f}")
    
    price_change = ((latest['btc_price'] - latest['paper_avg_px']) / latest['paper_avg_px']) * 100
    print(f"   Price Change: {price_change:+.2f}%")
    
    if latest['unrealized_pnl'] > 0:
        print(f"   Status: ✅ In Profit (+${latest['unrealized_pnl']:,.2f})")
    else:
        print(f"   Status: ⚠️  In Loss (${latest['unrealized_pnl']:,.2f})")
else:
    print("\n⚪ NO ACTIVE POSITION")
    print("   Bot is in HOLD mode - waiting for trading opportunity")

print(f"\n💰 Account Performance:")
print(f"   Starting: ${first['equity']:,.2f}")
print(f"   Current:  ${latest['equity']:,.2f}")
print(f"   Change:   ${latest['equity'] - first['equity']:+,.2f} ({((latest['equity'] - first['equity']) / first['equity'] * 100):+.2f}%)")

if latest['realized_pnl'] != 0:
    print(f"\n📊 Realized Results:")
    print(f"   Realized PnL: ${latest['realized_pnl']:+,.2f}")
    print(f"   This reflects actual closed trades")

print("\n" + "="*80)
