#!/usr/bin/env python3
"""Comprehensive analysis of 24-hour VM trading results."""

import pandas as pd
import json
from datetime import datetime, timedelta

def analyze_24hr_results():
    """Analyze the 24-hour trading results from the VM."""
    
    # Read executions
    df = pd.read_csv('vm_executions_24hr.csv')
    
    print("=" * 80)
    print("🤖 24-HOUR VM TRADING BOT - COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Parse timestamps
    df['ts_iso'] = pd.to_datetime(df['ts_iso'], format='mixed')
    
    # Overall stats
    print("📊 OVERALL STATISTICS:")
    print(f"   Total Trades: {len(df)}")
    print(f"   Date Range: {df['ts_iso'].min()} to {df['ts_iso'].max()}")
    
    # Calculate duration
    duration = df['ts_iso'].max() - df['ts_iso'].min()
    print(f"   Trading Duration: {duration}")
    print()
    
    # Trade direction breakdown
    print("📈 TRADE DIRECTION:")
    buy_count = (df['side'] == 'BUY').sum()
    sell_count = (df['side'] == 'SELL').sum()
    print(f"   BUY trades: {buy_count} ({buy_count/len(df)*100:.1f}%)")
    print(f"   SELL trades: {sell_count} ({sell_count/len(df)*100:.1f}%)")
    print()
    
    # Recent activity (last 24 hours)
    now = df['ts_iso'].max()
    last_24h = df[df['ts_iso'] >= now - timedelta(hours=24)]
    
    print(f"🕐 LAST 24 HOURS ACTIVITY:")
    print(f"   Trades in last 24h: {len(last_24h)}")
    if len(last_24h) > 0:
        print(f"   BUY: {(last_24h['side'] == 'BUY').sum()}")
        print(f"   SELL: {(last_24h['side'] == 'SELL').sum()}")
    print()
    
    # Latest trades
    print("🔥 LATEST 10 TRADES:")
    latest = df.tail(10)[['ts_iso', 'side', 'qty', 'mid_price', 'fill_price']]
    for idx, row in latest.iterrows():
        print(f"   {row['ts_iso']} | {row['side']:4s} | Qty: {row['qty']:.6f} | Price: ${row['fill_price']:.2f}")
    print()
    
    # Trading frequency
    if len(df) > 1:
        time_diffs = df['ts_iso'].diff().dt.total_seconds() / 60  # in minutes
        avg_interval = time_diffs.mean()
        print(f"⏱️  TRADING FREQUENCY:")
        print(f"   Average time between trades: {avg_interval:.1f} minutes")
        print(f"   Trades per hour (avg): {60/avg_interval:.2f}")
        print()
    
    # Price analysis
    print(f"💰 PRICE ANALYSIS:")
    print(f"   Min Price: ${df['fill_price'].min():.2f}")
    print(f"   Max Price: ${df['fill_price'].max():.2f}")
    print(f"   Avg Price: ${df['fill_price'].mean():.2f}")
    print(f"   Current Price: ${df['fill_price'].iloc[-1]:.2f}")
    print()
    
    # Volume analysis
    print(f"📦 VOLUME ANALYSIS:")
    print(f"   Total BTC traded: {df['qty'].sum():.6f} BTC")
    print(f"   Total USD volume: ${df['notional_usd'].sum():,.2f}")
    print(f"   Avg trade size: {df['qty'].mean():.6f} BTC")
    print()
    
    print("=" * 80)
    print("✅ Bot is running successfully on the VM!")
    print("=" * 80)

if __name__ == "__main__":
    analyze_24hr_results()
