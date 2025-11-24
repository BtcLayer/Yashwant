"""
Alert Routing System for MetaStackerBandit
Features: Slack/Email notifications, escalation policies, rate limiting, deduplication
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import pytz
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import hashlib
from collections import defaultdict, deque

IST = pytz.timezone("Asia/Kolkata")

class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class AlertChannel(Enum):
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"

@dataclass
class AlertRule:
    name: str
    condition: str  # Python expression to evaluate
    level: AlertLevel
    channels: List[AlertChannel]
    cooldown_minutes: int = 15
    max_alerts_per_hour: int = 10
    escalation_minutes: int = 30
    escalation_level: Optional[AlertLevel] = None
    enabled: bool = True

@dataclass
class AlertConfig:
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#trading-alerts"
    slack_username: str = "MetaStackerBot"
    
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    
    webhook_url: Optional[str] = None
    
    rate_limit_window: int = 3600  # 1 hour
    max_alerts_per_window: int = 100

@dataclass
class Alert:
    id: str
    rule_name: str
    level: AlertLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    channels: List[AlertChannel]
    escalated: bool = False
    escalation_count: int = 0

class AlertRouter:
    """Production alert routing system with escalation and rate limiting"""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque())
        self.cooldowns: Dict[str, float] = {}
        self.escalation_timers: Dict[str, threading.Timer] = {}
        self.lock = threading.RLock()
        
        # Initialize default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules for trading system"""
        default_rules = [
            AlertRule(
                name="ic_drift_critical",
                condition="metrics.get('ic_drift', 0) <= -0.05",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=30,
                escalation_minutes=60,
                escalation_level=AlertLevel.EMERGENCY
            ),
            AlertRule(
                name="ic_drift_warning",
                condition="metrics.get('ic_drift', 0) <= -0.03",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.SLACK],
                cooldown_minutes=15
            ),
            AlertRule(
                name="drawdown_critical",
                condition="metrics.get('max_dd_to_date', 0) <= -0.03",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=60,
                escalation_minutes=120,
                escalation_level=AlertLevel.EMERGENCY
            ),
            AlertRule(
                name="drawdown_warning",
                condition="metrics.get('max_dd_to_date', 0) <= -0.02",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.SLACK],
                cooldown_minutes=30
            ),
            AlertRule(
                name="cost_blowup",
                condition="metrics.get('avg_cost_bps', 0) >= 7.0",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.SLACK],
                cooldown_minutes=60
            ),
            AlertRule(
                name="capacity_breach",
                condition="metrics.get('capacity_participation', 0) >= 0.03",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=30
            ),
            AlertRule(
                name="data_freshness",
                condition="metrics.get('book_lag_ms', 0) > 5000",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=15
            ),
            AlertRule(
                name="leakage_detected",
                condition="metrics.get('leakage_flag', False) == True",
                level=AlertLevel.EMERGENCY,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=0,
                escalation_minutes=15
            ),
            AlertRule(
                name="same_bar_roundtrip",
                condition="metrics.get('same_bar_roundtrip_flag', False) == True",
                level=AlertLevel.EMERGENCY,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=0,
                escalation_minutes=15
            ),
            AlertRule(
                name="execution_failures",
                condition="metrics.get('reject_rate', 0) > 0.05",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown_minutes=30
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        with self.lock:
            self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule"""
        with self.lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
    
    def evaluate_alerts(self, metrics: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Evaluate all rules against current metrics"""
        if context is None:
            context = {}
        
        # Create evaluation context
        eval_context = {
            'metrics': metrics,
            'context': context,
            'timestamp': datetime.now(IST),
            'time': time.time()
        }
        
        with self.lock:
            for rule_name, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                try:
                    # Check cooldown
                    if self._is_in_cooldown(rule_name):
                        continue
                    
                    # Check rate limit
                    if self._is_rate_limited(rule_name):
                        continue
                    
                    # Evaluate condition
                    if self._evaluate_condition(rule.condition, eval_context):
                        self._trigger_alert(rule, metrics, context)
                        
                except Exception as e:
                    self._log_error(f"Error evaluating rule {rule_name}: {e}")
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate alert condition"""
        try:
            # Create safe evaluation context
            safe_context = {
                'metrics': context.get('metrics', {}),
                'context': context.get('context', {}),
                'timestamp': context.get('timestamp'),
                'time': context.get('time', 0)
            }
            
            # Evaluate condition
            result = eval(condition, {"__builtins__": {}}, safe_context)
            return bool(result)
            
        except Exception as e:
            self._log_error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown"""
        if rule_name not in self.cooldowns:
            return False
        
        rule = self.rules[rule_name]
        cooldown_end = self.cooldowns[rule_name] + (rule.cooldown_minutes * 60)
        return time.time() < cooldown_end
    
    def _is_rate_limited(self, rule_name: str) -> bool:
        """Check if rule is rate limited"""
        rule = self.rules[rule_name]
        now = time.time()
        window_start = now - (rule.max_alerts_per_hour * 3600 / rule.max_alerts_per_hour)
        
        # Clean old timestamps
        timestamps = self.rate_limits[rule_name]
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()
        
        return len(timestamps) >= rule.max_alerts_per_hour
    
    def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any], context: Dict[str, Any]):
        """Trigger alert for rule"""
        # Create alert
        alert_id = self._generate_alert_id(rule.name, metrics)
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            level=rule.level,
            message=self._format_alert_message(rule, metrics, context),
            details={
                'metrics': metrics,
                'context': context,
                'rule': rule.name,
                'timestamp': datetime.now(IST).isoformat()
            },
            timestamp=datetime.now(IST),
            channels=rule.channels
        )
        
        # Send alert
        self._send_alert(alert)
        
        # Update cooldown and rate limits
        self.cooldowns[rule.name] = time.time()
        self.rate_limits[rule.name].append(time.time())
        
        # Add to history
        self.alert_history.append(alert)
        
        # Setup escalation if configured
        if rule.escalation_minutes and rule.escalation_level:
            self._setup_escalation(alert, rule)
    
    def _generate_alert_id(self, rule_name: str, metrics: Dict[str, Any]) -> str:
        """Generate unique alert ID"""
        content = f"{rule_name}:{json.dumps(metrics, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _format_alert_message(self, rule: AlertRule, metrics: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format alert message"""
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        
        message = f"ALERT: {rule.level.value} - {rule.name}\n"
        message += f"Time: {timestamp}\n\n"
        
        # Add metrics summary
        if 'ic_drift' in metrics:
            message += f"IC Drift: {metrics['ic_drift']:.3f}\n"
        if 'max_dd_to_date' in metrics:
            message += f"Max DD: {metrics['max_dd_to_date']:.1%}\n"
        if 'avg_cost_bps' in metrics:
            message += f"Avg Cost: {metrics['avg_cost_bps']:.1f} bps\n"
        if 'capacity_participation' in metrics:
            message += f"Capacity: {metrics['capacity_participation']:.1%}\n"
        
        # Add context if available
        if context:
            message += f"\nContext: {json.dumps(context, indent=2)}"
        
        return message
    
    def _send_alert(self, alert: Alert):
        """Send alert to configured channels"""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.SLACK:
                    self._send_slack_alert(alert)
                elif channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert)
                elif channel == AlertChannel.LOG:
                    self._log_alert(alert)
                    
            except Exception as e:
                self._log_error(f"Error sending alert to {channel.value}: {e}")
    
    def _send_slack_alert(self, alert: Alert):
        """Send alert to Slack"""
        if not self.config.slack_webhook_url:
            return
        
        payload = {
            "channel": self.config.slack_channel,
            "username": self.config.slack_username,
            "text": alert.message,
            "attachments": [
                {
                    "color": self._get_color_for_level(alert.level),
                    "fields": [
                        {
                            "title": "Alert ID",
                            "value": alert.id,
                            "short": True
                        },
                        {
                            "title": "Rule",
                            "value": alert.rule_name,
                            "short": True
                        },
                        {
                            "title": "Level",
                            "value": alert.level.value,
                            "short": True
                        }
                    ],
                    "footer": "MetaStackerBandit",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        response = requests.post(
            self.config.slack_webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    
    def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        if not self.config.smtp_server or not self.config.email_to:
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.config.email_from or "noreply@metastacker.com"
        msg['To'] = ", ".join(self.config.email_to)
        msg['Subject'] = f"[{alert.level.value}] {alert.rule_name} - MetaStackerBandit"
        
        # Create HTML body
        html_body = f"""
        <html>
        <body>
            <h2 style="color: {self._get_color_for_level(alert.level)};">{alert.level.value} Alert</h2>
            <h3>{alert.rule_name}</h3>
            <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')}</p>
            <p><strong>Alert ID:</strong> {alert.id}</p>
            <pre>{alert.message}</pre>
            <h4>Details:</h4>
            <pre>{json.dumps(alert.details, indent=2)}</pre>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
            server.starttls(context=context)
            if self.config.smtp_username:
                server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg)
    
    def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook"""
        if not self.config.webhook_url:
            return
        
        payload = {
            "alert_id": alert.id,
            "rule_name": alert.rule_name,
            "level": alert.level.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "details": alert.details
        }
        
        response = requests.post(
            self.config.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    
    def _log_alert(self, alert: Alert):
        """Log alert to file"""
        log_entry = {
            "timestamp": alert.timestamp.isoformat(),
            "level": alert.level.value,
            "rule": alert.rule_name,
            "message": alert.message,
            "details": alert.details
        }
        
        # Write to log file
        log_file = "paper_trading_outputs/logs/alerts/alert_log.jsonl"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _get_color_for_level(self, level: AlertLevel) -> str:
        """Get color for alert level"""
        colors = {
            AlertLevel.INFO: "good",
            AlertLevel.WARNING: "warning",
            AlertLevel.CRITICAL: "danger",
            AlertLevel.EMERGENCY: "#FF0000"
        }
        return colors.get(level, "good")
    
    def _setup_escalation(self, alert: Alert, rule: AlertRule):
        """Setup escalation timer"""
        if alert.id in self.escalation_timers:
            return
        
        def escalate():
            if not alert.escalated:
                alert.escalated = True
                alert.escalation_count += 1
                alert.level = rule.escalation_level
                alert.message = f"ESCALATED: {alert.message}"
                self._send_alert(alert)
        
        timer = threading.Timer(rule.escalation_minutes * 60, escalate)
        timer.start()
        self.escalation_timers[alert.id] = timer
    
    def _log_error(self, message: str):
        """Log error message"""
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] AlertRouter ERROR: {message}")
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified hours"""
        cutoff = datetime.now(IST) - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alert router statistics"""
        now = time.time()
        recent_alerts = [alert for alert in self.alert_history 
                        if (now - alert.timestamp.timestamp()) < 3600]  # Last hour
        
        stats = {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled),
            "total_alerts": len(self.alert_history),
            "recent_alerts": len(recent_alerts),
            "active_cooldowns": len(self.cooldowns),
            "active_escalations": len(self.escalation_timers),
            "rate_limits": {
                rule_name: len(timestamps) 
                for rule_name, timestamps in self.rate_limits.items()
            }
        }
        
        return stats
    
    def close(self):
        """Close alert router and cleanup"""
        # Cancel all escalation timers
        for timer in self.escalation_timers.values():
            timer.cancel()
        
        self.escalation_timers.clear()

# Global alert router instance
_alert_router: Optional[AlertRouter] = None

def get_alert_router(config: Optional[AlertConfig] = None) -> AlertRouter:
    """Get global alert router instance"""
    global _alert_router
    if _alert_router is None:
        if config is None:
            config = AlertConfig()
        _alert_router = AlertRouter(config)
    return _alert_router

def close_alert_router():
    """Close global alert router"""
    global _alert_router
    if _alert_router is not None:
        _alert_router.close()
        _alert_router = None
