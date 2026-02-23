"""
Order Intent Tracking for MetaStackerBandit
Tracks pre-trade decisions and reasoning for order intent logging
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


from live_demo.reason_codes import VetoReasonCode

@dataclass
class OrderIntent:
    """Order intent data structure"""

    decision_time_ist: str
    bar_id_decision: int
    asset: str
    side: str  # 'BUY', 'SELL', 'HOLD'
    intent_qty: float
    intent_notional: float
    reason_codes: Dict[str, bool]  # threshold, band, spread_guard, etc.
    signal_strength: float
    model_confidence: float
    risk_score: float
    market_conditions: Dict[str, Any]


class OrderIntentTracker:
    """Tracks pre-trade decisions and order intents"""

    def __init__(self):
        self.intent_history: List[OrderIntent] = []
        self.current_intent: Optional[OrderIntent] = None

    def log_order_intent(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        decision: Dict[str, Any],
        model_out: Dict[str, Any],
        market_data: Dict[str, Any],
        risk_state: Dict[str, Any],
    ) -> OrderIntent:
        """Log order intent for pre-trade decision"""

        # Convert timestamp to IST
        dt_ist = datetime.fromtimestamp(ts / 1000.0, tz=IST)
        decision_time_ist = dt_ist.isoformat()

        # Determine side
        side = (
            "BUY"
            if decision.get("dir", 0) > 0
            else "SELL" if decision.get("dir", 0) < 0 else "HOLD"
        )

        # Calculate intent quantities
        intent_qty = abs(decision.get("alpha", 0.0))
        intent_notional = intent_qty * market_data.get("mid", 0.0)

        # Determine reason codes
        reason_codes = {
            VetoReasonCode.THRESHOLD.value: abs(decision.get("alpha", 0.0)) >= 0.001,
            VetoReasonCode.BAND.value: self._check_band_conditions(model_out, market_data),
            VetoReasonCode.SPREAD.value: self._check_spread_conditions(market_data),
            VetoReasonCode.VOLATILITY.value: self._check_volatility_conditions(market_data),
            VetoReasonCode.LIQUIDITY.value: self._check_liquidity_conditions(market_data),
            VetoReasonCode.RISK.value: self._check_risk_conditions(risk_state),
        }

        # Create order intent
        intent = OrderIntent(
            decision_time_ist=decision_time_ist,
            bar_id_decision=bar_id,
            asset=asset,
            side=side,
            intent_qty=intent_qty,
            intent_notional=intent_notional,
            reason_codes=reason_codes,
            signal_strength=abs(decision.get("alpha", 0.0)),
            model_confidence=model_out.get("confidence", 0.0),
            risk_score=risk_state.get("risk_score", 0.0),
            market_conditions={
                "spread_bps": market_data.get("spread_bps", 0.0),
                "volatility": market_data.get("rv_1h", 0.0),
                "volume": market_data.get("volume", 0.0),
                "funding_rate": market_data.get("funding_8h", 0.0),
            },
        )

        # Store intent
        self.current_intent = intent
        self.intent_history.append(intent)

        # Keep only last 1000 intents
        if len(self.intent_history) > 1000:
            self.intent_history = self.intent_history[-1000:]

        return intent

    def _extract_veto_reasons(self, reason_codes: Dict[str, bool]) -> tuple:
        """Extract primary and secondary veto reasons from failed guards
        
        Returns:
            tuple: (primary_veto, secondary_veto) - guard names that failed
        """
        # Get all guards that failed (False = failed)
        failed_guards = [k for k, v in reason_codes.items() if v is False]
        
        # Sort for consistency (alphabetical)
        failed_guards.sort()
        
        primary = failed_guards[0] if len(failed_guards) > 0 else None
        secondary = failed_guards[1] if len(failed_guards) > 1 else None
        
        return primary, secondary

    def _build_guard_details(
        self,
        reason_codes: Dict[str, bool],
        decision: Dict[str, Any],
        model_out: Dict[str, Any],
        market_data: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build detailed guard information with actual values vs thresholds
        
        Only includes details for guards that FAILED (returned False)
        
        Returns:
            dict: Guard details with actual values and thresholds
        """
        details = {}
        
        # Threshold guard - signal strength check
        if not reason_codes.get(VetoReasonCode.THRESHOLD.value, True):
            signal_strength = abs(decision.get("alpha", 0.0))
            details['threshold'] = {
                "signal_strength": round(signal_strength, 4),
                "required": 0.001,
                "gap": round(0.001 - signal_strength, 4)
            }
        
        # Band guard - model prediction strength
        if not reason_codes.get(VetoReasonCode.BAND.value, True):
            s_model = abs(model_out.get("s_model", 0.0))
            details['band'] = {
                "s_model": round(s_model, 4),
                "required": 0.001,
                "gap": round(0.001 - s_model, 4)
            }
        
        # Spread guard - market spread check
        if not reason_codes.get(VetoReasonCode.SPREAD.value, True):
            spread_bps = market_data.get("spread_bps", 0.0)
            details['spread_guard'] = {
                "spread_bps": round(spread_bps, 2),
                "threshold_bps": 10.0,
                "excess_bps": round(spread_bps - 10.0, 2) if spread_bps > 10.0 else 0.0
            }
        
        # Volatility guard - volatility range check
        if not reason_codes.get(VetoReasonCode.VOLATILITY.value, True):
            volatility = market_data.get("rv_1h", 0.0)
            details['volatility'] = {
                "rv_1h": round(volatility, 4),
                "min_threshold": 0.0,
                "max_threshold": 0.50,
                "out_of_range": "too_low" if volatility < 0.0 else "too_high" if volatility > 0.50 else "in_range"
            }
        
        # Liquidity guard - volume check
        if not reason_codes.get(VetoReasonCode.LIQUIDITY.value, True):
            volume = market_data.get("volume", 0.0)
            details['liquidity'] = {
                "volume": round(volume, 2),
                "min_threshold": 100.0,
                "shortfall": round(100.0 - volume, 2) if volume < 100.0 else 0.0
            }
        
        # Risk guard - position limit check
        if not reason_codes.get(VetoReasonCode.RISK.value, True):
            position = risk_state.get("position", 0.0)
            max_position = risk_state.get("max_position", 1.0)
            details['risk'] = {
                "position": round(position, 4),
                "max_position": round(max_position, 4),
                "utilization_pct": round(abs(position) / max_position * 100, 2) if max_position > 0 else 0.0
            }
        
        return details

    def _check_band_conditions(
        self, model_out: Dict[str, Any], market_data: Dict[str, Any]
    ) -> bool:
        """Check if model predictions are within acceptable bands"""
        s_model = model_out.get("s_model", 0.0)
        return abs(s_model) >= 0.001  # S_MIN threshold

    def _check_spread_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if spread conditions are acceptable"""
        spread_bps = market_data.get("spread_bps", 0.0)
        return spread_bps <= 10.0  # Max 10 bps spread

    def _check_volatility_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if volatility conditions are acceptable"""
        volatility = market_data.get("rv_1h", 0.0)
        return 0.0 <= volatility <= 0.50  # Reasonable volatility range (min lowered to 0.0)

    def _check_liquidity_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if liquidity conditions are acceptable"""
        volume = market_data.get("volume", 0.0)
        return volume >= 100.0  # Minimum volume threshold

    def _check_risk_conditions(self, risk_state: Dict[str, Any]) -> bool:
        """Check if risk conditions are acceptable"""
        position = risk_state.get("position", 0.0)
        max_position = risk_state.get("max_position", 1.0)
        return abs(position) <= max_position

    def get_intent_log(
        self, ts: float, asset: str, bar_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get order intent log for emission"""
        if not self.current_intent:
            return None

        intent = self.current_intent

        return {
            "ts_ist": intent.decision_time_ist,
            "bar_id_decision": intent.bar_id_decision,
            "asset": intent.asset,
            "side": intent.side,
            "intent_qty": intent.intent_qty,
            "intent_notional": intent.intent_notional,
            "reason_codes": intent.reason_codes,
            "signal_strength": intent.signal_strength,
            "model_confidence": intent.model_confidence,
            "risk_score": intent.risk_score,
            "market_conditions": intent.market_conditions,
        }

    def get_intent_log_enhanced(
        self,
        ts: float,
        asset: str,
        bar_id: int,
        decision: Dict[str, Any],
        model_out: Dict[str, Any],
        market_data: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get enhanced order intent log with veto reason details
        
        This is the new method that includes veto_reason_primary,
        veto_reason_secondary, and guard_details.
        """
        if not self.current_intent:
            return None

        intent = self.current_intent
        
        # Extract veto reasons
        primary_veto, secondary_veto = self._extract_veto_reasons(intent.reason_codes)
        
        # Build guard details
        guard_details = self._build_guard_details(
            intent.reason_codes,
            decision,
            model_out,
            market_data,
            risk_state
        )

        return {
            "ts_ist": intent.decision_time_ist,
            "bar_id_decision": intent.bar_id_decision,
            "asset": intent.asset,
            "side": intent.side,
            "intent_qty": intent.intent_qty,
            "intent_notional": intent.intent_notional,
            "reason_codes": intent.reason_codes,
            "signal_strength": intent.signal_strength,
            "model_confidence": intent.model_confidence,
            "risk_score": intent.risk_score,
            "market_conditions": intent.market_conditions,
            # Enhanced veto tracking fields
            "veto_reason_primary": primary_veto,
            "veto_reason_secondary": secondary_veto,
            "guard_details": guard_details
        }

    def log_order_intent_dict(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        decision: Dict[str, Any],
        model_out: Dict[str, Any],
        market_data: Dict[str, Any],
        risk_state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Log order intent and return dictionary directly with enhanced veto tracking"""
        intent = self.log_order_intent(
            ts, bar_id, asset, decision, model_out, market_data, risk_state
        )
        if intent:
            # Extract veto reasons
            primary_veto, secondary_veto = self._extract_veto_reasons(intent.reason_codes)
            
            # Build guard details
            guard_details = self._build_guard_details(
                intent.reason_codes,
                decision,
                model_out,
                market_data,
                risk_state
            )
            
            return {
                "ts_ist": intent.decision_time_ist,
                "bar_id_decision": intent.bar_id_decision,
                "asset": intent.asset,
                "side": intent.side,
                "intent_qty": intent.intent_qty,
                "intent_notional": intent.intent_notional,
                "reason_codes": intent.reason_codes,
                "signal_strength": intent.signal_strength,
                "model_confidence": intent.model_confidence,
                "risk_score": intent.risk_score,
                "market_conditions": intent.market_conditions,
                # Enhanced veto tracking fields
                "veto_reason_primary": primary_veto,
                "veto_reason_secondary": secondary_veto,
                "guard_details": guard_details
            }
        return None

    def get_intent_statistics(self) -> Dict[str, Any]:
        """Get order intent statistics"""
        if not self.intent_history:
            return {}

        total_intents = len(self.intent_history)
        buy_intents = sum(1 for intent in self.intent_history if intent.side == "BUY")
        sell_intents = sum(1 for intent in self.intent_history if intent.side == "SELL")
        hold_intents = sum(1 for intent in self.intent_history if intent.side == "HOLD")

        avg_signal_strength = (
            sum(intent.signal_strength for intent in self.intent_history)
            / total_intents
        )
        avg_model_confidence = (
            sum(intent.model_confidence for intent in self.intent_history)
            / total_intents
        )

        return {
            "total_intents": total_intents,
            "buy_intents": buy_intents,
            "sell_intents": sell_intents,
            "hold_intents": hold_intents,
            "avg_signal_strength": avg_signal_strength,
            "avg_model_confidence": avg_model_confidence,
            "buy_ratio": buy_intents / total_intents if total_intents > 0 else 0.0,
            "sell_ratio": sell_intents / total_intents if total_intents > 0 else 0.0,
            "hold_ratio": hold_intents / total_intents if total_intents > 0 else 0.0,
        }
