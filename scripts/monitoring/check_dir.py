import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print("Signal columns:", df.columns.tolist()[:20])

if 'dir' in df.columns:
    print("\ndir column distribution:")
    print(df['dir'].value_counts())
    
    # Check when s_model is negative
    down_signals = df[df['s_model'] < 0]
    print(f"\nWhen s_model < 0 ({len(down_signals)} times):")
    print("dir values:")
    print(down_signals['dir'].value_counts())
