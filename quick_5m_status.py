import pandas as pd
from pathlib import Path

# Check 5m executions
exec_file = Path("paper_trading_outputs/5m/sheets_fallback/executions_paper.csv")
if exec_file.exists():
    df = pd.read_csv(exec_file)
    print(f"Total trades: {len(df)}")
    print(f"\nSide counts:")
    print(df["side"].value_counts())
    
    if len(df) > 0:
        print(f"\nLast 5 trades:")
        cols_to_show = ['ts_iso', 'side', 'qty', 'realized_pnl', 'equity']
        print(df[cols_to_show].tail())
        
        # Summary stats
        print(f"\n=== SUMMARY STATS ===")
        print(f"Win rate: {(df['realized_pnl'] > 0).sum() / len(df) * 100:.1f}%")
        print(f"Total PnL: ${df['realized_pnl'].sum():.2f}")
        print(f"Current Equity: ${df['equity'].iloc[-1]:.2f}")
        print(f"Initial Equity: ${df['equity'].iloc[0]:.2f}")
        returns = (df['equity'].iloc[-1] - df['equity'].iloc[0]) / df['equity'].iloc[0] * 100
        print(f"Total Return: {returns:.2f}%")
else:
    print("Executions file not found")

# Check signals
sig_file = Path("paper_trading_outputs/5m/sheets_fallback/signals.csv")
if sig_file.exists():
    df_sig = pd.read_csv(sig_file)
    print(f"\n=== SIGNALS ===")
    print(f"Total signals: {len(df_sig)}")
    if 'ts_ist' in df_sig.columns and len(df_sig) > 0:
        print(f"Last signal: {df_sig['ts_ist'].iloc[-1]}")
else:
    print("\nSignals file not found")

# Check equity
eq_file = Path("paper_trading_outputs/5m/sheets_fallback/equity.csv")
if eq_file.exists():
    df_eq = pd.read_csv(eq_file)
    print(f"\n=== EQUITY ===")
    if len(df_eq) > 0:
        print(f"Current equity: ${df_eq['equity'].iloc[-1]:.2f}")
        print(f"Initial equity: ${df_eq['equity'].iloc[0]:.2f}")
        returns = (df_eq['equity'].iloc[-1] - df_eq['equity'].iloc[0]) / df_eq['equity'].iloc[0] * 100
        print(f"Total return: {returns:.2f}%")
else:
    print("\nEquity file not found")
