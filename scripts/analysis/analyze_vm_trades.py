#!/usr/bin/env python3
"""Analyze VM trading results from the 24-hour run."""

import pandas as pd
import sys

def analyze_trades():
    """Analyze the executions from the VM."""
    try:
        # Read executions
        df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
        
        print("=" * 80)
        print("24-HOUR VM TRADING BOT STATUS REPORT")
        print("=" * 80)
        
        # Basic stats
        print(f"\n📊 TRADE STATISTICS:")
        print(f"   Total trades executed: {len(df)}")
        
        # Count by direction
        if len(df) > 0:
            buy_count = (df.iloc[:, 2] == 'BUY').sum()
            sell_count = (df.iloc[:, 2] == 'SELL').sum()
            print(f"   BUY trades: {buy_count}")
            print(f"   SELL trades: {sell_count}")
            
            # Show last few trades
            print(f"\n📈 LAST 10 TRADES:")
            print(df.tail(10).to_string())
            
            # Read equity if available
            try:
                equity_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/equity.csv')
                if len(equity_df) > 0:
                    print(f"\n💰 EQUITY STATUS:")
                    print(equity_df.tail(5).to_string())
            except Exception as e:
                print(f"\n⚠️  Could not read equity data: {e}")
        else:
            print("   ⚠️  No trades executed yet")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Error analyzing trades: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_trades()
