"""
models.py - Database Models (Tables)

This file defines the structure of your database tables.
Each class represents a table, and each attribute represents a column.

SQLAlchemy will read these classes and create the actual
tables in your SQLite database automatically.
"""

from sqlalchemy import Column, Integer, Float, Boolean, DateTime, String
from datetime import datetime
from app.database import Base


class MetricsSnapshot(Base):
    """
    Stores a complete snapshot of system metrics at a point in time.
    
    Every time we collect metrics, we save a row in this table.
    This allows us to query historical data like:
    - "Show me CPU usage for the last hour"
    - "What was memory usage yesterday at 3pm?"
    
    Table name: metrics_snapshots
    """
    
    __tablename__ = "metrics_snapshots"
    
    # Primary key - unique identifier for each row
    # autoincrement means SQLite assigns 1, 2, 3, etc. automatically
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # When this snapshot was taken
    # index=True makes searching by timestamp fast
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # CPU metrics
    cpu_usage_percent = Column(Float)
    cpu_core_count = Column(Integer)
    cpu_logical_count = Column(Integer)
    cpu_frequency_mhz = Column(Float, nullable=True)
    
    # Memory metrics
    memory_total_gb = Column(Float)
    memory_used_gb = Column(Float)
    memory_available_gb = Column(Float)
    memory_usage_percent = Column(Float)
    
    # Disk metrics
    disk_total_gb = Column(Float)
    disk_used_gb = Column(Float)
    disk_free_gb = Column(Float)
    disk_usage_percent = Column(Float)
    
    # Battery metrics (nullable - desktops don't have batteries)
    battery_percent = Column(Float, nullable=True)
    battery_is_plugged = Column(Boolean, nullable=True)
    battery_time_remaining_mins = Column(Integer, nullable=True)
    
    # Network metrics
    network_bytes_sent_mb = Column(Float)
    network_bytes_recv_mb = Column(Float)
    network_packets_sent = Column(Integer)
    network_packets_recv = Column(Integer)
    
    def to_dict(self):
        """
        Converts this database row to a dictionary.
        
        Useful for returning data from API endpoints,
        since FastAPI needs dictionaries to convert to JSON.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cpu": {
                "usage_percent": self.cpu_usage_percent,
                "core_count": self.cpu_core_count,
                "logical_count": self.cpu_logical_count,
                "frequency_mhz": self.cpu_frequency_mhz
            },
            "memory": {
                "total_gb": self.memory_total_gb,
                "used_gb": self.memory_used_gb,
                "available_gb": self.memory_available_gb,
                "usage_percent": self.memory_usage_percent
            },
            "disk": {
                "total_gb": self.disk_total_gb,
                "used_gb": self.disk_used_gb,
                "free_gb": self.disk_free_gb,
                "usage_percent": self.disk_usage_percent
            },
            "battery": {
                "percent": self.battery_percent,
                "is_plugged": self.battery_is_plugged,
                "time_remaining_mins": self.battery_time_remaining_mins
            } if self.battery_percent is not None else None,
            "network": {
                "bytes_sent_mb": self.network_bytes_sent_mb,
                "bytes_recv_mb": self.network_bytes_recv_mb,
                "packets_sent": self.network_packets_sent,
                "packets_recv": self.network_packets_recv
            }
        }


class Alert(Base):
    """
    Stores alerts when metrics cross defined thresholds.
    
    For example, if CPU goes above 80%, an alert is created
    with severity "warning" or "critical".
    """
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # What metric triggered the alert (cpu, memory, disk, battery)
    metric_type = Column(String(50))
    
    # The actual value that triggered the alert
    metric_value = Column(Float)
    
    # The threshold that was crossed
    threshold_value = Column(Float)
    
    # Severity: "warning" or "critical"
    severity = Column(String(20))
    
    # Human-readable message
    message = Column(String(500))
    
    # Has the user acknowledged/dismissed this alert?
    acknowledged = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "severity": self.severity,
            "message": self.message,
            "acknowledged": self.acknowledged
        }