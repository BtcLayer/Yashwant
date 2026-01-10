"""
Production Log Schemas for MetaStackerBandit
Complete field definitions with dtypes, units, null policies, and validation
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


class DataType(Enum):
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    TIMESTAMP = "timestamp"
    JSON = "json"


class NullPolicy(Enum):
    NEVER_NULL = "never_null"
    ALLOW_NULL = "allow_null"
    DEFAULT_NULL = "default_null"


@dataclass
class FieldDefinition:
    field: str
    dtype: DataType
    units: Optional[str] = None
    null_policy: NullPolicy = NullPolicy.ALLOW_NULL
    default_value: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""
    example: Any = None


class ProductionSchemas:
    """Production-ready log schemas with comprehensive field definitions"""

    # Data/Market Ingest Schema
    MARKET_DATA_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "mid",
            DataType.FLOAT,
            "USD",
            NullPolicy.NEVER_NULL,
            min_value=0.0,
            description="Mid price",
            example=66123.5,
        ),
        FieldDefinition(
            "bid1",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Best bid price",
            example=66120.0,
        ),
        FieldDefinition(
            "ask1",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Best ask price",
            example=66125.0,
        ),
        FieldDefinition(
            "spread_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Bid-ask spread in basis points",
            example=7.6,
        ),
        FieldDefinition(
            "obi_10",
            DataType.FLOAT,
            "ratio",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Order book imbalance (10 levels)",
            example=0.45,
        ),
        FieldDefinition(
            "rv_1h",
            DataType.FLOAT,
            "annualized_vol",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="1-hour realized volatility",
            example=0.23,
        ),
        FieldDefinition(
            "funding_8h",
            DataType.FLOAT,
            "rate",
            NullPolicy.ALLOW_NULL,
            description="8-hour funding rate",
            example=0.0001,
        ),
        FieldDefinition(
            "book_lag_ms",
            DataType.FLOAT,
            "milliseconds",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Order book update latency",
            example=45.2,
        ),
        FieldDefinition(
            "missing_pct",
            DataType.FLOAT,
            "percentage",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=100.0,
            description="Missing data percentage",
            example=0.0,
        ),
        FieldDefinition(
            "dup_bars",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Duplicate bars detected",
            example=0,
        ),
        FieldDefinition(
            "non_monotonic_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Non-monotonic timestamp flag",
            example=False,
        ),
        FieldDefinition(
            "source_seq",
            DataType.INTEGER,
            "sequence",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Source sequence number",
            example=12345,
        ),
    ]

    # Signals/Cohorts Schema
    SIGNALS_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "S_top",
            DataType.FLOAT,
            "signal_strength",
            NullPolicy.ALLOW_NULL,
            description="Top cohort signal strength",
            example=0.34,
        ),
        FieldDefinition(
            "S_bot",
            DataType.FLOAT,
            "signal_strength",
            NullPolicy.ALLOW_NULL,
            description="Bottom cohort signal strength",
            example=-0.12,
        ),
        FieldDefinition(
            "F_top_norm",
            DataType.FLOAT,
            "normalized_signal",
            NullPolicy.ALLOW_NULL,
            description="Normalized top cohort flow",
            example=0.021,
        ),
        FieldDefinition(
            "F_bot_norm",
            DataType.FLOAT,
            "normalized_signal",
            NullPolicy.ALLOW_NULL,
            description="Normalized bottom cohort flow",
            example=-0.009,
        ),
        FieldDefinition(
            "rho_top_mean",
            DataType.FLOAT,
            "correlation",
            NullPolicy.ALLOW_NULL,
            min_value=-1.0,
            max_value=1.0,
            description="Top cohort correlation",
            example=0.78,
        ),
        FieldDefinition(
            "rho_bot_mean",
            DataType.FLOAT,
            "correlation",
            NullPolicy.ALLOW_NULL,
            min_value=-1.0,
            max_value=1.0,
            description="Bottom cohort correlation",
            example=0.31,
        ),
        FieldDefinition(
            "cohort_top_sz",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Top cohort size",
            example=142,
        ),
        FieldDefinition(
            "cohort_bot_sz",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Bottom cohort size",
            example=137,
        ),
        FieldDefinition(
            "feature_version",
            DataType.STRING,
            "version",
            NullPolicy.ALLOW_NULL,
            description="Feature engineering version",
            example="v3.2.1",
        ),
        FieldDefinition(
            "signal_version",
            DataType.STRING,
            "version",
            NullPolicy.ALLOW_NULL,
            description="Signal processing version",
            example="s_2025-10-01",
        ),
        FieldDefinition(
            "zscore_clip_events",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Z-score clipping events",
            example=0,
        ),
    ]

    # Ensemble/Models Schema
    ENSEMBLE_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "pred_xgb",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="XGBoost prediction",
            example=12.4,
        ),
        FieldDefinition(
            "pred_hgb",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="HistGradientBoosting prediction",
            example=9.7,
        ),
        FieldDefinition(
            "pred_lasso",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="Lasso prediction",
            example=4.1,
        ),
        FieldDefinition(
            "pred_logit",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="Logistic regression prediction",
            example=6.2,
        ),
        FieldDefinition(
            "pred_stack",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="Stacked ensemble prediction",
            example=10.8,
        ),
        FieldDefinition(
            "pred_bma",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="Bayesian model averaging",
            example=11.2,
        ),
        FieldDefinition(
            "bandit_arm",
            DataType.STRING,
            "arm_name",
            NullPolicy.ALLOW_NULL,
            description="Selected bandit arm",
            example="stacked",
        ),
        FieldDefinition(
            "bandit_weights",
            DataType.JSON,
            "weights",
            NullPolicy.ALLOW_NULL,
            description="Bandit arm weights",
            example={"stacked": 0.46, "top_follow": 0.22},
        ),
        FieldDefinition(
            "reward_prev",
            DataType.FLOAT,
            "reward",
            NullPolicy.ALLOW_NULL,
            description="Previous reward",
            example=0.0009,
        ),
        FieldDefinition(
            "regret_est",
            DataType.FLOAT,
            "regret",
            NullPolicy.ALLOW_NULL,
            description="Estimated regret",
            example=-0.0002,
        ),
        FieldDefinition(
            "exp_rate",
            DataType.FLOAT,
            "rate",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Exploration rate",
            example=0.06,
        ),
        FieldDefinition(
            "a",
            DataType.FLOAT,
            "coefficient",
            NullPolicy.ALLOW_NULL,
            description="Calibration coefficient a",
            example=-8.5,
        ),
        FieldDefinition(
            "b",
            DataType.FLOAT,
            "coefficient",
            NullPolicy.ALLOW_NULL,
            description="Calibration coefficient b",
            example=1.12,
        ),
        FieldDefinition(
            "score_cal_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            description="Calibrated score in bps",
            example=3.6,
        ),
        FieldDefinition(
            "in_band_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="In no-trade band flag",
            example=True,
        ),
        FieldDefinition(
            "ic_200",
            DataType.FLOAT,
            "correlation",
            NullPolicy.ALLOW_NULL,
            min_value=-1.0,
            max_value=1.0,
            description="200-bar information coefficient",
            example=0.07,
        ),
        FieldDefinition(
            "oof_fold",
            DataType.INTEGER,
            "fold",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Out-of-fold fold number",
            example=2,
        ),
        FieldDefinition(
            "cv_id",
            DataType.STRING,
            "id",
            NullPolicy.ALLOW_NULL,
            description="Cross-validation ID",
            example="WF2",
        ),
        FieldDefinition(
            "train_span",
            DataType.STRING,
            "date_range",
            NullPolicy.ALLOW_NULL,
            description="Training data span",
            example="2025-07-01..2025-09-30",
        ),
        FieldDefinition(
            "embargo_purge_ok",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Embargo purge OK flag",
            example=True,
        ),
        FieldDefinition(
            "git_sha",
            DataType.STRING,
            "hash",
            NullPolicy.ALLOW_NULL,
            description="Git commit SHA",
            example="9abcf12",
        ),
    ]

    # Risk/Sizing Schema
    RISK_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "forecast_vol_20",
            DataType.FLOAT,
            "annualized_vol",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="20-bar forecast volatility",
            example=0.18,
        ),
        FieldDefinition(
            "target_vol_ann",
            DataType.FLOAT,
            "annualized_vol",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Target annualized volatility",
            example=0.20,
        ),
        FieldDefinition(
            "raw_score",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            description="Raw model score",
            example=0.65,
        ),
        FieldDefinition(
            "position_before",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            description="Position before rebalance",
            example=0.25,
        ),
        FieldDefinition(
            "position_after",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            description="Position after rebalance",
            example=0.30,
        ),
        FieldDefinition(
            "delta_pos",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            description="Position change",
            example=0.05,
        ),
        FieldDefinition(
            "notional_target_usd",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Target notional USD",
            example=15000.0,
        ),
        FieldDefinition(
            "leverage_x",
            DataType.FLOAT,
            "multiplier",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Leverage multiplier",
            example=1.0,
        ),
        FieldDefinition(
            "reduce_for_spread_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Reduce for spread flag",
            example=False,
        ),
        FieldDefinition(
            "funding_bias",
            DataType.FLOAT,
            "bias",
            NullPolicy.ALLOW_NULL,
            description="Funding bias adjustment",
            example=0.001,
        ),
    ]

    # Execution Schema
    EXECUTION_SCHEMA = [
        FieldDefinition(
            "decision_time_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="Decision timestamp IST",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "exec_time_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="Execution timestamp IST",
            example="2025-10-22T10:10:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "side",
            DataType.STRING,
            "side",
            NullPolicy.NEVER_NULL,
            allowed_values=["BUY", "SELL"],
            description="Order side",
            example="SELL",
        ),
        FieldDefinition(
            "order_type",
            DataType.STRING,
            "type",
            NullPolicy.NEVER_NULL,
            allowed_values=["MARKET", "LIMIT", "STOP"],
            description="Order type",
            example="LIMIT",
        ),
        FieldDefinition(
            "limit_px",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Limit price",
            example=66123.5,
        ),
        FieldDefinition(
            "fill_px",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Fill price",
            example=66118.0,
        ),
        FieldDefinition(
            "fill_qty",
            DataType.FLOAT,
            "contracts",
            NullPolicy.ALLOW_NULL,
            description="Fill quantity",
            example=0.42,
        ),
        FieldDefinition(
            "slip_bps_mkt",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            description="Market slippage in bps",
            example=2.8,
        ),
        FieldDefinition(
            "route",
            DataType.STRING,
            "exchange",
            NullPolicy.ALLOW_NULL,
            description="Execution route",
            example="HL-REST",
        ),
        FieldDefinition(
            "rejections",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Order rejections",
            example=0,
        ),
        FieldDefinition(
            "ioc_ms",
            DataType.FLOAT,
            "milliseconds",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="IOC timeout in ms",
            example=540.0,
        ),
        FieldDefinition(
            "throttle_guard_events",
            DataType.INTEGER,
            "count",
            NullPolicy.ALLOW_NULL,
            min_value=0,
            description="Throttle guard events",
            example=0,
        ),
    ]

    # Costs & PnL Schema
    COSTS_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:10:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675313,
        ),
        FieldDefinition(
            "fee_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Fee in basis points",
            example=2.0,
        ),
        FieldDefinition(
            "slip_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Slippage in basis points",
            example=3.0,
        ),
        FieldDefinition(
            "impact_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Market impact in bps",
            example=1.2,
        ),
        FieldDefinition(
            "impact_k",
            DataType.FLOAT,
            "coefficient",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Impact coefficient",
            example=2.0,
        ),
        FieldDefinition(
            "adv_ref",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="ADV reference",
            example=25000000.0,
        ),
        FieldDefinition(
            "trade_notional",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Trade notional",
            example=27769.6,
        ),
        FieldDefinition(
            "cost_usd",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            description="Total cost USD",
            example=14.7,
        ),
        FieldDefinition(
            "pnl_usd_fill",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            description="PnL per fill USD",
            example=62.1,
        ),
        FieldDefinition(
            "pnl_usd_bar",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            description="PnL per bar USD",
            example=55.4,
        ),
        FieldDefinition(
            "pnl_attrib",
            DataType.JSON,
            "attribution",
            NullPolicy.ALLOW_NULL,
            description="PnL attribution breakdown",
            example={"alpha": 71.2, "timing": -1.1, "fees": -5.6, "impact": -9.1},
        ),
    ]

    # Health/Post-trade Schema
    HEALTH_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:10:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Asset or ALL for aggregate",
            example="ALL",
        ),
        FieldDefinition(
            "Sharpe_roll_1d",
            DataType.FLOAT,
            "ratio",
            NullPolicy.ALLOW_NULL,
            description="1-day rolling Sharpe ratio",
            example=3.2,
        ),
        FieldDefinition(
            "Sortino_1w",
            DataType.FLOAT,
            "ratio",
            NullPolicy.ALLOW_NULL,
            description="1-week Sortino ratio",
            example=4.8,
        ),
        FieldDefinition(
            "max_dd_to_date",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            max_value=0.0,
            description="Maximum drawdown to date",
            example=-0.07,
        ),
        FieldDefinition(
            "time_in_mkt",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Time in market",
            example=0.11,
        ),
        FieldDefinition(
            "hit_rate_w",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Weekly hit rate",
            example=0.56,
        ),
        FieldDefinition(
            "turnover_bps_day",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Daily turnover in bps",
            example=1840.0,
        ),
        FieldDefinition(
            "capacity_participation",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="ADV participation",
            example=0.52,
        ),
        FieldDefinition(
            "ic_drift",
            DataType.FLOAT,
            "correlation",
            NullPolicy.ALLOW_NULL,
            description="IC drift",
            example=-0.03,
        ),
        FieldDefinition(
            "calibration_drift",
            DataType.FLOAT,
            "drift",
            NullPolicy.ALLOW_NULL,
            description="Calibration drift",
            example=0.012,
        ),
        FieldDefinition(
            "leakage_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Data leakage flag",
            example=False,
        ),
        FieldDefinition(
            "same_bar_roundtrip_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Same bar roundtrip flag",
            example=False,
        ),
        FieldDefinition(
            "ws_lag_ms",
            DataType.FLOAT,
            "milliseconds",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Websocket latency in milliseconds",
            example=45.2,
        ),
        FieldDefinition(
            "is_connected",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="Exchange connectivity status",
            example=True,
        ),
    ]

    # Repro/Config Schema
    REPRO_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "git_sha",
            DataType.STRING,
            "hash",
            NullPolicy.ALLOW_NULL,
            description="Git commit SHA",
            example="9abcf12",
        ),
        FieldDefinition(
            "model_version",
            DataType.STRING,
            "version",
            NullPolicy.ALLOW_NULL,
            description="Model version",
            example="v2.1.3",
        ),
        FieldDefinition(
            "feature_version",
            DataType.STRING,
            "version",
            NullPolicy.ALLOW_NULL,
            description="Feature version",
            example="v3.2.1",
        ),
        FieldDefinition(
            "seed",
            DataType.INTEGER,
            "seed",
            NullPolicy.ALLOW_NULL,
            description="Random seed",
            example=42,
        ),
        FieldDefinition(
            "train_start_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.ALLOW_NULL,
            description="Training start IST",
            example="2025-07-01T00:00:00+05:30",
        ),
        FieldDefinition(
            "train_end_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.ALLOW_NULL,
            description="Training end IST",
            example="2025-09-30T23:59:59+05:30",
        ),
        FieldDefinition(
            "hyperparams_hash",
            DataType.STRING,
            "hash",
            NullPolicy.ALLOW_NULL,
            description="Hyperparameters hash",
            example="a1b2c3d4",
        ),
        FieldDefinition(
            "data_hash",
            DataType.STRING,
            "hash",
            NullPolicy.ALLOW_NULL,
            description="Training data hash",
            example="e5f6g7h8",
        ),
        FieldDefinition(
            "adv_method",
            DataType.STRING,
            "method",
            NullPolicy.ALLOW_NULL,
            description="ADV calculation method",
            example="rolling_20d",
        ),
    ]

    # Order Intent Schema
    ORDER_INTENT_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "bar_id_decision",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Bar ID when decision made",
            example=9675312,
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "side",
            DataType.STRING,
            "side",
            NullPolicy.NEVER_NULL,
            allowed_values=["BUY", "SELL", "HOLD"],
            description="Order side",
            example="BUY",
        ),
        FieldDefinition(
            "intent_qty",
            DataType.FLOAT,
            "fraction",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Intended quantity",
            example=0.25,
        ),
        FieldDefinition(
            "intent_notional",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Intended notional USD",
            example=15000.0,
        ),
        FieldDefinition(
            "reason_codes",
            DataType.JSON,
            "flags",
            NullPolicy.ALLOW_NULL,
            description="Reason codes for decision",
            example={"threshold": True, "band": False, "spread_guard": True},
        ),
        FieldDefinition(
            "signal_strength",
            DataType.FLOAT,
            "strength",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Signal strength",
            example=0.34,
        ),
        FieldDefinition(
            "model_confidence",
            DataType.FLOAT,
            "confidence",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Model confidence",
            example=0.78,
        ),
        FieldDefinition(
            "risk_score",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Risk score",
            example=0.23,
        ),
        FieldDefinition(
            "market_conditions",
            DataType.JSON,
            "conditions",
            NullPolicy.ALLOW_NULL,
            description="Market conditions",
            example={"spread_bps": 7.6, "volatility": 0.23, "volume": 1500.0},
        ),
    ]

    # Feature Log Schema
    FEATURE_LOG_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "mom_3",
            DataType.FLOAT,
            "return",
            NullPolicy.ALLOW_NULL,
            description="3-bar momentum",
            example=0.0023,
        ),
        FieldDefinition(
            "mr_ema20",
            DataType.FLOAT,
            "return",
            NullPolicy.ALLOW_NULL,
            description="Mean reversion EMA20",
            example=-0.0015,
        ),
        FieldDefinition(
            "obi_10",
            DataType.FLOAT,
            "ratio",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Order book imbalance 10 levels",
            example=0.45,
        ),
        FieldDefinition(
            "spread_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Bid-ask spread",
            example=7.6,
        ),
        FieldDefinition(
            "rv_1h",
            DataType.FLOAT,
            "annualized_vol",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="1-hour realized volatility",
            example=0.23,
        ),
        FieldDefinition(
            "regime_bucket",
            DataType.STRING,
            "regime",
            NullPolicy.ALLOW_NULL,
            allowed_values=[
                "high_vol_high_vol",
                "high_vol_low_vol",
                "low_vol_high_vol",
                "low_vol_low_vol",
            ],
            description="Market regime classification",
            example="high_vol_high_vol",
        ),
        FieldDefinition(
            "funding_delta",
            DataType.FLOAT,
            "rate",
            NullPolicy.ALLOW_NULL,
            description="Funding rate change",
            example=0.0001,
        ),
        FieldDefinition(
            "adv20",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="20-day average daily volume",
            example=25000000.0,
        ),
        FieldDefinition(
            "volume_ratio",
            DataType.FLOAT,
            "ratio",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Current volume vs average",
            example=1.2,
        ),
        FieldDefinition(
            "price_change_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            description="Price change in basis points",
            example=23.4,
        ),
        FieldDefinition(
            "volatility_regime",
            DataType.STRING,
            "regime",
            NullPolicy.ALLOW_NULL,
            allowed_values=["very_high", "high", "medium", "low"],
            description="Volatility regime",
            example="high",
        ),
        FieldDefinition(
            "liquidity_score",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Liquidity score",
            example=0.78,
        ),
    ]

    # Enhanced Calibration Schema
    CALIBRATION_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:05:00+05:30",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "monotonic_id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "a",
            DataType.FLOAT,
            "coefficient",
            NullPolicy.ALLOW_NULL,
            description="Calibration coefficient a",
            example=-8.5,
        ),
        FieldDefinition(
            "b",
            DataType.FLOAT,
            "coefficient",
            NullPolicy.ALLOW_NULL,
            description="Calibration coefficient b",
            example=1.12,
        ),
        FieldDefinition(
            "pred_cal_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            description="Calibrated prediction in bps",
            example=3.6,
        ),
        FieldDefinition(
            "in_band_flag",
            DataType.BOOLEAN,
            "flag",
            NullPolicy.ALLOW_NULL,
            description="In no-trade band flag",
            example=True,
        ),
        FieldDefinition(
            "band_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="No-trade band width",
            example=15.0,
        ),
        FieldDefinition(
            "realized_bps",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            description="Realized returns in bps",
            example=2.8,
        ),
        FieldDefinition(
            "prediction_error",
            DataType.FLOAT,
            "basis_points",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            description="Prediction error",
            example=0.8,
        ),
        FieldDefinition(
            "calibration_score",
            DataType.FLOAT,
            "score",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Calibration quality score",
            example=0.78,
        ),
        FieldDefinition(
            "band_hit_rate",
            DataType.FLOAT,
            "rate",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="No-trade band hit rate",
            example=0.65,
        ),
        FieldDefinition(
            "prediction_accuracy",
            DataType.FLOAT,
            "accuracy",
            NullPolicy.ALLOW_NULL,
            min_value=0.0,
            max_value=1.0,
            description="Prediction accuracy",
            example=0.72,
        ),
    ]
    
    TRADE_SUMMARY_SCHEMA = [
        FieldDefinition(
            "ts_ist",
            DataType.TIMESTAMP,
            "ISO-8601+05:30",
            NullPolicy.NEVER_NULL,
            description="IST timestamp",
            example="2025-10-22T10:10:00+05:30",
        ),
        FieldDefinition(
            "asset",
            DataType.STRING,
            "symbol",
            NullPolicy.NEVER_NULL,
            description="Trading asset symbol",
            example="BTC-PERP",
        ),
        FieldDefinition(
            "bar_id",
            DataType.INTEGER,
            "id",
            NullPolicy.NEVER_NULL,
            description="Monotonic bar identifier",
            example=9675312,
        ),
        FieldDefinition(
            "signal_alpha",
            DataType.FLOAT,
            "bps",
            NullPolicy.ALLOW_NULL,
            description="Ensemble prediction in basis points",
            example=12.5,
        ),
        FieldDefinition(
            "intent_side",
            DataType.STRING,
            "side",
            NullPolicy.ALLOW_NULL,
            description="Intent direction (BUY/SELL/HOLD)",
            example="BUY",
        ),
        FieldDefinition(
            "intent_qty",
            DataType.FLOAT,
            "qty",
            NullPolicy.ALLOW_NULL,
            description="Intended trade quantity",
            example=0.42,
        ),
        FieldDefinition(
            "exec_side",
            DataType.STRING,
            "side",
            NullPolicy.ALLOW_NULL,
            description="Actual execution side",
            example="BUY",
        ),
        FieldDefinition(
            "exec_price",
            DataType.FLOAT,
            "price",
            NullPolicy.ALLOW_NULL,
            description="Average fill price",
            example=66120.5,
        ),
        FieldDefinition(
            "exec_qty",
            DataType.FLOAT,
            "qty",
            NullPolicy.ALLOW_NULL,
            description="Actual filled quantity",
            example=0.42,
        ),
        FieldDefinition(
            "fee_usd",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            description="Total execution fees in USD",
            example=14.7,
        ),
        FieldDefinition(
            "pnl_usd",
            DataType.FLOAT,
            "USD",
            NullPolicy.ALLOW_NULL,
            description="Realized PnL from this trade in USD",
            example=62.1,
        ),
        FieldDefinition(
            "reason_codes",
            DataType.JSON,
            "codes",
            NullPolicy.ALLOW_NULL,
            description="Decision reason codes and gating status",
            example={"threshold": True, "risk_ok": True},
        ),
        FieldDefinition(
            "event_id",
            DataType.STRING,
            "id",
            NullPolicy.ALLOW_NULL,
            description="Unique event traceability ID",
            example="1698000000:BTC:summary:a1b2c3d4",
        ),
    ]

    @classmethod
    def get_schema(cls, schema_name: str) -> List[FieldDefinition]:
        """Get schema by name"""
        schema_map = {
            "market_data": cls.MARKET_DATA_SCHEMA,
            "signals": cls.SIGNALS_SCHEMA,
            "ensemble": cls.ENSEMBLE_SCHEMA,
            "risk": cls.RISK_SCHEMA,
            "execution": cls.EXECUTION_SCHEMA,
            "costs": cls.COSTS_SCHEMA,
            "health": cls.HEALTH_SCHEMA,
            "repro": cls.REPRO_SCHEMA,
            "order_intent": cls.ORDER_INTENT_SCHEMA,
            "feature_log": cls.FEATURE_LOG_SCHEMA,
            "calibration": cls.CALIBRATION_SCHEMA,
            "trade_summary": cls.TRADE_SUMMARY_SCHEMA,
        }
        return schema_map.get(schema_name, [])

    @classmethod
    def validate_record(
        cls, record: Dict[str, Any], schema_name: str
    ) -> Dict[str, Any]:
        """Validate record against schema"""
        schema = cls.get_schema(schema_name)
        validated = {}
        errors = []

        for field_def in schema:
            value = record.get(field_def.field)

            # Handle null values
            if value is None:
                if field_def.null_policy == NullPolicy.NEVER_NULL:
                    errors.append(f"Field {field_def.field} cannot be null")
                    continue
                elif field_def.null_policy == NullPolicy.DEFAULT_NULL:
                    value = field_def.default_value
                else:
                    validated[field_def.field] = None
                    continue

            # Type validation
            try:
                if field_def.dtype == DataType.INTEGER:
                    value = int(value)
                elif field_def.dtype == DataType.FLOAT:
                    value = float(value)
                elif field_def.dtype == DataType.BOOLEAN:
                    value = bool(value)
                elif field_def.dtype == DataType.TIMESTAMP:
                    if isinstance(value, str):
                        # Validate ISO format
                        datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError) as e:
                errors.append(f"Field {field_def.field} type error: {e}")
                continue

            # Range validation
            if field_def.min_value is not None and value < field_def.min_value:
                errors.append(
                    f"Field {field_def.field} below minimum: {value} < {field_def.min_value}"
                )
                continue
            if field_def.max_value is not None and value > field_def.max_value:
                errors.append(
                    f"Field {field_def.field} above maximum: {value} > {field_def.max_value}"
                )
                continue

            # Allowed values validation
            if (
                field_def.allowed_values is not None
                and value not in field_def.allowed_values
            ):
                errors.append(f"Field {field_def.field} not in allowed values: {value}")
                continue

            validated[field_def.field] = value

        return {"validated": validated, "errors": errors}

    @classmethod
    def get_example_record(cls, schema_name: str) -> Dict[str, Any]:
        """Generate example record from schema"""
        schema = cls.get_schema(schema_name)
        example = {}

        for field_def in schema:
            if field_def.example is not None:
                example[field_def.field] = field_def.example
            elif field_def.default_value is not None:
                example[field_def.field] = field_def.default_value
            elif field_def.dtype == DataType.TIMESTAMP:
                example[field_def.field] = datetime.now(IST).isoformat()
            elif field_def.dtype == DataType.STRING:
                example[field_def.field] = f"example_{field_def.field}"
            elif field_def.dtype == DataType.INTEGER:
                example[field_def.field] = 0
            elif field_def.dtype == DataType.FLOAT:
                example[field_def.field] = 0.0
            elif field_def.dtype == DataType.BOOLEAN:
                example[field_def.field] = False
            elif field_def.dtype == DataType.JSON:
                example[field_def.field] = {}

        return example
