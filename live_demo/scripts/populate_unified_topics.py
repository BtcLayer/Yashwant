import os
import json
import time
from live_demo.ops.log_router import LogRouter
from live_demo.ops.llm_logging import write_jsonl

# Load logging config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

router = LogRouter(cfg.get('logging', {}))
asset = cfg['data']['symbol']
ts = int(time.time() * 1000)

# Emit ensemble (llm)
router.emit_ensemble(ts=ts, asset=asset, raw_preds={'s_model': 0.0123, 'p_up': 0.55, 'p_down': 0.40}, meta={'manifest': cfg['artifacts']['latest_manifest']})

# Emit execution (emitter+llm)
router.emit_execution(ts=ts, asset=asset, exec_resp={'side':'BUY','price':50000,'qty':0.001,'slip_bps':1.2,'route':'BINANCE'}, risk_state={'position':0.1}, bar_id=1)

# Emit costs (emitter)
router.emit_costs(ts=ts, asset=asset, costs={'trade_notional':50.0,'fee_bps':5.0,'slip_bps':1.2,'impact_k':0.5,'impact_bps':0.8,'adv_ref':1000000.0,'cost_usd':0.05,'cost_bps_total':7.0})

# Emit equity (llm)
router.emit_equity(asset=asset, ts=ts, pnl_total_usd=12.34, equity_value=10012.34)

# Emit overlay_status (llm)
router.emit_overlay_status(ts=ts, asset=asset, status={'bar_id':1,'confidence':0.66,'alignment_rule':'agreement','chosen_timeframes':['5m','15m'],'individual_signals':{'5m':{'dir':1,'alpha':0.3,'conf':0.7},'15m':{'dir':1,'alpha':0.4,'conf':0.8}}})

# Emit alerts (llm)
router.emit_alert(ts=ts, asset=asset, alert={'type':'ws_stale','staleness_ms':120000,'reconnects':0,'queue_drops':0})

# Emit hyperliquid_fills (llm)
router.emit_hyperliquid_fill(ts=ts, asset=asset, fill={'ts':ts,'address':'0xabc','coin':'BTC','side':'buy','price':50000,'size':0.001})

# Emit sizing/risk (llm direct)
write_jsonl('sizing_risk_log', {'asset': asset, 'raw_score_bps': 12.3, 'target_vol_ann': 0.15, 'position_after': 0.0, 'overlay_conf': 0.75}, asset=asset)

# Emit KPI scorecard (llm direct)
write_jsonl('kpi_scorecard', {'asset': asset, 'event':'kpi_scorecard','Sharpe_1w':2.6,'max_DD_pct':5.0,'turnover_bps_day':120,'in_band_share':0.55,'gates':{'sharpe_pass':True,'dd_pass':True,'turnover_pass':True,'cost_pass':None}}, asset=asset)

print('Emitted sample records to unified logs base.')
