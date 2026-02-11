from dataclasses import dataclass
from typing import Dict, Optional, Any, Tuple
from collections import deque
import importlib
import math

import numpy as np

from live_demo.reason_codes import GuardReasonCode


@dataclass
class RiskConfig:
    sigma_target: float = 0.20
    pos_max: float = 1.0
    cooldown_bars: int = 1
    realized_vol_window: int = 50
    # Duration of one bar in minutes (used for annualization and cooldown calculations)
    bar_minutes: float = 5.0
    # Base USD notional used to translate target position fraction into quantity
    # Example: with BTC at $60k, base_notional=5000 and target_pos=0.1 -> qty ≈ 500 / 60000 ≈ 0.0083 BTC
    base_notional: float = 5000.0
    # Optional: when realized_vol is not yet available (startup/one-shot), use this floor
    # so we can compute a non-zero target. If <= 0, we fall back to returning 0.
    vol_floor: float = 0.0
    # Guardrails
    adv_cap_pct: float = 0.0  # % of ADV20 USD per trade cap
    rebalance_min_pos_delta: float = (
        0.0  # min change in target position fraction to trade
    )
    daily_stop_dd_pct: float = 0.0  # daily stop drawdown percent
    warmup_skip_bars: int = 0  # bars to skip trading after start
    # Paper trading costs and slippage assumptions (bps)
    cost_bps: float = 5.0
    slippage_bps: float = 0.0
    impact_k: float = 0.0
    max_impact_bps_hard: float = 200.0  # Hard veto threshold for impact cost
    # Net-edge gating
    min_net_edge_bps: float = 10.0
    max_total_cost_bps: float = 25.0
    enable_net_edge_gating: bool = True
    # Position exit management (optional)
    enable_forced_exits: bool = True
    max_position_duration_bars: int = 288
    stop_loss_bps: float = 200.0
    take_profit_bps: float = 300.0


class RiskAndExec:
    def __init__(self, client, symbol: str, cfg: RiskConfig):
        self.client = client
        self.symbol = symbol
        self.cfg = cfg
        self._retns = []
        self._cooldown_until_ts = 0
        self._pos = 0.0
        self.adv20_usd: float = 0.0  # to be set from main using last_close * adv20_qty
        # Exchange filters/precision cache
        self._filters: Optional[Dict[str, Any]] = None
        self._step_size: Optional[float] = None
        self._tick_size: Optional[float] = None
        self._min_qty: float = 0.0
        self._min_notional: float = 0.0
        # Paper trading state (when dry_run)
        self._paper_qty: float = 0.0
        self._paper_avg_px: float = 0.0
        self._paper_realized: float = 0.0
        # Position tracking for exit management
        self._position_entry_bar: Optional[int] = None
        self._position_entry_price: Optional[float] = None
        self._position_entry_ts_ms: Optional[int] = None
        # Pre-trade guard state
        self._order_times_ms = deque(maxlen=100)
        self._hour_execs = deque(maxlen=10_000)  # (ts_ms, notional_usd)
        self._flip_last_sign = 0
        self._flip_last_ts_ms = 0

    def update_returns(self, prev_close: float, new_close: float):
        if prev_close and new_close:
            r = (new_close / prev_close) - 1.0
            self._retns.append(r)
            if len(self._retns) > self.cfg.realized_vol_window:
                self._retns = self._retns[-self.cfg.realized_vol_window :]

    def realized_vol(self) -> float:
        if len(self._retns) < 2:
            return 0.0
        # Annualize using number of bars per year = 365 days * 24 hours * 60 minutes / minutes_per_bar
        minutes_per_bar = max(1e-9, float(self.cfg.bar_minutes))
        bars_per_year = (365.0 * 24.0 * 60.0) / minutes_per_bar
        return float(np.std(self._retns, ddof=1) * np.sqrt(bars_per_year))

    def target_position(self, direction: int, alpha: float) -> float:
        rv = self.realized_vol()
        # If realized vol not available yet, optionally use a configured floor for testing/demo
        if rv <= 0:
            if (self.cfg.vol_floor or 0.0) > 0.0:
                rv = float(self.cfg.vol_floor)
            else:
                return 0.0
        pos = (self.cfg.sigma_target / rv) * alpha
        pos = max(-self.cfg.pos_max, min(self.cfg.pos_max, pos))
        return float(direction) * pos

    def should_close_position(
        self,
        current_bar: int,
        current_price: float,
        decision: Dict[str, Any],
        exit_thresholds: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str]:
        """Determine if current position should be closed.
        
        Returns:
            (should_close, reason) tuple
        """
        current_pos = float(self._pos)
        
        # No position to close
        if abs(current_pos) < 1e-9:
            return False, ""
        
        exit_conf_min = 0.40  # Default relaxed threshold
        exit_alpha_min = 0.30
        max_duration_bars = 288  # 24 hours at 5m intervals
        stop_loss_bps = 200.0  # 2% stop loss
        take_profit_bps = 300.0  # 3% take profit
        
        if exit_thresholds:
            exit_conf_min = float(exit_thresholds.get('exit_conf_min', exit_conf_min))
            exit_alpha_min = float(exit_thresholds.get('exit_alpha_min', exit_alpha_min))
            max_duration_bars = int(exit_thresholds.get('max_position_duration_bars', max_duration_bars))
            stop_loss_bps = float(exit_thresholds.get('stop_loss_bps', stop_loss_bps))
            take_profit_bps = float(exit_thresholds.get('take_profit_bps', take_profit_bps))
        
        direction = int(decision.get('dir', 0))
        alpha = float(decision.get('alpha', 0.0))
        conf = float(decision.get('details', {}).get('conf', 0.0)) if isinstance(decision.get('details'), dict) else alpha
        
        # Exit Reason 1: Model signal reversal with sufficient confidence
        # Close LONG if model predicts DOWN with relaxed exit thresholds
        if current_pos > 0 and direction == -1:
            if conf >= exit_conf_min or alpha >= exit_alpha_min:
                return True, "model_reversal_long_to_short"
        
        # Close SHORT if model predicts UP with relaxed exit thresholds
        if current_pos < 0 and direction == 1:
            if conf >= exit_conf_min or alpha >= exit_alpha_min:
                return True, "model_reversal_short_to_long"
        
        # Exit Reason 2: Maximum position duration exceeded
        if self._position_entry_bar is not None and max_duration_bars > 0:
            bars_held = current_bar - self._position_entry_bar
            if bars_held >= max_duration_bars:
                return True, f"max_duration_{bars_held}_bars"
        
        # Exit Reason 3: Stop loss hit
        if self._position_entry_price is not None and current_price > 0 and stop_loss_bps > 0:
            pnl_bps = 0.0
            if current_pos > 0:  # LONG position
                pnl_bps = ((current_price - self._position_entry_price) / self._position_entry_price) * 10000.0
            else:  # SHORT position
                pnl_bps = ((self._position_entry_price - current_price) / self._position_entry_price) * 10000.0
            
            if pnl_bps < -stop_loss_bps:
                return True, f"stop_loss_{pnl_bps:.1f}bps"
        
        # Exit Reason 4: Take profit hit
        if self._position_entry_price is not None and current_price > 0 and take_profit_bps > 0:
            pnl_bps = 0.0
            if current_pos > 0:  # LONG position
                pnl_bps = ((current_price - self._position_entry_price) / self._position_entry_price) * 10000.0
            else:  # SHORT position
                pnl_bps = ((self._position_entry_price - current_price) / self._position_entry_price) * 10000.0
            
            if pnl_bps > take_profit_bps:
                return True, f"take_profit_{pnl_bps:.1f}bps"
        
        return False, ""

    def get_exit_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a reversal decision into an explicit exit decision.
        
        When holding a position and model reverses, we want to close the position
        (set target to 0) rather than flip to opposite direction.
        """
        return {
            'dir': 0,  # Neutral direction = close position
            'alpha': 0.0,
            'details': {
                **decision.get('details', {}),
                'mode': 'exit',
                'original_dir': decision.get('dir', 0),
                'exit_reason': 'position_close'
            }
        }
    
    def update_position_tracking(self, new_pos: float, current_bar: int, current_price: float, ts_ms: int):
        """Update position tracking when position changes."""
        old_pos = float(self._pos)
        self._pos = new_pos
        
        # Position opened or increased
        if abs(new_pos) > abs(old_pos) + 1e-9:
            self._position_entry_bar = current_bar
            self._position_entry_price = current_price
            self._position_entry_ts_ms = ts_ms
        # Position closed completely
        elif abs(new_pos) < 1e-9:
            self._position_entry_bar = None
            self._position_entry_price = None
            self._position_entry_ts_ms = None
        # Position flipped direction
        elif (old_pos > 0 and new_pos < 0) or (old_pos < 0 and new_pos > 0):
            self._position_entry_bar = current_bar
            self._position_entry_price = current_price
            self._position_entry_ts_ms = ts_ms

    def in_cooldown(self, now_ms: int) -> bool:
        return now_ms < self._cooldown_until_ts

    def set_cooldown(self, last_kline_close_ms: int):
        # Cooldown duration is expressed in bars; convert bars to milliseconds using bar_minutes
        bar_ms = max(1.0, float(self.cfg.bar_minutes)) * 60_000.0
        self._cooldown_until_ts = int(
            last_kline_close_ms + self.cfg.cooldown_bars * bar_ms
        )

    def get_position(self) -> float:
        return self._pos

    # ---------- Pre-trade guards (centralized) ----------
    def apply_spread_guard(self, decision: Dict[str, Any], book_ticker: Optional[Dict[str, float]], ms_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Override decision to neutral if spread exceeds configured cap.

        ms_cfg example: {"enable": true, "max_spread_bps": 5.0}
        book_ticker example: {"bid": 60000.0, "ask": 60001.0}
        """
        try:
            if not ms_cfg or not bool(ms_cfg.get('enable', False)):
                return decision
            bt = book_ticker or {}
            bid = bt.get('bid')
            ask = bt.get('ask')
            if bid is None or ask is None:
                return decision
            mid = 0.5 * (float(bid) + float(ask))
            spread_bps = 10000.0 * (float(ask) - float(bid)) / max(1e-9, mid)
            if float(spread_bps) > float(ms_cfg.get('max_spread_bps', 5.0)):
                details_prev = decision.get('details', {}) if isinstance(decision, dict) else {}
                return {
                    **decision,
                    'dir': 0,
                    'alpha': 0.0,
                    'details': {**details_prev, 'mode': GuardReasonCode.SPREAD, 'spread_bps': spread_bps}
                }
        except Exception:
            # Guard must not break the loop
            return decision
        return decision

    def _prune_orders_1s(self, now_ms: int):
        one_sec_ago = now_ms - 1000
        while self._order_times_ms and self._order_times_ms[0] < one_sec_ago:
            self._order_times_ms.popleft()

    def _prune_hour_execs(self, now_ms: int):
        one_hr_ago = now_ms - 3600_000
        while self._hour_execs and self._hour_execs[0][0] < one_hr_ago:
            self._hour_execs.popleft()

    def notify_order_attempt(self, ts_ms: int):
        try:
            self._prune_orders_1s(ts_ms)
            self._order_times_ms.append(ts_ms)
        except Exception:
            pass

    def post_execution_update(self, exec_resp: Optional[Dict[str, Any]], ts_ms: int):
        """Update hourly notional and flip-timing state from an execution response."""
        try:
            if not exec_resp:
                return
            notional = 0.0
            try:
                q = float(exec_resp.get('qty') or 0.0)
                px = float(exec_resp.get('price') or exec_resp.get('mid_price') or 0.0)
                notional = abs(q * px)
            except Exception:
                notional = 0.0
            self._prune_hour_execs(ts_ms)
            if notional > 0.0:
                self._hour_execs.append((ts_ms, notional))
            # Update flip timing by comparing new target position sign with existing position
            new_pos = float(self._pos)
            new_sign = 0
            if new_pos > 0:
                new_sign = 1
            elif new_pos < 0:
                new_sign = -1
            if self._flip_last_sign != 0 and new_sign != 0 and new_sign != self._flip_last_sign:
                self._flip_last_ts_ms = ts_ms
            if new_sign != 0:
                self._flip_last_sign = new_sign
        except Exception:
            pass

    def evaluate_pretrade_guards(
        self,
        decision: Dict[str, Any],
        *,
        ts_ms: int,
        book_ticker: Optional[Dict[str, float]] = None,
        funding_rate: Optional[float] = None,
        last_price: Optional[float] = None,
        controls: Optional[Dict[str, Any]] = None,
        microstructure_cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply all configured pre-trade guards and return possibly-updated decision.

        Non-fatal: any errors will leave decision unchanged.
        """
        try:
            details_prev = decision.get('details', {}) if isinstance(decision, dict) else {}
            d = dict(decision)
            # Spread guard (reuse existing helper)
            d = self.apply_spread_guard(d, book_ticker, microstructure_cfg or {})
            # Funding guard: avoid paying extreme funding in decision direction
            try:
                fr = float(funding_rate) if funding_rate is not None else 0.0
                fg_bias = float((controls or {}).get('funding_guard_bias', 0.0) or 0.0)
                # Simple rule: if |funding| > bias and sign(funding)==dir, neutralize
                if d.get('dir', 0) != 0 and abs(fr) > fg_bias and (1 if fr > 0 else -1) == int(d.get('dir', 0)):
                    d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.FUNDING, 'funding': fr}}
            except Exception:
                pass
            # Min sign-flip gap: prevent rapid flips within N seconds
            try:
                gap_s = int((controls or {}).get('min_sign_flip_gap_s', 0) or 0)
                if gap_s > 0 and int(d.get('dir', 0)) != 0:
                    new_sign = 1 if int(d.get('dir', 0)) > 0 else -1
                    last_flip = int(self._flip_last_ts_ms or 0)
                    if self._flip_last_sign != 0 and new_sign != self._flip_last_sign and last_flip > 0:
                        if (ts_ms - last_flip) < (gap_s * 1000):
                            d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.MIN_SIGN_FLIP, 'gap_s': gap_s}}
            except Exception:
                pass
            # Delta pi minimum: require sufficient change in target position fraction
            try:
                bps_min = float((controls or {}).get('delta_pi_min_bps', 0.0) or 0.0)
                if bps_min > 0 and int(d.get('dir', 0)) != 0:
                    # Map bps threshold to position fraction
                    frac_min = bps_min / 10_000.0
                    tgt = self.target_position(int(d.get('dir', 0)), float(d.get('alpha', 0.0)))
                    if abs(float(tgt) - float(self._pos)) < frac_min:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.DELTA_PI_MIN, 'delta_pi_min_bps': bps_min}}
            except Exception:
                pass
            # Impact Guard: estimate impact BPS and cap it
            try:
                max_impact = float((controls or {}).get('max_impact_bps', 0.0) or 0.0)
                impact_k = float(self.cfg.impact_k or 0.0)
                if max_impact > 0.0 and impact_k > 0.0 and int(d.get('dir', 0)) != 0 and last_price is not None:
                    tgt = self.target_position(int(d.get('dir', 0)), float(d.get('alpha', 0.0)))
                    pos_delta_frac = abs(float(tgt) - float(self._pos))
                    est_notional = pos_delta_frac * max(1e-6, float(self.cfg.base_notional))
                    est_qty = est_notional / max(1e-6, last_price)
                    
                    # Estimate impact bps: k * qty * 10000
                    est_impact_bps = impact_k * est_qty * 10000.0
                    
                    if est_impact_bps > max_impact:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {
                            **details_prev, 
                            'mode': GuardReasonCode.IMPACT_GUARD, 
                            'est_impact_bps': est_impact_bps, 
                            'max_impact_bps': max_impact
                        }}
            except Exception:
                pass
            
            # Hard impact veto: block trades with critically high impact costs
            try:
                if self.cfg.max_impact_bps_hard > 0.0 and int(d.get('dir', 0)) != 0 and last_price is not None:
                    impact_k = float(self.cfg.impact_k or 0.0)
                    if impact_k > 0.0:
                        tgt = self.target_position(int(d.get('dir', 0)), float(d.get('alpha', 0.0)))
                        pos_delta_frac = abs(float(tgt) - float(self._pos))
                        est_notional = pos_delta_frac * max(1e-6, float(self.cfg.base_notional))
                        est_qty = est_notional / max(1e-6, last_price)
                        
                        # Estimate impact bps
                        impact_est = impact_k * (est_qty ** 2) * last_price
                        impact_bps_est = (impact_est / est_notional) * 10000 if est_notional > 0 else 0.0
                        
                        if impact_bps_est > self.cfg.max_impact_bps_hard:
                            d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {
                                **details_prev,
                                'mode': GuardReasonCode.IMPACT_CRITICAL,
                                'impact_bps_est': impact_bps_est,
                                'max_impact_bps_hard': self.cfg.max_impact_bps_hard,
                                'est_notional': est_notional,
                                'est_qty': est_qty,
                                'veto_reason': f"Impact {impact_bps_est:.1f} bps exceeds hard limit {self.cfg.max_impact_bps_hard}"
                            }}
            except Exception:
                pass
            
            # Net-edge gating: require predicted edge to exceed total costs
            try:
                if self.cfg.enable_net_edge_gating and int(d.get('dir', 0)) != 0:
                    # Extract signal strength in bps
                    alpha = float(d.get('alpha', 0.0))
                    signal_strength_bps = alpha * 10000  # Convert to bps
                    
                    # Estimate total cost
                    base_cost_bps = float(self.cfg.cost_bps)
                    slip_bps = float(self.cfg.slippage_bps)
                    
                    # Estimate impact cost
                    impact_bps_est = 0.0
                    if float(self.cfg.impact_k or 0.0) > 0.0 and last_price is not None:
                        tgt = self.target_position(int(d.get('dir', 0)), alpha)
                        pos_delta_frac = abs(float(tgt) - float(self._pos))
                        est_notional = pos_delta_frac * max(1e-6, float(self.cfg.base_notional))
                        est_qty = est_notional / max(1e-6, last_price)
                        impact_est = float(self.cfg.impact_k) * (est_qty ** 2) * last_price
                        impact_bps_est = (impact_est / est_notional) * 10000 if est_notional > 0 else 0.0
                    
                    total_cost_bps = base_cost_bps + slip_bps + impact_bps_est
                    net_edge_bps = signal_strength_bps - total_cost_bps
                    
                    # Store for logging
                    details = d.get('details', {})
                    details['net_edge_bps'] = net_edge_bps
                    details['estimated_cost_bps'] = total_cost_bps
                    details['signal_strength_bps'] = signal_strength_bps
                    
                    # Check threshold
                    if net_edge_bps < self.cfg.min_net_edge_bps:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {
                            **details_prev,
                            'mode': GuardReasonCode.NET_EDGE_INSUFFICIENT,
                            'net_edge_bps': net_edge_bps,
                            'estimated_cost_bps': total_cost_bps,
                            'signal_strength_bps': signal_strength_bps,
                            'min_net_edge_bps': self.cfg.min_net_edge_bps
                        }}
                    else:
                        # Update details even if passed
                        d['details'] = details
            except Exception:
                pass
            
            # Throttle: limit orders per second
            try:
                mops = int((controls or {}).get('max_orders_per_sec', 0) or 0)
                if mops > 0 and int(d.get('dir', 0)) != 0:
                    self._prune_orders_1s(ts_ms)
                    if len(self._order_times_ms) >= mops:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.THROTTLE, 'max_orders_per_sec': mops}}
            except Exception:
                pass
            # ADV per-order cap: estimate this order's notional and cap per controls.adv_order_cap (fraction of ADV)
            try:
                order_cap_frac = float((controls or {}).get('adv_order_cap', 0.0) or 0.0)
                adv_usd = float(self.adv20_usd or 0.0)
                if order_cap_frac > 0.0 and adv_usd > 0.0 and int(d.get('dir', 0)) != 0:
                    tgt = self.target_position(int(d.get('dir', 0)), float(d.get('alpha', 0.0)))
                    pos_delta_frac = abs(float(tgt) - float(self._pos))
                    est_notional = pos_delta_frac * max(1e-6, float(self.cfg.base_notional))
                    cap_usd = adv_usd * order_cap_frac
                    if est_notional > cap_usd:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.ADV_ORDER_CAP, 'est_usd': est_notional, 'cap_usd': cap_usd}}
            except Exception:
                pass
            # ADV per-hour cap: estimate notional and cap total per hour
            try:
                hour_cap = float((controls or {}).get('adv_hour_cap', 0.0) or 0.0)
                adv_usd = float(self.adv20_usd or 0.0)
                if hour_cap > 0.0 and adv_usd > 0.0 and int(d.get('dir', 0)) != 0 and last_price is not None:
                    self._prune_hour_execs(ts_ms)
                    used = sum(n for _, n in self._hour_execs)
                    cap_usd = adv_usd * hour_cap
                    # Estimate notional for this trade using base_notional and position change fraction
                    tgt = self.target_position(int(d.get('dir', 0)), float(d.get('alpha', 0.0)))
                    pos_delta_frac = abs(float(tgt) - float(self._pos))
                    est_notional = pos_delta_frac * max(1e-6, float(self.cfg.base_notional))
                    if used + est_notional > cap_usd:
                        d = {**d, 'dir': 0, 'alpha': 0.0, 'details': {**details_prev, 'mode': GuardReasonCode.ADV_HOUR_CAP, 'used_usd': used, 'cap_usd': cap_usd}}
            except Exception:
                pass
            return d
        except Exception:
            return decision

    # ---------- Precision & exchange info helpers ----------
    def _extract_filters(self, info: Dict[str, Any]) -> None:
        try:
            filters = info.get("filters", [])
            lot = next(
                (
                    f
                    for f in filters
                    if f.get("filterType") in ("MARKET_LOT_SIZE", "LOT_SIZE")
                ),
                None,
            )
            tick = next(
                (f for f in filters if f.get("filterType") == "PRICE_FILTER"), None
            )
            min_notional = next(
                (f for f in filters if f.get("filterType") == "MIN_NOTIONAL"), None
            )
            if lot:
                if lot.get("stepSize"):
                    self._step_size = float(lot["stepSize"])
                if lot.get("minQty"):
                    self._min_qty = max(self._min_qty, float(lot["minQty"]))
            if tick and tick.get("tickSize"):
                self._tick_size = float(tick["tickSize"])
            if min_notional and min_notional.get("notional"):
                self._min_notional = max(
                    self._min_notional, float(min_notional["notional"])
                )
            self._filters = info
        except (KeyError, TypeError, ValueError):
            # Best-effort; keep defaults
            pass

    def ensure_exchange_filters(self):
        if self._filters is not None:
            return
        # Try connector's exchange_info
        try:
            if hasattr(self.client, "exchange_info"):
                ei = self.client.exchange_info()
                symbols = ei.get("symbols") if isinstance(ei, dict) else None
                if symbols:
                    match = next(
                        (s for s in symbols if s.get("symbol") == self.symbol), None
                    )
                    if match:
                        self._extract_filters(match)
                        return
        except (KeyError, TypeError, ValueError):
            pass
        # Try python-binance futures exchange info
        try:
            if hasattr(self.client, "futures_exchange_info"):
                ei = self.client.futures_exchange_info()
                symbols = ei.get("symbols") if isinstance(ei, dict) else None
                if symbols:
                    match = next(
                        (s for s in symbols if s.get("symbol") == self.symbol), None
                    )
                    if match:
                        self._extract_filters(match)
                        return
        except (KeyError, TypeError, ValueError, AttributeError):
            pass
        # Try python-binance get_symbol_info via adapter method
        try:
            if hasattr(self.client, "get_symbol_info"):
                info = self.client.get_symbol_info(self.symbol)
                if info:
                    self._extract_filters(info)
                    return
        except (KeyError, TypeError, ValueError):
            pass
        # Try python-binance futures symbol info
        try:
            if hasattr(self.client, "futures_symbol_info"):
                info = self.client.futures_symbol_info(self.symbol)
                if info:
                    self._extract_filters(info)
                    return
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

    def clamp_qty(self, qty: float, price: float) -> float:
        q = abs(qty)
        # Min qty
        if self._min_qty > 0:
            q = max(q, self._min_qty)
        # Min notional
        if self._min_notional > 0 and price > 0:
            q = max(q, self._min_notional / price)
        # Step size
        step = self._step_size or 0.000001
        q = math.floor(q / step) * step
        return q if qty >= 0 else -q

    # ---------- Paper simulation helpers ----------
    def _apply_slippage(self, side: str, price: float) -> float:
        bps = max(0.0, float(self.cfg.slippage_bps))
        if bps <= 0.0:
            return price
        slip = price * (bps / 10_000.0)
        return price + slip if side.upper() == "BUY" else price - slip

    def _simulate_trade(self, side: str, qty: float, price: float) -> Dict[str, Any]:
        # Side is 'BUY' or 'SELL'; qty is positive number; price is effective trade price (after slippage)
        signed_trade = qty if side.upper() == "BUY" else -qty
        old_qty = self._paper_qty
        new_qty = old_qty + signed_trade
        realized = 0.0
        fee = abs(qty * price) * (max(0.0, float(self.cfg.cost_bps)) / 10_000.0)
        # Impact cost model (optional, simple quadratic on notional fraction)
        impact = 0.0
        if self.cfg.impact_k and self.cfg.impact_k > 0.0:
            # Using a simple proxy: impact = k * (qty)^2 scaled by price
            impact = float(self.cfg.impact_k) * (qty**2) * price
        # Realized PnL occurs when we reduce or flip the existing position
        if (
            old_qty == 0.0
            or (old_qty > 0 and signed_trade > 0)
            or (old_qty < 0 and signed_trade < 0)
        ):
            # Adding to same-side position: recompute average price
            total_qty = abs(old_qty) + qty
            if total_qty > 0:
                if old_qty == 0.0:
                    self._paper_avg_px = price
                else:
                    # Weighted average by absolute quantities
                    self._paper_avg_px = (
                        abs(old_qty) * self._paper_avg_px + qty * price
                    ) / total_qty
        else:
            # Closing some or all of the existing position
            close_qty = min(abs(old_qty), qty)
            # Profit sign depends on existing position direction
            direction = 1.0 if old_qty > 0 else -1.0
            realized += close_qty * (price - self._paper_avg_px) * direction
            # If we fully closed and opened reverse in one trade
            if close_qty < qty:
                # Remainder opens a new position at trade price
                # New side is the trade's side
                self._paper_avg_px = price
            elif close_qty == abs(old_qty) and (abs(new_qty) > 1e-12):
                # Flipped with exact close and some remainder to opposite side
                self._paper_avg_px = price
        # Update paper qty and realized pnl (fees reduce PnL)
        self._paper_qty = new_qty
        self._paper_realized += realized - fee - impact
        unrealized = (
            (price - self._paper_avg_px) * self._paper_qty
            if abs(self._paper_qty) > 1e-12
            else 0.0
        )
        return {
            "paper_qty": self._paper_qty,
            "paper_avg_px": self._paper_avg_px,
            "realized_pnl": self._paper_realized,
            "unrealized_pnl": unrealized,
            "fee": fee,
            "impact": impact,
            "trade_price": price,
        }

    def get_exchange_position_qty(self) -> Tuple[float, Optional[Dict[str, Any]]]:
        # binance-connector UMFutures
        try:
            if hasattr(self.client, "position_information"):
                arr = self.client.position_information(symbol=self.symbol)
                if isinstance(arr, list) and arr:
                    pos = arr[0]
                    return float(pos.get("positionAmt", 0) or 0), pos
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
        # python-binance
        try:
            if hasattr(self.client, "futures_position_information"):
                arr = self.client.futures_position_information(symbol=self.symbol)
                if isinstance(arr, list) and arr:
                    pos = arr[0]
                    return float(pos.get("positionAmt", 0) or 0), pos
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
        return 0.0, None

    def get_paper_state(self) -> Dict[str, float]:
        """Return current paper trading state for equity calculations."""
        return {
            "paper_qty": float(self._paper_qty),
            "paper_avg_px": float(self._paper_avg_px),
            "realized_pnl": float(self._paper_realized),
        }

    def mirror_to_exchange(
        self, target_pos: float, last_price: float, dry_run: bool = True
    ) -> Optional[Dict]:
        """
        Mirror position in units of notional fraction relative to 1x. For demo, we place a market order for delta.
        target_pos: desired signed exposure fraction [-pos_max, pos_max]
        last_price: used to translate to quantity; here we use a nominal base notional.
        """
        # Ensure filters for precision
        self.ensure_exchange_filters()
        # Apply no-trade band: skip tiny rebalances
        if abs(float(target_pos) - float(self._pos)) < max(
            0.0, float(self.cfg.rebalance_min_pos_delta or 0.0)
        ):
            return None
        # Map target position fraction to target quantity using configurable base notional
        base_notional = max(1e-6, float(self.cfg.base_notional))
        target_qty = target_pos * base_notional / max(1e-6, last_price)
        # Read current exchange position
        exch_qty, _ = self.get_exchange_position_qty()
        delta_qty = target_qty - exch_qty
        if abs(delta_qty) < 1e-9:
            # Keep local pos in sync with target
            self._pos = target_pos
            return None
        side = "BUY" if delta_qty > 0 else "SELL"
        qty = self.clamp_qty(abs(delta_qty), last_price)
        # Apply ADV cap in notional if configured and adv20 is known
        adv_cap = max(0.0, float(self.cfg.adv_cap_pct or 0.0))
        adv_usd = max(0.0, float(self.adv20_usd or 0.0))
        if adv_cap > 0.0 and adv_usd > 0.0:
            max_notional = adv_usd * (adv_cap / 100.0)
            trade_notional = qty * last_price
            if trade_notional > max_notional and max_notional > 0.0:
                qty = max_notional / max(1e-6, last_price)
        if qty <= 0:
            self._pos = target_pos
            return None
        if dry_run:
            self._pos = target_pos
            # Apply slippage and simulate PnL/fees without touching the exchange
            eff_price = self._apply_slippage(side, last_price)
            sim = self._simulate_trade(side, abs(qty), eff_price)
            return {
                "dry_run": True,
                "side": side,
                "qty": qty,
                "price": eff_price,
                "mid_price": last_price,
                "exch_qty": exch_qty,
                "target_qty": target_qty,
                "delta_qty": delta_qty,
                "paper_qty": sim.get("paper_qty"),
                "paper_avg_px": sim.get("paper_avg_px"),
                "realized_pnl": sim.get("realized_pnl"),
                "unrealized_pnl": sim.get("unrealized_pnl"),
                "fee": sim.get("fee"),
                "impact": sim.get("impact"),
            }
        # Try to import a specific client exception type from python-binance dynamically
        try:
            mod = importlib.import_module("binance.error")
            ClientError = getattr(mod, "ClientError")  # type: ignore
        except (
            ImportError,
            AttributeError,
        ):  # pragma: no cover - missing package or api change

            class ClientError(Exception):  # type: ignore
                pass

        try:
            resp = self.client.new_order(
                symbol=self.symbol, side=side, type="MARKET", quantity=qty
            )
            # After send, refresh position and reconcile
            new_exch_qty, _ = self.get_exchange_position_qty()
            self._pos = target_pos
            return {
                "action": "sent",
                "side": side,
                "qty": qty,
                "price": last_price,
                "exch_qty_before": exch_qty,
                "exch_qty_after": new_exch_qty,
                "target_qty": target_qty,
                "reconciled": abs(new_exch_qty - target_qty)
                <= max(self._step_size or 1e-6, 1e-6),
                "raw": resp,
            }
        except ClientError as e:
            return {"error": f"order_failed: {e}", "side": side, "qty": qty}

    def mirror_passive_then_cross(
        self,
        target_pos: float,
        last_price: float,
        book: Optional[Dict[str, float]] = None,
        timeout_s: float = 5.0,
        dry_run: bool = True,
    ) -> Optional[Dict]:
        """Attempt passive fill at top-of-book for up to timeout, then cross remaining.
        Paper simulation only: uses best bid/ask and available sizes as a rough cap for passive fills.
        """
        # Ensure filters for precision
        self.ensure_exchange_filters()
        # Apply no-trade band
        if abs(float(target_pos) - float(self._pos)) < max(
            0.0, float(self.cfg.rebalance_min_pos_delta or 0.0)
        ):
            return None
        # Map target position to target quantity
        base_notional = max(1e-6, float(self.cfg.base_notional))
        target_qty = target_pos * base_notional / max(1e-6, last_price)
        exch_qty, _ = self.get_exchange_position_qty()
        delta_qty = target_qty - exch_qty
        if abs(delta_qty) < 1e-9:
            self._pos = target_pos
            return None
        side = "BUY" if delta_qty > 0 else "SELL"
        qty = self.clamp_qty(abs(delta_qty), last_price)
        # ADV cap by notional
        adv_cap = max(0.0, float(self.cfg.adv_cap_pct or 0.0))
        adv_usd = max(0.0, float(self.adv20_usd or 0.0))
        if adv_cap > 0.0 and adv_usd > 0.0:
            max_notional = adv_usd * (adv_cap / 100.0)
            trade_notional = qty * last_price
            if trade_notional > max_notional and max_notional > 0.0:
                qty = max_notional / max(1e-6, last_price)
        if qty <= 0:
            self._pos = target_pos
            return None
        # Passive phase: rest at top of book price
        bid = float(book.get("bid")) if (book and book.get("bid") is not None) else None
        ask = float(book.get("ask")) if (book and book.get("ask") is not None) else None
        bid_qty = (
            float(book.get("bid_qty"))
            if (book and book.get("bid_qty") is not None)
            else 0.0
        )
        ask_qty = (
            float(book.get("ask_qty"))
            if (book and book.get("ask_qty") is not None)
            else 0.0
        )
        if side == "BUY":
            passive_px = bid if bid is not None else last_price
            book_qty = max(0.0, bid_qty)
        else:
            passive_px = ask if ask is not None else last_price
            book_qty = max(0.0, ask_qty)
        # Simple passive fill model: fraction of displayed top size within timeout
        # This is conservative and prevents full fills unless qty is small.
        passive_fill_cap = max(0.0, 0.25 * book_qty)  # 25% of top size
        passive_fill_qty = min(qty, passive_fill_cap)
        # Simulate passive trade (no slippage beyond cost/impact handled internally by _simulate_trade)
        total_fee = 0.0
        total_impact = 0.0
        weighted_price_numer = 0.0
        total_exec_qty = 0.0
        if dry_run and passive_fill_qty > 0:
            sim_p = self._simulate_trade(side, passive_fill_qty, passive_px)
            total_fee += float(sim_p.get("fee") or 0.0)
            total_impact += float(sim_p.get("impact") or 0.0)
            weighted_price_numer += passive_fill_qty * passive_px
            total_exec_qty += passive_fill_qty
        # Remaining to cross
        cross_qty = max(0.0, qty - passive_fill_qty)
        cross_px = last_price
        if dry_run and cross_qty > 0:
            eff_cross_px = self._apply_slippage(side, cross_px)
            sim_c = self._simulate_trade(side, cross_qty, eff_cross_px)
            total_fee += float(sim_c.get("fee") or 0.0)
            total_impact += float(sim_c.get("impact") or 0.0)
            weighted_price_numer += cross_qty * eff_cross_px
            total_exec_qty += cross_qty
        # Update desired position target (paper/exchange syncing)
        self._pos = target_pos
        # Build response
        avg_px = (
            (weighted_price_numer / max(1e-9, total_exec_qty))
            if total_exec_qty > 0
            else last_price
        )
        resp = {
            "dry_run": dry_run,
            "mode": "passive_then_cross",
            "side": side,
            "qty": qty,
            "price": avg_px,
            "mid_price": last_price,
            "passive_qty": passive_fill_qty,
            "passive_price": passive_px,
            "cross_qty": cross_qty,
            "cross_price": cross_px,
            "waited_ms": int(max(0.0, float(timeout_s)) * 1000.0),
            "exch_qty": exch_qty,
            "target_qty": target_qty,
            "delta_qty": delta_qty,
            "paper_qty": getattr(self, "_paper_qty", 0.0),
            "paper_avg_px": getattr(self, "_paper_avg_px", 0.0),
            "realized_pnl": getattr(self, "_paper_realized", 0.0),
            "unrealized_pnl": (
                (avg_px - getattr(self, "_paper_avg_px", 0.0))
                * getattr(self, "_paper_qty", 0.0)
                if abs(getattr(self, "_paper_qty", 0.0)) > 1e-12
                else 0.0
            ),
            "fee": total_fee,
            "impact": total_impact,
        }
        return resp
