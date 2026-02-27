"""
Full end-to-end pipeline simulation — exactly what the live bot does per bar.
Run before restarting bot to confirm everything is healthy.
"""
import sys, json, random
sys.path.insert(0, r'C:\Users\yashw\MetaStackerBandit')

from live_demo.model_runtime import ModelRuntime
from live_demo.features import LiveFeatureComputer
from live_demo.decision import Thresholds, compute_signals_and_eligibility, decide_bandit
from live_demo.risk_and_exec import RiskConfig, RiskAndExec
from live_demo.bandit import SimpleThompsonBandit

print("=" * 62)
print(" END-TO-END PIPELINE HEALTH CHECK")
print("=" * 62)

# ── Load config ────────────────────────────────────────────────
cfg = json.load(open(r'C:\Users\yashw\MetaStackerBandit\live_demo\config.json'))
th = Thresholds(**cfg['thresholds'])
risk_cfg_dict = dict(cfg['risk'])
risk_cfg_dict['bar_minutes'] = 5.0
risk_cfg = RiskConfig(**risk_cfg_dict)
print(f"\n✅ Config loaded")
print(f"   impact_k={risk_cfg_dict['impact_k']}  base_notional=${risk_cfg_dict['base_notional']:,.0f}")
print(f"   vol_floor={risk_cfg_dict['vol_floor']}  sigma_target={risk_cfg_dict['sigma_target']}")
print(f"   max_impact_bps_hard={risk_cfg.max_impact_bps_hard}")

# ── Load model ─────────────────────────────────────────────────
mr = ModelRuntime(r'C:\Users\yashw\MetaStackerBandit\live_demo\models\LATEST.json')
cols = mr.columns
print(f"\n✅ Model loaded — {len(cols)} features, calibrator={mr.calibrator is not None}")

# ── Warm up features (simulate 500-bar warmup the bot does) ───
lf = LiveFeatureComputer(cols)
random.seed(42)
price = 96000.0

print(f"\n⏳ Simulating 120-bar warmup...")
for i in range(120):
    price += random.gauss(0, 55)
    bar = {'open': price-20, 'high': price+35, 'low': price-35, 'close': price, 'volume': 75.0}
    feats = lf.update_and_build(bar, {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}, 0.0)

print(f"   is_warmed: {lf.is_warmed()}  bar_count: {lf._bar_count}")
print(f"   mr_ema20_z: {feats[cols.index('mr_ema20_z')]:.4f}  (should be in [-5, +5])")

# ── Model inference ────────────────────────────────────────────
model_out = mr.infer(feats)
print(f"\n✅ Model inference:")
print(f"   p_down={model_out['p_down']:.4f}  p_neutral={model_out['p_neutral']:.4f}  p_up={model_out['p_up']:.4f}")
print(f"   s_model={model_out['s_model']:.4f}  sum={model_out['p_down']+model_out['p_neutral']+model_out['p_up']:.6f}")

# ── Decision gate ──────────────────────────────────────────────
cohort_snap = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
sigs, elig, eps_vec, extras = compute_signals_and_eligibility(cohort_snap, model_out, th)

print(f"\n✅ Decision gate:")
print(f"   p_non_neutral={extras['p_non_neutral']:.4f}  conf_dir={extras['conf_dir']:.4f}  strength={extras['strength']:.4f}")
print(f"   Eligibility: pros={elig['pros']}  amateurs={elig['amateurs']}  model_meta={elig['model_meta']}  model_bma={elig['model_bma']}")

# ── Bandit selection ───────────────────────────────────────────
bandit = SimpleThompsonBandit(n_arms=4)
decision = decide_bandit(sigs, elig, eps_vec, extras, bandit)
print(f"\n✅ Bandit decision:")
print(f"   dir={decision['dir']}  alpha={decision['alpha']:.4f}")
print(f"   chosen_arm={decision['details'].get('chosen')}")

# ── Risk / sizing ──────────────────────────────────────────────
risk = RiskAndExec(None, 'BTCUSDT', risk_cfg)
# Seed some returns so realized_vol is available
for i in range(60):
    risk.update_returns(95900 + i*10, 95910 + i*10)

last_price = price
target_pos = risk.target_position(decision['dir'], decision['alpha'])
print(f"\n✅ Position sizing:")
print(f"   realized_vol={risk.realized_vol():.4f} (annualized)")
print(f"   target_pos_fraction={target_pos:.4f}  ({target_pos*100:.1f}%)")
est_notional = abs(target_pos) * risk_cfg.base_notional
est_qty = est_notional / last_price
print(f"   est_notional=${est_notional:,.2f}")
print(f"   est_qty={est_qty:.6f} BTC @ ${last_price:,.0f}")

# ── Cost guard simulation ──────────────────────────────────────
impact_k = float(risk_cfg.impact_k or 0.0)
impact = impact_k * (est_qty ** 2) * last_price
impact_bps = (impact / est_notional) * 10000 if est_notional > 0 else 0.0
print(f"\n✅ Cost guard:")
print(f"   impact_bps={impact_bps:.2f}  hard_limit={risk_cfg.max_impact_bps_hard}")
print(f"   WOULD VETO: {impact_bps > risk_cfg.max_impact_bps_hard}")

# ── Final summary ──────────────────────────────────────────────
print()
print("=" * 62)
issues = []
if not lf.is_warmed():              issues.append("Feature computer not warmed")
if abs(model_out['s_model']) < 0.01: issues.append("s_model near zero — very weak signal")
if model_out['p_down'] > 0.99:      issues.append("Calibrator still stuck — fix not applied")
if not any(elig.values()):          issues.append("No arms eligible — decision will always be neutral")
if impact_bps > risk_cfg.max_impact_bps_hard: issues.append(f"Cost guard veto — impact {impact_bps:.0f} > {risk_cfg.max_impact_bps_hard}")
if target_pos == 0.0:               issues.append("target_pos=0 — likely realized_vol=0 at startup")

if not issues:
    print(" ✅ ALL CHECKS PASSED — BOT READY TO RESTART")
else:
    print(" ⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"    ✗ {issue}")
print("=" * 62)
