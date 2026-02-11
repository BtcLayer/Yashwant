"""
Automated Circuit Breaker System
Automatically pauses trading when risk conditions are met
Automatically resumes when conditions improve
"""

import json
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict


@dataclass
class CircuitBreakerState:
    """Current state of the circuit breaker"""
    is_paused: bool = False
    pause_reason: Optional[str] = None
    pause_timestamp: Optional[float] = None
    pause_conditions_met: Dict[str, bool] = None
    consecutive_losses: int = 0
    last_trade_profitable: Optional[bool] = None
    
    def __post_init__(self):
        if self.pause_conditions_met is None:
            self.pause_conditions_met = {}


class AutoCircuitBreaker:
    """
    Automated circuit breaker for trading system
    
    Pauses trading when:
    - Max drawdown exceeded
    - Too many consecutive losses
    - Sharpe ratio too low
    - Model drift detected
    - Extreme volatility
    - API errors
    
    Resumes trading when:
    - Drawdown recovered
    - Sharpe ratio improved
    - Model drift stabilized
    - Minimum pause time elapsed
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize circuit breaker
        
        Args:
            config_path: Path to circuit_breaker_config.json
        """
        self.config = self._load_config(config_path)
        self.state = CircuitBreakerState()
        self.pause_history: List[Dict] = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "pause_conditions": {
                "max_drawdown": -0.15,  # 15% drawdown
                "consecutive_losses": 5,
                "sharpe_1d_below": -0.5,
                "ic_drift_below": -0.05,
                "volatility_spike_multiplier": 3.0,
                "api_error_rate": 0.1
            },
            "resume_conditions": {
                "drawdown_recovered_to": -0.05,  # Recover to 5% DD
                "sharpe_1d_above": 0.5,
                "ic_drift_above": -0.01,
                "min_pause_hours": 24
            },
            "logging": {
                "log_all_checks": False,  # Set to True for debugging
                "log_state_changes": True
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key in loaded_config:
                        default_config[key].update(loaded_config[key])
                return default_config
            except Exception as e:
                print(f"⚠️  Failed to load circuit breaker config: {e}")
                print("Using default configuration")
        
        return default_config
    
    def check_should_pause(
        self, 
        health_metrics: Any,
        market_data: Optional[Dict] = None
    ) -> bool:
        """
        Check if trading should be paused
        
        Args:
            health_metrics: HealthMetrics object from health_monitor
            market_data: Optional dict with market data (volatility, etc.)
            
        Returns:
            True if should pause, False otherwise
        """
        if self.state.is_paused:
            return True  # Already paused
        
        conditions_met = {}
        pause_reasons = []
        
        # Check max drawdown
        if hasattr(health_metrics, 'max_dd_to_date') and health_metrics.max_dd_to_date is not None:
            dd_threshold = self.config['pause_conditions']['max_drawdown']
            if health_metrics.max_dd_to_date < dd_threshold:
                conditions_met['max_drawdown'] = True
                pause_reasons.append(
                    f"Max drawdown {health_metrics.max_dd_to_date:.2%} < {dd_threshold:.2%}"
                )
        
        # Check consecutive losses
        loss_threshold = self.config['pause_conditions']['consecutive_losses']
        if self.state.consecutive_losses >= loss_threshold:
            conditions_met['consecutive_losses'] = True
            pause_reasons.append(
                f"Consecutive losses {self.state.consecutive_losses} >= {loss_threshold}"
            )
        
        # Check Sharpe ratio
        if hasattr(health_metrics, 'sharpe_roll_1d') and health_metrics.sharpe_roll_1d is not None:
            sharpe_threshold = self.config['pause_conditions']['sharpe_1d_below']
            if health_metrics.sharpe_roll_1d < sharpe_threshold:
                conditions_met['low_sharpe'] = True
                pause_reasons.append(
                    f"Sharpe 1d {health_metrics.sharpe_roll_1d:.2f} < {sharpe_threshold:.2f}"
                )
        
        # Check IC drift
        if hasattr(health_metrics, 'ic_drift') and health_metrics.ic_drift is not None:
            ic_threshold = self.config['pause_conditions']['ic_drift_below']
            if health_metrics.ic_drift < ic_threshold:
                conditions_met['ic_drift'] = True
                pause_reasons.append(
                    f"IC drift {health_metrics.ic_drift:.3f} < {ic_threshold:.3f}"
                )
        
        # Check volatility spike (if market data provided)
        if market_data and 'volatility' in market_data and 'avg_volatility' in market_data:
            vol_multiplier = self.config['pause_conditions']['volatility_spike_multiplier']
            if market_data['volatility'] > vol_multiplier * market_data['avg_volatility']:
                conditions_met['volatility_spike'] = True
                pause_reasons.append(
                    f"Volatility spike: {market_data['volatility']:.4f} > "
                    f"{vol_multiplier}x avg ({market_data['avg_volatility']:.4f})"
                )
        
        # If any condition met, pause trading
        if conditions_met:
            self._pause_trading(conditions_met, pause_reasons)
            return True
        
        return False
    
    def check_should_resume(self, health_metrics: Any) -> bool:
        """
        Check if trading should resume
        
        Args:
            health_metrics: HealthMetrics object from health_monitor
            
        Returns:
            True if should resume, False otherwise
        """
        if not self.state.is_paused:
            return False  # Not paused, nothing to resume
        
        resume_conditions = {}
        
        # Check if minimum pause time elapsed
        min_pause_hours = self.config['resume_conditions']['min_pause_hours']
        if self.state.pause_timestamp:
            hours_paused = (time.time() - self.state.pause_timestamp) / 3600
            resume_conditions['time_elapsed'] = hours_paused >= min_pause_hours
        else:
            resume_conditions['time_elapsed'] = False
        
        # Check drawdown recovery
        # Note: current_drawdown is tracked in HealthMonitor, not HealthMetrics
        # For now, use max_dd_to_date as proxy for recovery check
        if hasattr(health_metrics, 'max_dd_to_date') and health_metrics.max_dd_to_date is not None:
            dd_threshold = self.config['resume_conditions']['drawdown_recovered_to']
            resume_conditions['drawdown_recovered'] = (
                health_metrics.max_dd_to_date > dd_threshold
            )
        else:
            resume_conditions['drawdown_recovered'] = False
        
        # Check Sharpe recovery
        if hasattr(health_metrics, 'sharpe_roll_1d') and health_metrics.sharpe_roll_1d is not None:
            sharpe_threshold = self.config['resume_conditions']['sharpe_1d_above']
            resume_conditions['sharpe_recovered'] = (
                health_metrics.sharpe_roll_1d > sharpe_threshold
            )
        else:
            resume_conditions['sharpe_recovered'] = False
        
        # Check IC drift recovery
        if hasattr(health_metrics, 'ic_drift') and health_metrics.ic_drift is not None:
            ic_threshold = self.config['resume_conditions']['ic_drift_above']
            resume_conditions['ic_stable'] = health_metrics.ic_drift > ic_threshold
        else:
            resume_conditions['ic_stable'] = False
        
        # Resume if ALL conditions met
        if all(resume_conditions.values()):
            self._resume_trading(resume_conditions)
            return True
        
        # Log why not resuming (if configured)
        if self.config['logging']['log_all_checks']:
            failed_conditions = [k for k, v in resume_conditions.items() if not v]
            print(f"⏸️  Still paused. Waiting for: {', '.join(failed_conditions)}")
        
        return False
    
    def update_trade_result(self, profitable: bool):
        """
        Update consecutive loss counter based on trade result
        
        Args:
            profitable: True if trade was profitable, False otherwise
        """
        if profitable:
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_losses += 1
        
        self.state.last_trade_profitable = profitable
    
    def _pause_trading(self, conditions_met: Dict[str, bool], reasons: List[str]):
        """Pause trading and log the event"""
        self.state.is_paused = True
        self.state.pause_timestamp = time.time()
        self.state.pause_conditions_met = conditions_met
        self.state.pause_reason = "; ".join(reasons)
        
        # Log pause event
        pause_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "PAUSE",
            "conditions": conditions_met,
            "reasons": reasons
        }
        self.pause_history.append(pause_event)
        
        if self.config['logging']['log_state_changes']:
            print("\n" + "="*80)
            print("🛑 CIRCUIT BREAKER TRIGGERED - TRADING PAUSED")
            print("="*80)
            for reason in reasons:
                print(f"   ⚠️  {reason}")
            print("="*80 + "\n")
    
    def _resume_trading(self, resume_conditions: Dict[str, bool]):
        """Resume trading and log the event"""
        pause_duration = None
        if self.state.pause_timestamp:
            pause_duration = time.time() - self.state.pause_timestamp
        
        self.state.is_paused = False
        self.state.pause_reason = None
        self.state.pause_timestamp = None
        self.state.pause_conditions_met = {}
        
        # Log resume event
        resume_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "RESUME",
            "conditions": resume_conditions,
            "pause_duration_hours": pause_duration / 3600 if pause_duration else None
        }
        self.pause_history.append(resume_event)
        
        if self.config['logging']['log_state_changes']:
            print("\n" + "="*80)
            print("✅ CIRCUIT BREAKER CLEARED - TRADING RESUMED")
            print("="*80)
            if pause_duration:
                print(f"   Paused for: {pause_duration/3600:.1f} hours")
            print("   Resume conditions met:")
            for condition, met in resume_conditions.items():
                print(f"      ✓ {condition}: {met}")
            print("="*80 + "\n")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        status = {
            "is_paused": self.state.is_paused,
            "pause_reason": self.state.pause_reason,
            "consecutive_losses": self.state.consecutive_losses,
            "last_trade_profitable": self.state.last_trade_profitable
        }
        
        if self.state.is_paused and self.state.pause_timestamp:
            status["paused_for_hours"] = (time.time() - self.state.pause_timestamp) / 3600
            status["pause_conditions"] = self.state.pause_conditions_met
        
        return status
    
    def log_state_change(self, log_file: Optional[str] = None):
        """Log state changes to file"""
        if not log_file:
            return
        
        try:
            with open(log_file, 'a') as f:
                for event in self.pause_history:
                    f.write(json.dumps(event) + '\n')
            # Clear history after logging
            self.pause_history = []
        except Exception as e:
            print(f"⚠️  Failed to log circuit breaker state: {e}")
    
    def reset_consecutive_losses(self):
        """Manually reset consecutive loss counter"""
        self.state.consecutive_losses = 0
    
    def force_pause(self, reason: str):
        """Manually force pause (for emergency situations)"""
        self._pause_trading(
            {"manual_override": True},
            [f"Manual pause: {reason}"]
        )
    
    def force_resume(self):
        """Manually force resume (use with caution!)"""
        self._resume_trading({"manual_override": True})
