"""Find signals with actual directional bias"""
import pandas as pd
import json
from pathlib import Path

# Load all signals
signals = []
files = list(Path('paper_trading_outputs').rglob('signals.jsonl'))

for f in files:
    with open(f) as file:
        for line in file:
            if line.strip():
                try:
                    rec = json.loads(line)
                    p_up = float(rec.get('p_up', 0.0))
                    p_down = float(rec.get('p_down', 0.0))
                    p_neutral = float(rec.get('p_neutral', 1.0))
                    
                    # Normalize
                    total = p_up + p_down + p_neutral
                    if total > 0:
                        p_up /= total
                        p_down /= total
                        p_neutral /= total
                    
                    signals.append({
                        'p_up': p_up,
                        'p_down': p_down,
                        'p_neutral': p_neutral,
                        'has_direction': p_up > 0.01 or p_down > 0.01
                    })
                except:
                    pass

df = pd.DataFrame(signals)
print(f'Total signals: {len(df)}')
print(f'Signals with p_up > 0.01: {(df["p_up"] > 0.01).sum()}')
print(f'Signals with p_down > 0.01: {(df["p_down"] > 0.01).sum()}')
print(f'Signals with p_up > 0.05: {(df["p_up"] > 0.05).sum()}')
print(f'Signals with p_down > 0.05: {(df["p_down"] > 0.05).sum()}')

# Show distribution of directional signals
directional = df[(df['p_up'] > 0.01) | (df['p_down'] > 0.01)]
print(f'\nDirectional signals: {len(directional)}')
if len(directional) > 0:
    print(directional.describe())
    print('\nSample directional signals:')
    print(directional.head(20))
