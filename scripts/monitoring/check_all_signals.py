import pandas as pd

# Check 5m
df5m = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
print('5m s_model stats:')
print(f'Mean: {df5m["s_model"].mean():.4f}')
print(f'Min: {df5m["s_model"].min():.4f}')
print(f'Max: {df5m["s_model"].max():.4f}')
print(f'Positive: {(df5m["s_model"] > 0).sum()}')
print(f'Negative: {(df5m["s_model"] < 0).sum()}')
print(f'Total: {len(df5m)}')

# Check 12h
df12h = pd.read_csv('paper_trading_outputs/12h/sheets_fallback/signals.csv')
print('\n12h s_model stats:')
print(f'Mean: {df12h["s_model"].mean():.4f}')
print(f'Min: {df12h["s_model"].min():.4f}')
print(f'Max: {df12h["s_model"].max():.4f}')
print(f'Positive: {(df12h["s_model"] > 0).sum()}')
print(f'Negative: {(df12h["s_model"] < 0).sum()}')
print(f'Total: {len(df12h)}')
