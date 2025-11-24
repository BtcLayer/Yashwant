"""
Production Integration Example for MetaStackerBandit
Demonstrates how to integrate all production components
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pytz

# Import production components
from live_demo.schemas.production_schemas import ProductionSchemas, FieldDefinition
from live_demo.emitters.production_emitter import ProductionLogEmitter, EmitterConfig
from live_demo.alerts.alert_router import AlertRouter, AlertConfig, AlertLevel
from live_demo.security.data_sanitizer import DataSanitizer, sanitize_log_record, hash_identifiers

IST = pytz.timezone("Asia/Kolkata")

class ProductionIntegration:
    """Production integration example showing how to use all components together"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        
        # Initialize production components
        self.schemas = ProductionSchemas()
        self.emitter = self._setup_emitter()
        self.alert_router = self._setup_alert_router()
        self.sanitizer = DataSanitizer()
        
        # Metrics tracking
        self.metrics = {}
        self.last_health_check = datetime.now(IST)
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load production configuration"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Default production configuration
        return {
            "emitter": {
                "base_dir": "paper_trading_outputs/logs",
                "max_file_size_mb": 100,
                "max_files": 10,
                "compression": True,
                "sampling_rate": 1.0,
                "retry_attempts": 3,
                "enable_async": True
            },
            "alerts": {
                "slack_webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                "slack_channel": "#trading-alerts",
                "smtp_server": os.getenv("SMTP_SERVER"),
                "smtp_username": os.getenv("SMTP_USERNAME"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "email_to": os.getenv("EMAIL_TO", "").split(",")
            },
            "security": {
                "salt": os.getenv("SANITIZER_SALT", "default_salt_change_in_production")
            }
        }
    
    def _setup_emitter(self) -> ProductionLogEmitter:
        """Setup production log emitter"""
        emitter_config = EmitterConfig(**self.config["emitter"])
        return ProductionLogEmitter(emitter_config)
    
    def _setup_alert_router(self) -> AlertRouter:
        """Setup alert router"""
        alert_config = AlertConfig(**self.config["alerts"])
        return AlertRouter(alert_config)
    
    def log_market_data(self, ts: int, asset: str, bar_id: int, mid: float, 
                       bid1: float, ask1: float, spread_bps: float, rv_1h: float):
        """Log market data with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "ts_ist": datetime.fromtimestamp(ts/1000, IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "mid": mid,
            "bid1": bid1,
            "ask1": ask1,
            "spread_bps": spread_bps,
            "rv_1h": rv_1h,
            "book_lag_ms": 0.0,
            "missing_pct": 0.0,
            "dup_bars": 0,
            "non_monotonic_flag": False,
            "source_seq": 0
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "market_data")
        if validation_result["errors"]:
            print(f"Market data validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "market_data")
        
        # Emit log
        self.emitter.emit_market_data(sanitized_record)
        
        # Update metrics
        self.metrics["last_market_data"] = datetime.now(IST).isoformat()
    
    def log_signals(self, ts: int, asset: str, bar_id: int, S_top: float, S_bot: float,
                   cohort_sizes: Dict[str, int], feature_version: str = "v3.2.1"):
        """Log signals with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "ts_ist": datetime.fromtimestamp(ts/1000, IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "S_top": S_top,
            "S_bot": S_bot,
            "F_top_norm": S_top / max(abs(S_top), 1e-6),
            "F_bot_norm": S_bot / max(abs(S_bot), 1e-6),
            "rho_top_mean": 0.0,
            "rho_bot_mean": 0.0,
            "cohort_top_sz": cohort_sizes.get("top", 0),
            "cohort_bot_sz": cohort_sizes.get("bot", 0),
            "feature_version": feature_version,
            "signal_version": "s_2025-10-01",
            "zscore_clip_events": 0
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "signals")
        if validation_result["errors"]:
            print(f"Signals validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "signals")
        
        # Emit log
        self.emitter.emit_signals(sanitized_record)
        
        # Update metrics
        self.metrics["last_signals"] = datetime.now(IST).isoformat()
    
    def log_ensemble(self, ts: int, asset: str, bar_id: int, model_out: Dict[str, Any],
                    bandit_state: Optional[Dict[str, Any]] = None, ic_200: float = 0.0):
        """Log ensemble predictions with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "ts_ist": datetime.fromtimestamp(ts/1000, IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "pred_xgb": model_out.get("pred_xgb", 0.0),
            "pred_hgb": model_out.get("pred_hgb", 0.0),
            "pred_lasso": model_out.get("pred_lasso", 0.0),
            "pred_logit": model_out.get("pred_logit", 0.0),
            "pred_stack": model_out.get("s_model", 0.0),
            "pred_bma": model_out.get("s_model", 0.0),
            "bandit_arm": bandit_state.get("chosen_arm", "model") if bandit_state else "model",
            "bandit_weights": bandit_state.get("weights", {}) if bandit_state else {},
            "reward_prev": bandit_state.get("last_reward", 0.0) if bandit_state else 0.0,
            "regret_est": 0.0,
            "exp_rate": 0.0,
            "a": -8.5,
            "b": 1.12,
            "score_cal_bps": 3.6,
            "in_band_flag": True,
            "ic_200": ic_200,
            "oof_fold": 2,
            "cv_id": "WF2",
            "train_span": "2025-07-01..2025-09-30",
            "embargo_purge_ok": True,
            "git_sha": "9abcf12"
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "ensemble")
        if validation_result["errors"]:
            print(f"Ensemble validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "ensemble")
        
        # Emit log
        self.emitter.emit_ensemble(sanitized_record)
        
        # Update metrics
        self.metrics["last_ensemble"] = datetime.now(IST).isoformat()
    
    def log_execution(self, ts: int, asset: str, bar_id: int, side: str, order_type: str,
                     fill_px: float, fill_qty: float, slip_bps: float, route: str = "BINANCE"):
        """Log execution with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "decision_time_ist": datetime.fromtimestamp(ts/1000, IST).isoformat(),
            "exec_time_ist": datetime.now(IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "side": side,
            "order_type": order_type,
            "limit_px": fill_px,
            "fill_px": fill_px,
            "fill_qty": fill_qty,
            "slip_bps_mkt": slip_bps,
            "route": route,
            "rejections": 0,
            "ioc_ms": 0.0,
            "throttle_guard_events": 0
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "execution")
        if validation_result["errors"]:
            print(f"Execution validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "execution")
        
        # Emit log
        self.emitter.emit_execution(sanitized_record)
        
        # Update metrics
        self.metrics["last_execution"] = datetime.now(IST).isoformat()
    
    def log_costs(self, ts: int, asset: str, bar_id: int, trade_notional: float,
                 cost_usd: float, pnl_usd: float, impact_bps: float = 0.0):
        """Log costs with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "ts_ist": datetime.fromtimestamp(ts/1000, IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "fee_bps": 2.0,
            "slip_bps": 3.0,
            "impact_bps": impact_bps,
            "impact_k": 2.0,
            "adv_ref": 25000000.0,
            "trade_notional": trade_notional,
            "cost_usd": cost_usd,
            "pnl_usd_fill": pnl_usd,
            "pnl_usd_bar": pnl_usd,
            "pnl_attrib": {
                "alpha": pnl_usd * 0.8,
                "timing": pnl_usd * 0.1,
                "fees": -cost_usd,
                "impact": -impact_bps * trade_notional / 10000
            }
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "costs")
        if validation_result["errors"]:
            print(f"Costs validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "costs")
        
        # Emit log
        self.emitter.emit_costs(sanitized_record)
        
        # Update metrics
        self.metrics["last_costs"] = datetime.now(IST).isoformat()
    
    def log_health(self, sharpe_1d: float, max_dd: float, hit_rate: float,
                  turnover_bps: float, capacity_participation: float, ic_drift: float):
        """Log health metrics with production schemas and sanitization"""
        
        # Create raw record
        raw_record = {
            "ts_ist": datetime.now(IST).isoformat(),
            "asset": "ALL",
            "Sharpe_roll_1d": sharpe_1d,
            "Sortino_1w": sharpe_1d * 1.2,
            "max_dd_to_date": max_dd,
            "time_in_mkt": 0.11,
            "hit_rate_w": hit_rate,
            "turnover_bps_day": turnover_bps,
            "capacity_participation": capacity_participation,
            "ic_drift": ic_drift,
            "calibration_drift": 0.0,
            "leakage_flag": False,
            "same_bar_roundtrip_flag": False
        }
        
        # Validate against schema
        validation_result = self.schemas.validate_record(raw_record, "health")
        if validation_result["errors"]:
            print(f"Health validation errors: {validation_result['errors']}")
            return
        
        # Sanitize data
        sanitized_record = sanitize_log_record(validation_result["validated"], "health")
        
        # Emit log
        self.emitter.emit_health(sanitized_record)
        
        # Update metrics
        self.metrics["last_health"] = datetime.now(IST).isoformat()
    
    def evaluate_alerts(self, metrics: Dict[str, Any]):
        """Evaluate alerts based on current metrics"""
        self.alert_router.evaluate_alerts(metrics)
    
    def get_production_stats(self) -> Dict[str, Any]:
        """Get comprehensive production statistics"""
        return {
            "timestamp": datetime.now(IST).isoformat(),
            "emitter_stats": self.emitter.get_stats(),
            "alert_stats": self.alert_router.get_stats(),
            "sanitizer_stats": self.sanitizer.get_stats(),
            "metrics": self.metrics
        }
    
    def close(self):
        """Close all production components"""
        self.emitter.close()
        self.alert_router.close()
        print("Production integration closed")

# Example usage
def example_production_usage():
    """Example of how to use production integration"""
    
    # Initialize production integration
    integration = ProductionIntegration()
    
    # Example market data logging
    integration.log_market_data(
        ts=1698000000000,  # Unix timestamp in ms
        asset="BTC-PERP",
        bar_id=9675312,
        mid=66123.5,
        bid1=66120.0,
        ask1=66125.0,
        spread_bps=7.6,
        rv_1h=0.23
    )
    
    # Example signals logging
    integration.log_signals(
        ts=1698000000000,
        asset="BTC-PERP",
        bar_id=9675312,
        S_top=0.34,
        S_bot=-0.12,
        cohort_sizes={"top": 142, "bot": 137}
    )
    
    # Example ensemble logging
    integration.log_ensemble(
        ts=1698000000000,
        asset="BTC-PERP",
        bar_id=9675312,
        model_out={"s_model": 0.65, "p_up": 0.6, "p_down": 0.2, "p_neutral": 0.2},
        bandit_state={"chosen_arm": "stacked", "weights": {"stacked": 0.46}},
        ic_200=0.07
    )
    
    # Example execution logging
    integration.log_execution(
        ts=1698000000000,
        asset="BTC-PERP",
        bar_id=9675312,
        side="SELL",
        order_type="LIMIT",
        fill_px=66118.0,
        fill_qty=0.42,
        slip_bps=2.8
    )
    
    # Example costs logging
    integration.log_costs(
        ts=1698000000000,
        asset="BTC-PERP",
        bar_id=9675313,
        trade_notional=27769.6,
        cost_usd=14.7,
        pnl_usd=62.1,
        impact_bps=1.2
    )
    
    # Example health logging
    integration.log_health(
        sharpe_1d=3.2,
        max_dd=-0.07,
        hit_rate=0.56,
        turnover_bps=1840.0,
        capacity_participation=0.52,
        ic_drift=-0.03
    )
    
    # Example alert evaluation
    metrics = {
        "ic_drift": -0.04,
        "max_dd_to_date": -0.025,
        "avg_cost_bps": 8.5,
        "capacity_participation": 0.035,
        "book_lag_ms": 6000,
        "leakage_flag": False,
        "same_bar_roundtrip_flag": False,
        "reject_rate": 0.06
    }
    integration.evaluate_alerts(metrics)
    
    # Get production statistics
    stats = integration.get_production_stats()
    print("Production Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Close integration
    integration.close()

if __name__ == "__main__":
    example_production_usage()
