"""
Quick diagnostic script to understand why the bot isn't making decisions
"""
import json

# Check config
with open('live_demo/config.json', 'r') as f:
    cfg = json.load(f)

print("=" * 60)
print("BOT CONFIGURATION DIAGNOSTIC")
print("=" * 60)

print("\n1. WARMUP SETTINGS:")
print(f"   warmup_bars: {cfg['data'].get('warmup_bars', 'NOT SET')}")
print(f"   warmup_skip_bars: {cfg['risk'].get('warmup_skip_bars', 'NOT SET')}")

print("\n2. THRESHOLDS:")
th = cfg['thresholds']
print(f"   CONF_MIN: {th.get('CONF_MIN')}")
print(f"   S_MIN: {th.get('S_MIN')}")
print(f"   M_MIN: {th.get('M_MIN')}")
print(f"   ALPHA_MIN: {th.get('ALPHA_MIN')}")
print(f"   require_consensus: {th.get('require_consensus')}")

print("\n3. COST GATES:")
costs = th.get('costs', {})
print(f"   taker_fee_bps: {costs.get('taker_fee_bps')}")
print(f"   slippage_bps: {costs.get('slippage_bps')}")
print(f"   min_net_edge_buffer_bps: {costs.get('min_net_edge_buffer_bps')}")
print(f"   TOTAL HURDLE: {costs.get('taker_fee_bps', 0) + costs.get('slippage_bps', 0) + costs.get('min_net_edge_buffer_bps', 0)} bps")

print("\n4. DYNAMIC ABSTAIN:")
dyn = th.get('dynamic_abstain', {})
print(f"   enabled: {dyn.get('enable')}")
print(f"   volatility_threshold: {dyn.get('volatility_threshold')}")
print(f"   spread_threshold_bps: {dyn.get('spread_threshold_bps')}")

print("\n5. EXECUTION:")
exec_cfg = cfg.get('execution', {})
print(f"   dry_run: {exec_cfg.get('dry_run', 'NOT SET')}")
print(f"   mode: {exec_cfg.get('mode', 'NOT SET')}")

print("\n6. BANDIT:")
bandit_cfg = exec_cfg.get('bandit', {})
print(f"   epsilon: {bandit_cfg.get('epsilon', 0.0)}")
print(f"   model_optimism: {bandit_cfg.get('model_optimism', 0.0)}")

print("\n" + "=" * 60)
print("ANALYSIS:")
print("=" * 60)

# Calculate what alpha is needed to pass Net Edge gate
hurdle = costs.get('taker_fee_bps', 0) + costs.get('slippage_bps', 0) + costs.get('min_net_edge_bps', 0)
min_alpha_needed = hurdle / 50.0  # We use alpha * 50.0 in decision.py
print(f"\nTo pass Net Edge gate:")
print(f"  - Need alpha > {min_alpha_needed:.4f}")
print(f"  - This means p_up - p_down > {min_alpha_needed:.4f}")
print(f"  - Example: p_up=0.70, p_down=0.30 → alpha=0.40 → edge=20bps → PASS")
print(f"  - Example: p_up=0.55, p_down=0.45 → alpha=0.10 → edge=5bps → FAIL")

print("\n" + "=" * 60)
