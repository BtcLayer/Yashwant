import pandas as pd

df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/signals.csv')

print('s_model stats:')
print(f'Mean: {df["s_model"].mean():.4f}')
print(f'Min: {df["s_model"].min():.4f}')
print(f'Max: {df["s_model"].max():.4f}')
print(f'Positive: {(df["s_model"] > 0).sum()}')
print(f'Negative: {(df["s_model"] < 0).sum()}')
print(f'Zero: {(df["s_model"] == 0).sum()}')
print(f'Total: {len(df)}')

# Check executions
exec_df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/executions_paper.csv')
print(f'\nExecutions:')
print(exec_df['side'].value_counts())
