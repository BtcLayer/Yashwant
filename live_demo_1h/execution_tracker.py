"""
Execution Details Tracking for MetaStackerBandit
Tracks order rejections, timing, throttle events, and execution performance
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from collections import deque
import pytz
from dataclasses import dataclass
import json

IST = pytz.timezone("Asia/Kolkata")

@dataclass
class ExecutionDetails:
    """Execution details container"""
    decision_time_ist: str
    exec_time_ist: str
    asset: str
    bar_id: int
    side: str
    order_type: str
    limit_px: Optional[float] = None
    fill_px: Optional[float] = None
    fill_qty: Optional[float] = None
    slip_bps_mkt: Optional[float] = None
    route: Optional[str] = None
    rejections: int = 0
    ioc_ms: Optional[float] = None
    throttle_guard_events: int = 0

class ExecutionTracker:
    """Execution details tracking system"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.execution_history = deque(maxlen=max_history)
        self.rejection_count = 0
        self.total_orders = 0
        self.throttle_events = 0
        self.execution_times = deque(maxlen=1000)
        self.route_stats = {}
        self.order_type_stats = {}
        
    def start_execution(self, asset: str, bar_id: int, side: str, order_type: str, 
                       limit_px: Optional[float] = None) -> str:
        """Start tracking an execution"""
        execution_id = f"{asset}_{bar_id}_{int(time.time() * 1000)}"
        
        execution = ExecutionDetails(
            decision_time_ist=datetime.now(IST).isoformat(),
            exec_time_ist="",  # Will be filled when execution completes
            asset=asset,
            bar_id=bar_id,
            side=side,
            order_type=order_type,
            limit_px=limit_px
        )
        
        self.execution_history.append({
            'id': execution_id,
            'execution': execution,
            'start_time': time.time(),
            'completed': False
        })
        
        self.total_orders += 1
        
        return execution_id
    
    def complete_execution(self, execution_id: str, fill_px: Optional[float] = None,
                          fill_qty: Optional[float] = None, route: Optional[str] = None,
                          slip_bps: Optional[float] = None, ioc_ms: Optional[float] = None):
        """Complete an execution"""
        for exec_record in self.execution_history:
            if exec_record['id'] == execution_id:
                exec_record['completed'] = True
                exec_record['execution'].exec_time_ist = datetime.now(IST).isoformat()
                exec_record['execution'].fill_px = fill_px
                exec_record['execution'].fill_qty = fill_qty
                exec_record['execution'].route = route
                exec_record['execution'].slip_bps_mkt = slip_bps
                exec_record['execution'].ioc_ms = ioc_ms
                
                # Calculate execution time
                execution_time = time.time() - exec_record['start_time']
                self.execution_times.append(execution_time)
                
                # Update route stats
                if route:
                    self.route_stats[route] = self.route_stats.get(route, 0) + 1
                
                break
    
    def record_rejection(self, execution_id: str, reason: str = "unknown"):
        """Record an order rejection"""
        self.rejection_count += 1
        
        for exec_record in self.execution_history:
            if exec_record['id'] == execution_id:
                exec_record['execution'].rejections += 1
                exec_record['rejection_reason'] = reason
                break
    
    def record_throttle_event(self, execution_id: str, event_type: str = "rate_limit"):
        """Record a throttle guard event"""
        self.throttle_events += 1
        
        for exec_record in self.execution_history:
            if exec_record['id'] == execution_id:
                exec_record['execution'].throttle_guard_events += 1
                exec_record['throttle_event_type'] = event_type
                break
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_times:
            return {}
        
        completed_executions = [e for e in self.execution_history if e['completed']]
        
        stats = {
            'total_orders': self.total_orders,
            'completed_orders': len(completed_executions),
            'rejection_count': self.rejection_count,
            'rejection_rate': self.rejection_count / max(self.total_orders, 1),
            'throttle_events': self.throttle_events,
            'avg_execution_time_ms': sum(self.execution_times) / len(self.execution_times) * 1000,
            'max_execution_time_ms': max(self.execution_times) * 1000,
            'min_execution_time_ms': min(self.execution_times) * 1000,
            'route_distribution': self.route_stats,
            'order_type_distribution': self.order_type_stats
        }
        
        return stats
    
    def get_recent_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution details"""
        recent = list(self.execution_history)[-limit:]
        
        return [
            {
                'id': exec_record['id'],
                'execution': asdict(exec_record['execution']),
                'completed': exec_record['completed'],
                'execution_time_ms': (time.time() - exec_record['start_time']) * 1000 if exec_record['completed'] else None
            }
            for exec_record in recent
        ]
    
    def get_execution_log(self, timestamp: float, asset: str, bar_id: int) -> Optional[Dict[str, Any]]:
        """Get execution log for a specific timestamp"""
        # Find the most recent execution for this asset/bar
        for exec_record in reversed(self.execution_history):
            if (exec_record['execution'].asset == asset and 
                exec_record['execution'].bar_id == bar_id):
                
                execution = exec_record['execution']
                
                return {
                    "ts_ist": datetime.fromtimestamp(timestamp/1000, IST).isoformat(),
                    "decision_time_ist": execution.decision_time_ist,
                    "exec_time_ist": execution.exec_time_ist,
                    "asset": execution.asset,
                    "bar_id": execution.bar_id,
                    "side": execution.side,
                    "order_type": execution.order_type,
                    "limit_px": execution.limit_px,
                    "fill_px": execution.fill_px,
                    "fill_qty": execution.fill_qty,
                    "slip_bps_mkt": execution.slip_bps_mkt,
                    "route": execution.route,
                    "rejections": execution.rejections,
                    "ioc_ms": execution.ioc_ms,
                    "throttle_guard_events": execution.throttle_guard_events
                }
        
        return None
    
    def calculate_slippage(self, intended_price: float, fill_price: float) -> float:
        """Calculate slippage in basis points"""
        if intended_price == 0:
            return 0.0
        
        slippage = ((fill_price - intended_price) / intended_price) * 10000
        return slippage
    
    def calculate_impact(self, order_size: float, fill_price: float, 
                       market_price: float) -> float:
        """Calculate market impact in basis points"""
        if market_price == 0:
            return 0.0
        
        impact = ((fill_price - market_price) / market_price) * 10000
        return impact
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get execution performance metrics"""
        completed_executions = [e for e in self.execution_history if e['completed']]
        
        if not completed_executions:
            return {}
        
        # Calculate slippage statistics
        slippages = []
        impacts = []
        
        for exec_record in completed_executions:
            execution = exec_record['execution']
            if execution.fill_px and execution.limit_px:
                slippage = self.calculate_slippage(execution.limit_px, execution.fill_px)
                slippages.append(slippage)
            
            if execution.slip_bps_mkt:
                impacts.append(execution.slip_bps_mkt)
        
        metrics = {
            'execution_success_rate': len(completed_executions) / max(self.total_orders, 1),
            'avg_slippage_bps': sum(slippages) / len(slippages) if slippages else 0,
            'max_slippage_bps': max(slippages) if slippages else 0,
            'avg_impact_bps': sum(impacts) / len(impacts) if impacts else 0,
            'max_impact_bps': max(impacts) if impacts else 0,
            'total_slippage_cost': sum(slippages) / 10000,  # Convert to percentage
            'route_performance': self._calculate_route_performance()
        }
        
        return metrics
    
    def _calculate_route_performance(self) -> Dict[str, Any]:
        """Calculate performance by route"""
        route_performance = {}
        
        for route in self.route_stats.keys():
            route_executions = [e for e in self.execution_history 
                              if e['completed'] and e['execution'].route == route]
            
            if route_executions:
                avg_time = sum(e['execution'].ioc_ms or 0 for e in route_executions) / len(route_executions)
                success_rate = len(route_executions) / max(self.route_stats[route], 1)
                
                route_performance[route] = {
                    'avg_execution_time_ms': avg_time,
                    'success_rate': success_rate,
                    'total_orders': self.route_stats[route]
                }
        
        return route_performance
    
    def reset_stats(self):
        """Reset execution statistics"""
        self.execution_history.clear()
        self.rejection_count = 0
        self.total_orders = 0
        self.throttle_events = 0
        self.execution_times.clear()
        self.route_stats.clear()
        self.order_type_stats.clear()
