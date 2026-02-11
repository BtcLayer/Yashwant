from enum import Enum

class VetoReasonCode(str, Enum):
    """Reasons why an order intent was vetoed before execution (pre-decision logic)"""
    THRESHOLD = "threshold"
    BAND = "band"
    SPREAD = "spread_guard"
    VOLATILITY = "volatility_ok"
    LIQUIDITY = "liquidity_ok"
    RISK = "risk_ok"

class GuardReasonCode(str, Enum):
    """Reasons why a decision was blocked or modified by risk guards (post-decision logic)"""
    SPREAD = "spread_guard"
    FUNDING = "funding_guard"
    MIN_SIGN_FLIP = "min_sign_flip"
    DELTA_PI_MIN = "delta_pi_min"
    THROTTLE = "throttle_guard"
    ADV_ORDER_CAP = "adv_order_cap"
    ADV_HOUR_CAP = "adv_hour_cap"
    CALIBRATION_BAND = "calibration_band_gate"
    IMPACT_GUARD = "impact_guard"
    IMPACT_CRITICAL = "impact_critical"
    NET_EDGE_INSUFFICIENT = "net_edge_insufficient"
