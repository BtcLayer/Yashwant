"""
Order Intent Tracking for MetaStackerBandit
Tracks pre-trade decisions and reasoning for order intent logging
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

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
        risk_state: Dict[str, Any]
    ) -> OrderIntent:
        """Log order intent for pre-trade decision"""
        
        # Convert timestamp to IST
        dt_ist = datetime.fromtimestamp(ts / 1000.0, tz=IST)
        decision_time_ist = dt_ist.isoformat()
        
        # Determine side
        side = 'BUY' if decision.get('dir', 0) > 0 else 'SELL' if decision.get('dir', 0) < 0 else 'HOLD'
        
        # Calculate intent quantities
        intent_qty = abs(decision.get('alpha', 0.0))
        intent_notional = intent_qty * market_data.get('mid', 0.0)
        
        # Determine reason codes
        reason_codes = {
            'threshold': abs(decision.get('alpha', 0.0)) >= 0.12,
            'band': self._check_band_conditions(model_out, market_data),
            'spread_guard': self._check_spread_conditions(market_data),
            'volatility_ok': self._check_volatility_conditions(market_data),
            'liquidity_ok': self._check_liquidity_conditions(market_data),
            'risk_ok': self._check_risk_conditions(risk_state)
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
            signal_strength=abs(decision.get('alpha', 0.0)),
            model_confidence=model_out.get('confidence', 0.0),
            risk_score=risk_state.get('risk_score', 0.0),
            market_conditions={
                'spread_bps': market_data.get('spread_bps', 0.0),
                'volatility': market_data.get('rv_1h', 0.0),
                'volume': market_data.get('volume', 0.0),
                'funding_rate': market_data.get('funding_8h', 0.0)
            }
        )
        
        # Store intent
        self.current_intent = intent
        self.intent_history.append(intent)
        
        # Keep only last 1000 intents
        if len(self.intent_history) > 1000:
            self.intent_history = self.intent_history[-1000:]
        
        return intent
    
    def _check_band_conditions(self, model_out: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Check if model predictions are within acceptable bands"""
        s_model = model_out.get('s_model', 0.0)
        return abs(s_model) >= 0.12  # S_MIN threshold
    
    def _check_spread_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if spread conditions are acceptable"""
        spread_bps = market_data.get('spread_bps', 0.0)
        return spread_bps <= 10.0  # Max 10 bps spread
    
    def _check_volatility_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if volatility conditions are acceptable"""
        volatility = market_data.get('rv_1h', 0.0)
        return 0.01 <= volatility <= 0.50  # Reasonable volatility range
    
    def _check_liquidity_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Check if liquidity conditions are acceptable"""
        volume = market_data.get('volume', 0.0)
        return volume >= 100.0  # Minimum volume threshold
    
    def _check_risk_conditions(self, risk_state: Dict[str, Any]) -> bool:
        """Check if risk conditions are acceptable"""
        position = risk_state.get('position', 0.0)
        max_position = risk_state.get('max_position', 1.0)
        return abs(position) <= max_position
    
    def get_intent_log(self, ts: float, asset: str, bar_id: int) -> Optional[Dict[str, Any]]:
        """Get order intent log for emission"""
        if not self.current_intent:
            return None
        
        intent = self.current_intent
        
        return {
            'ts_ist': intent.decision_time_ist,
            'bar_id_decision': intent.bar_id_decision,
            'asset': intent.asset,
            'side': intent.side,
            'intent_qty': intent.intent_qty,
            'intent_notional': intent.intent_notional,
            'reason_codes': intent.reason_codes,
            'signal_strength': intent.signal_strength,
            'model_confidence': intent.model_confidence,
            'risk_score': intent.risk_score,
            'market_conditions': intent.market_conditions
        }
    
    def log_order_intent_dict(self, 
        ts: float, 
        bar_id: int, 
        asset: str, 
        decision: Dict[str, Any],
        model_out: Dict[str, Any],
        market_data: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Log order intent and return dictionary directly"""
        intent = self.log_order_intent(ts, bar_id, asset, decision, model_out, market_data, risk_state)
        if intent:
            return {
                'ts_ist': intent.decision_time_ist,
                'bar_id_decision': intent.bar_id_decision,
                'asset': intent.asset,
                'side': intent.side,
                'intent_qty': intent.intent_qty,
                'intent_notional': intent.intent_notional,
                'reason_codes': intent.reason_codes,
                'signal_strength': intent.signal_strength,
                'model_confidence': intent.model_confidence,
                'risk_score': intent.risk_score,
                'market_conditions': intent.market_conditions
            }
        return None
    
    def get_intent_statistics(self) -> Dict[str, Any]:
        """Get order intent statistics"""
        if not self.intent_history:
            return {}
        
        total_intents = len(self.intent_history)
        buy_intents = sum(1 for intent in self.intent_history if intent.side == 'BUY')
        sell_intents = sum(1 for intent in self.intent_history if intent.side == 'SELL')
        hold_intents = sum(1 for intent in self.intent_history if intent.side == 'HOLD')
        
        avg_signal_strength = sum(intent.signal_strength for intent in self.intent_history) / total_intents
        avg_model_confidence = sum(intent.model_confidence for intent in self.intent_history) / total_intents
        
        return {
            'total_intents': total_intents,
            'buy_intents': buy_intents,
            'sell_intents': sell_intents,
            'hold_intents': hold_intents,
            'avg_signal_strength': avg_signal_strength,
            'avg_model_confidence': avg_model_confidence,
            'buy_ratio': buy_intents / total_intents if total_intents > 0 else 0.0,
            'sell_ratio': sell_intents / total_intents if total_intents > 0 else 0.0,
            'hold_ratio': hold_intents / total_intents if total_intents > 0 else 0.0
        }
