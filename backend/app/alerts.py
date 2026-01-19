"""
alerts.py - Alert Detection and Management

This module checks metrics against thresholds and creates
alerts when limits are crossed.

Thresholds:
- Warning: When a metric is getting high (e.g., 70-85%)
- Critical: When a metric is dangerously high (e.g., >85%)
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Alert

# Default thresholds - can be customized later
THRESHOLDS = {
    "cpu": {
        "warning": 70,
        "critical": 85
    },
    "memory": {
        "warning": 75,
        "critical": 90
    },
    "disk": {
        "warning": 80,
        "critical": 95
    },
    "battery": {
        "warning": 20,   # Warning when LOW (below 20%)
        "critical": 10   # Critical when VERY LOW (below 10%)
    }
}


def check_and_create_alerts(metrics: dict, db: Session) -> list:
    """
    Checks all metrics against thresholds and creates alerts if needed.
    
    Parameters:
    - metrics: The current system metrics from get_all_metrics()
    - db: Database session
    
    Returns a list of any new alerts created.
    """
    new_alerts = []
    
    # Check CPU
    cpu_usage = metrics["cpu"]["usage_percent"]
    cpu_alert = check_metric(
        metric_type="cpu",
        value=cpu_usage,
        thresholds=THRESHOLDS["cpu"],
        higher_is_worse=True,
        db=db
    )
    if cpu_alert:
        new_alerts.append(cpu_alert)
    
    # Check Memory
    memory_usage = metrics["memory"]["usage_percent"]
    memory_alert = check_metric(
        metric_type="memory",
        value=memory_usage,
        thresholds=THRESHOLDS["memory"],
        higher_is_worse=True,
        db=db
    )
    if memory_alert:
        new_alerts.append(memory_alert)
    
    # Check Disk
    disk_usage = metrics["disk"]["usage_percent"]
    disk_alert = check_metric(
        metric_type="disk",
        value=disk_usage,
        thresholds=THRESHOLDS["disk"],
        higher_is_worse=True,
        db=db
    )
    if disk_alert:
        new_alerts.append(disk_alert)
    
    # Check Battery (if exists)
    if metrics["battery"]:
        battery_percent = metrics["battery"]["percent"]
        # Only alert if NOT plugged in
        if not metrics["battery"]["is_plugged"]:
            battery_alert = check_metric(
                metric_type="battery",
                value=battery_percent,
                thresholds=THRESHOLDS["battery"],
                higher_is_worse=False,  # For battery, LOWER is worse
                db=db
            )
            if battery_alert:
                new_alerts.append(battery_alert)
    
    return new_alerts


def check_metric(
    metric_type: str,
    value: float,
    thresholds: dict,
    higher_is_worse: bool,
    db: Session
) -> Alert | None:
    """
    Checks a single metric against its thresholds.
    
    Parameters:
    - metric_type: "cpu", "memory", "disk", or "battery"
    - value: The current value
    - thresholds: Dict with "warning" and "critical" levels
    - higher_is_worse: True for CPU/memory/disk, False for battery
    - db: Database session
    
    Returns an Alert if threshold crossed, None otherwise.
    """
    severity = None
    threshold_crossed = None
    
    if higher_is_worse:
        # CPU, Memory, Disk - higher values are bad
        if value >= thresholds["critical"]:
            severity = "critical"
            threshold_crossed = thresholds["critical"]
        elif value >= thresholds["warning"]:
            severity = "warning"
            threshold_crossed = thresholds["warning"]
    else:
        # Battery - lower values are bad
        if value <= thresholds["critical"]:
            severity = "critical"
            threshold_crossed = thresholds["critical"]
        elif value <= thresholds["warning"]:
            severity = "warning"
            threshold_crossed = thresholds["warning"]
    
    # No threshold crossed
    if severity is None:
        return None
    
    # Check if we already have an unacknowledged alert for this metric
    # (avoid spamming the same alert every 30 seconds)
    existing_alert = db.query(Alert).filter(
        Alert.metric_type == metric_type,
        Alert.severity == severity,
        Alert.acknowledged == False
    ).first()
    
    if existing_alert:
        # Update the existing alert with new value
        existing_alert.metric_value = value
        existing_alert.timestamp = datetime.now()
        db.commit()
        return None  # Don't count as "new" alert
    
    # Create new alert
    message = generate_alert_message(metric_type, value, threshold_crossed, severity)
    
    alert = Alert(
        timestamp=datetime.now(),
        metric_type=metric_type,
        metric_value=value,
        threshold_value=threshold_crossed,
        severity=severity,
        message=message,
        acknowledged=False
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    print(f"🚨 ALERT: {message}")
    
    return alert


def generate_alert_message(metric_type: str, value: float, threshold: float, severity: str) -> str:
    """
    Creates a human-readable alert message.
    """
    metric_names = {
        "cpu": "CPU usage",
        "memory": "Memory usage",
        "disk": "Disk usage",
        "battery": "Battery level"
    }
    
    metric_name = metric_names.get(metric_type, metric_type)
    severity_emoji = "⚠️" if severity == "warning" else "🔴"
    
    if metric_type == "battery":
        return f"{severity_emoji} {severity.upper()}: {metric_name} is low at {value}% (threshold: {threshold}%)"
    else:
        return f"{severity_emoji} {severity.upper()}: {metric_name} is high at {value}% (threshold: {threshold}%)"


def get_active_alerts(db: Session) -> list:
    """
    Gets all unacknowledged alerts.
    """
    alerts = db.query(Alert).filter(
        Alert.acknowledged == False
    ).order_by(Alert.timestamp.desc()).all()
    
    return [a.to_dict() for a in alerts]


def acknowledge_alert(alert_id: int, db: Session) -> bool:
    """
    Marks an alert as acknowledged (dismissed by user).
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.acknowledged = True
        db.commit()
        return True
    return False


def get_alert_history(hours: int, db: Session) -> list:
    """
    Gets alert history for the specified number of hours.
    """
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=hours)
    
    alerts = db.query(Alert).filter(
        Alert.timestamp >= cutoff
    ).order_by(Alert.timestamp.desc()).all()
    
    return [a.to_dict() for a in alerts]