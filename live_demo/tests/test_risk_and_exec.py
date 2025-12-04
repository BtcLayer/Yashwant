import pytest

from live_demo.risk_and_exec import RiskAndExec, RiskConfig


def test_target_position_shrinks_with_vol_guard(monkeypatch):
    cfg = RiskConfig(
        sigma_target=0.2,
        pos_max=1.0,
        vol_guard_enable=True,
        vol_guard_sigma=0.5,
        vol_guard_min_scale=0.3,
    )
    risk = RiskAndExec(client=None, symbol="BTCUSDT", cfg=cfg)
    monkeypatch.setattr(risk, "realized_vol", lambda: 1.0)

    guarded = risk.target_position(direction=1, alpha=0.8)
    assert guarded == pytest.approx(0.08, rel=1e-6)
    assert risk._last_vol_guard == pytest.approx(0.5, rel=1e-6)

    cfg_no_guard = RiskConfig(sigma_target=0.2, pos_max=1.0, vol_guard_enable=False)
    risk_no_guard = RiskAndExec(client=None, symbol="BTCUSDT", cfg=cfg_no_guard)
    monkeypatch.setattr(risk_no_guard, "realized_vol", lambda: 1.0)
    baseline = risk_no_guard.target_position(direction=1, alpha=0.8)

    assert baseline > guarded
