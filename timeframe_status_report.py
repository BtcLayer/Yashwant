import pandas as pd
import json

print("="*80)
print("COMPREHENSIVE TIMEFRAME STATUS REPORT")
print("="*80)

timeframes = {
    '5m': 'paper_trading_outputs/5m/sheets_fallback',
    '1h': 'paper_trading_outputs/1h/sheets_fallback',
    '12h': 'paper_trading_outputs/12h/sheets_fallback',
    '24h': 'paper_trading_outputs/24h/sheets_fallback'
}

for tf_name, path in timeframes.items():
    print(f"\n{'='*80}")
    print(f"{tf_name.upper()} TIMEFRAME")
    print("="*80)
    
    try:
        # Load signals
        signals = pd.read_csv(f'{path}/signals.csv')
        executions = pd.read_csv(f'{path}/executions_paper.csv')
        
        # Model signal analysis
        s_model_mean = signals['s_model'].mean()
        s_model_min = signals['s_model'].min()
        s_model_max = signals['s_model'].max()
        s_model_positive = (signals['s_model'] > 0).sum()
        s_model_negative = (signals['s_model'] < 0).sum()
        s_model_zero = (signals['s_model'] == 0).sum()
        
        print(f"\n📊 MODEL OUTPUT ANALYSIS:")
        print(f"  Total signals: {len(signals)}")
        print(f"  s_model range: [{s_model_min:.4f}, {s_model_max:.4f}]")
        print(f"  s_model mean: {s_model_mean:.4f}")
        print(f"  Positive predictions: {s_model_positive} ({s_model_positive/len(signals)*100:.1f}%)")
        print(f"  Negative predictions: {s_model_negative} ({s_model_negative/len(signals)*100:.1f}%)")
        print(f"  Neutral predictions: {s_model_zero}")
        
        # Execution analysis
        print(f"\n🔄 EXECUTION ANALYSIS:")
        print(f"  Total executions: {len(executions)}")
        
        if len(executions) > 0:
            side_counts = executions['side'].value_counts()
            print(f"  BUY trades: {side_counts.get('BUY', 0)}")
            print(f"  SELL trades: {side_counts.get('SELL', 0)}")
            
            # Calculate P&L
            total_pnl = 0
            wins = 0
            losses = 0
            
            for idx, row in executions.iterrows():
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
            
            win_rate = (wins / len(executions) * 100) if len(executions) > 0 else 0
            
            print(f"\n💰 P&L ANALYSIS:")
            print(f"  Total P&L: ${total_pnl:.2f}")
            print(f"  Wins: {wins}")
            print(f"  Losses: {losses}")
            print(f"  Win rate: {win_rate:.1f}%")
        
        # DIAGNOSIS
        print(f"\n🔍 DIAGNOSIS:")
        
        # Check if model is broken (only positive or only negative)
        if s_model_negative == 0 and s_model_positive > 0:
            print(f"  🔴 CRITICAL: Model ONLY predicts UP (no negative predictions)")
            print(f"     → System can ONLY generate BUY signals")
            print(f"     → Will NEVER generate SELL signals")
            print(f"     → This explains 0% win rate (positions never close)")
            print(f"  ❌ STATUS: BROKEN - Model needs retraining")
        elif s_model_positive == 0 and s_model_negative > 0:
            print(f"  🔴 CRITICAL: Model ONLY predicts DOWN (no positive predictions)")
            print(f"     → System can ONLY generate SELL signals")
            print(f"     → Will NEVER generate BUY signals")
            print(f"  ❌ STATUS: BROKEN - Model needs retraining")
        elif s_model_negative > 0 and s_model_positive > 0:
            # Model can predict both directions
            neg_pct = s_model_negative / len(signals) * 100
            pos_pct = s_model_positive / len(signals) * 100
            
            if neg_pct < 10 or pos_pct < 10:
                print(f"  🟡 WARNING: Model is heavily biased")
                print(f"     → {pos_pct:.1f}% UP predictions, {neg_pct:.1f}% DOWN predictions")
                print(f"     → Model may need rebalancing")
                print(f"  ⚠️  STATUS: WORKING but BIASED")
            else:
                print(f"  ✅ Model predictions are balanced")
                print(f"     → {pos_pct:.1f}% UP, {neg_pct:.1f}% DOWN")
                
                # Check if executions match model capability
                if len(executions) > 0:
                    buy_count = side_counts.get('BUY', 0)
                    sell_count = side_counts.get('SELL', 0)
                    
                    if sell_count == 0 and buy_count > 0:
                        print(f"  🔴 EXECUTION BUG: Model can predict DOWN but NO SELL trades!")
                        print(f"     → Position management logic may be broken")
                        print(f"     → System not closing positions")
                        print(f"  ❌ STATUS: Model OK, but EXECUTION BROKEN")
                    elif buy_count == 0 and sell_count > 0:
                        print(f"  🔴 EXECUTION BUG: Model can predict UP but NO BUY trades!")
                        print(f"     → Position management logic may be broken")
                        print(f"  ❌ STATUS: Model OK, but EXECUTION BROKEN")
                    else:
                        print(f"  ✅ Executions are bidirectional ({buy_count} BUY, {sell_count} SELL)")
                        
                        if win_rate == 0:
                            print(f"  🔴 PROFITABILITY: 0% win rate despite working model")
                            print(f"     → May need threshold tuning")
                            print(f"     → May need better exit logic")
                            print(f"  ⚠️  STATUS: WORKING but NOT PROFITABLE")
                        elif win_rate < 40:
                            print(f"  🟡 PROFITABILITY: Low win rate ({win_rate:.1f}%)")
                            print(f"     → Needs optimization")
                            print(f"  ⚠️  STATUS: WORKING but SUBOPTIMAL")
                        else:
                            print(f"  ✅ PROFITABILITY: Healthy win rate ({win_rate:.1f}%)")
                            print(f"  ✅ STATUS: FULLY OPERATIONAL")
                else:
                    print(f"  ⚠️  No executions yet - cannot verify execution logic")
                    print(f"  ⚠️  STATUS: Model OK, EXECUTION UNTESTED")
        else:
            print(f"  ⚠️  Insufficient data to diagnose")
            print(f"  ⚠️  STATUS: UNKNOWN")
            
    except FileNotFoundError as e:
        print(f"  ❌ ERROR: Data files not found")
        print(f"     {e}")
        print(f"  ❌ STATUS: NO DATA")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        print(f"  ❌ STATUS: ERROR")

print(f"\n{'='*80}")
print("SUMMARY")
print("="*80)
print("\n✅ = Working correctly")
print("⚠️  = Working but has issues")
print("🔴 = Critical problem")
print("❌ = Broken/Not working")
