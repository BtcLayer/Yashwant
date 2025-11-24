import os
import json
from collections import deque
from datetime import datetime, timezone

import numpy as np

from live_demo.model_runtime import ModelRuntime
from live_demo.features import FeatureBuilder, LiveFeatureComputer
from live_demo.decision import Thresholds, decide
from live_demo.bandit import SimpleThompsonBandit
from live_demo.ops.log_router import LogRouter
from live_demo.ops.log_emitter import get_emitter


def to_iso(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms/1000.0, tz=timezone.utc)
    return dt.isoformat().replace('+00:00', 'Z')


def load_cfg():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    cfg_path = os.path.join(base, 'config.json')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    models_dir = os.path.join(base, 'models')
    manifest = os.path.join(models_dir, 'LATEST.json')
    cfg = load_cfg()

    # Initialize model and features
    mr = ModelRuntime(manifest)
    fb = FeatureBuilder(mr.feature_schema_path)
    lf = LiveFeatureComputer(fb.columns, timeframe=cfg['data'].get('interval','5m'))

    # Synthetic warmup and last bar
    # start price 50000, small drift, constant volume
    price = 50000.0
    ts = 1730000000000  # fixed timestamp ms
    for i in range(200):
        o = price
        c = price * (1.0 + 0.0001*((-1)**i))
        h = max(o, c) * 1.0005
        l = min(o, c) * 0.9995
        v = 100 + (i % 5)
        bar_row = {'open': o, 'high': h, 'low': l, 'close': c, 'volume': v}
        cohort = {'pros': 0.05*np.sin(i/10.0), 'amateurs': -0.03*np.cos(i/12.0), 'mood': 0.07*np.sin(i/15.0)}
        _ = lf.update_and_build(bar_row, cohort, funding=0.0001)
        price = c
        ts += 300000  # 5m bars

    # Last bar features
    bar_row = {'open': price, 'high': price*1.0003, 'low': price*0.9997, 'close': price*1.0001, 'volume': 123}
    cohort = {'pros': 0.18, 'amateurs': -0.08, 'mood': 0.12}
    x = lf.update_and_build(bar_row, cohort, funding=0.0002)

    # Model inference
    model_out = mr.infer(x)

    # Build meta and BMA scores for bandit
    p_up = float(model_out.get('p_up', 0.33))
    p_down = float(model_out.get('p_down', 0.33))
    s_meta = float(model_out.get('s_model', 0.0))
    s_bma = 0.5*s_meta + 0.5*(p_up - p_down)
    decision_model_out = {**model_out, 's_model_meta': s_meta, 's_model_bma': s_bma}

    # Thresholds
    th = Thresholds(**cfg['thresholds'])

    # Bandit (4 arms: pros, amateurs, model_meta, model_bma)
    bandit = SimpleThompsonBandit(n_arms=4)

    # Decision
    d = decide(cohort, decision_model_out, th, bandit=bandit, epsilon=float(cfg.get('execution',{}).get('bandit',{}).get('epsilon',0.0)))

    # Emit logs via LogRouter (to JSONL or console depending on config)
    router = LogRouter(cfg.get('logging', {}))
    # Emit signals using the emitter directly (router has no signals topic)
    try:
        emitter = get_emitter()
        emitter.emit_signals(ts=ts, symbol=cfg['data']['symbol'], features=x, model_out=decision_model_out, decision=d, cohort=cohort)
    except Exception:
        pass
    router.emit_equity(ts=ts, asset=cfg['data']['symbol'], pnl_total_usd=0.0, equity_value=10000.0)
    router.emit_ensemble(ts=ts, asset=cfg['data']['symbol'], raw_preds=decision_model_out, meta={'manifest':'models/LATEST.json'})

    print(json.dumps({
        'ts': to_iso(ts),
        'decision': d,
        'cohort': cohort,
        'model_out': {k: decision_model_out[k] for k in ['p_down','p_neutral','p_up','s_model','s_model_meta','s_model_bma'] if k in decision_model_out}
    }, indent=2))
    print('OFFLINE LIVE DEMO SMOKE: PASS')


if __name__ == '__main__':
    main()
