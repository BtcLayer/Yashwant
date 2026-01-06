import pandas as pd

try:
    df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv').tail(20)
    
    # Determine dominant class for each row
    df['class'] = df[['p_up', 'p_down', 'p_neutral']].idxmax(axis=1)
    
    up_count = (df['class'] == 'p_up').sum()
    down_count = (df['class'] == 'p_down').sum()
    neutral_count = (df['class'] == 'p_neutral').sum()
    
    print("--- SIGNAL DISTRIBUTION (Last 20 Bars) ---")
    print(f"UP Signals:      {up_count} ({up_count/20:.0%})")
    print(f"DOWN Signals:    {down_count} ({down_count/20:.0%})")
    print(f"NEUTRAL Signals: {neutral_count} ({neutral_count/20:.0%})")
    print(f"Avg Neutral Prob: {df['p_neutral'].mean():.1%}")
    
    print("\n--- LATEST 5 SIGNALS ---")
    # Convert ts to readable time
    df['time'] = pd.to_datetime(df['ts'], unit='ms').dt.strftime('%H:%M')
    print(df[['time', 'p_up', 'p_down', 'p_neutral']].tail(5).to_string(index=False))

except Exception as e:
    print(e)
