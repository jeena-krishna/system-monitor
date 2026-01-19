"""
main.py - FastAPI Application Entry Point

This is the "front door" of your application. It:
1. Creates a web server
2. Defines URL routes (endpoints)
3. Connects those routes to your collector functions
4. Saves metrics to database for historical tracking
5. Runs automatic collection every 30 seconds
"""

import csv
import io
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.collector import (
    get_all_metrics, 
    get_cpu_metrics, 
    get_memory_metrics, 
    get_disk_metrics, 
    get_battery_metrics, 
    get_network_metrics
)
from app.database import engine, get_db, Base
from app.models import MetricsSnapshot
from app.scheduler import start_scheduler, stop_scheduler
from app.alerts import get_active_alerts, acknowledge_alert, get_alert_history, THRESHOLDS

# Create all database tables on startup
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager - runs code on startup and shutdown.
    
    - Code before 'yield' runs when the app STARTS
    - Code after 'yield' runs when the app STOPS
    
    This is where we start/stop our background scheduler.
    """
    # Startup: Start the background scheduler
    start_scheduler()
    yield
    # Shutdown: Stop the scheduler gracefully
    stop_scheduler()


# Create the FastAPI application instance
app = FastAPI(
    title="System Monitor API",
    description="A plug-and-play API that monitors your system's health",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware - allows your React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint - welcome message and available endpoints."""
    return {
        "message": "Welcome to System Monitor API",
        "docs_url": "/docs",
        "endpoints": {
            "all_metrics": "/metrics",
            "cpu": "/metrics/cpu",
            "memory": "/metrics/memory",
            "disk": "/metrics/disk",
            "battery": "/metrics/battery",
            "network": "/metrics/network",
            "save_snapshot": "/metrics/snapshot (POST)",
            "history": "/metrics/history?hours=1"
        }
    }


@app.get("/metrics")
def all_metrics():
    """Returns ALL current system metrics."""
    return get_all_metrics()


@app.get("/metrics/cpu")
def cpu_metrics():
    """Returns only CPU information."""
    return get_cpu_metrics()


@app.get("/metrics/memory")
def memory_metrics():
    """Returns only memory/RAM information."""
    return get_memory_metrics()


@app.get("/metrics/disk")
def disk_metrics():
    """Returns only disk/storage information."""
    return get_disk_metrics()


@app.get("/metrics/battery")
def battery_metrics():
    """Returns only battery information."""
    return get_battery_metrics()


@app.get("/metrics/network")
def network_metrics():
    """Returns only network I/O information."""
    return get_network_metrics()


@app.post("/metrics/snapshot")
def save_snapshot(db: Session = Depends(get_db)):
    """
    Manually collects current metrics and saves them to the database.
    
    Note: With the scheduler running, snapshots are saved automatically
    every 30 seconds. This endpoint is for manual/on-demand saves.
    """
    metrics = get_all_metrics()
    
    snapshot = MetricsSnapshot(
        timestamp=datetime.fromisoformat(metrics["timestamp"]),
        cpu_usage_percent=metrics["cpu"]["usage_percent"],
        cpu_core_count=metrics["cpu"]["core_count"],
        cpu_logical_count=metrics["cpu"]["logical_count"],
        cpu_frequency_mhz=metrics["cpu"]["frequency_mhz"],
        memory_total_gb=metrics["memory"]["total_gb"],
        memory_used_gb=metrics["memory"]["used_gb"],
        memory_available_gb=metrics["memory"]["available_gb"],
        memory_usage_percent=metrics["memory"]["usage_percent"],
        disk_total_gb=metrics["disk"]["total_gb"],
        disk_used_gb=metrics["disk"]["used_gb"],
        disk_free_gb=metrics["disk"]["free_gb"],
        disk_usage_percent=metrics["disk"]["usage_percent"],
        battery_percent=metrics["battery"]["percent"] if metrics["battery"] else None,
        battery_is_plugged=metrics["battery"]["is_plugged"] if metrics["battery"] else None,
        battery_time_remaining_mins=metrics["battery"]["time_remaining_mins"] if metrics["battery"] else None,
        network_bytes_sent_mb=metrics["network"]["bytes_sent_mb"],
        network_bytes_recv_mb=metrics["network"]["bytes_recv_mb"],
        network_packets_sent=metrics["network"]["packets_sent"],
        network_packets_recv=metrics["network"]["packets_recv"],
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return {
        "message": "Snapshot saved successfully",
        "snapshot": snapshot.to_dict()
    }


@app.get("/metrics/history")
def get_history(
    hours: int = Query(default=1, ge=1, le=168, description="Hours of history to retrieve (1-168)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves historical metrics from the database.
    
    Parameters:
    - hours: How many hours of history to fetch (default: 1, max: 168 = 7 days)
    
    Returns all snapshots from the last N hours, ordered by time.
    """
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    snapshots = db.query(MetricsSnapshot).filter(
        MetricsSnapshot.timestamp >= cutoff_time
    ).order_by(MetricsSnapshot.timestamp.asc()).all()
    
    return {
        "hours_requested": hours,
        "snapshot_count": len(snapshots),
        "snapshots": [s.to_dict() for s in snapshots]
    }


@app.get("/alerts")
def active_alerts(db: Session = Depends(get_db)):
    """
    Gets all active (unacknowledged) alerts.
    """
    return {
        "alerts": get_active_alerts(db),
        "count": len(get_active_alerts(db))
    }


@app.get("/alerts/history")
def alerts_history(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Gets alert history for the specified hours.
    """
    alerts = get_alert_history(hours, db)
    return {
        "hours_requested": hours,
        "alerts": alerts,
        "count": len(alerts)
    }


@app.post("/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Acknowledges (dismisses) an alert.
    """
    success = acknowledge_alert(alert_id, db)
    if success:
        return {"message": "Alert acknowledged", "alert_id": alert_id}
    return {"error": "Alert not found", "alert_id": alert_id}


@app.get("/alerts/thresholds")
def get_thresholds():
    """
    Gets the current alert thresholds.
    """
    return THRESHOLDS


@app.get("/export/csv")
def export_csv(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of data to export"),
    db: Session = Depends(get_db)
):
    """
    Exports metrics history as a CSV file.
    
    This creates a downloadable CSV with all metrics from the specified time period.
    Perfect for analysis in Excel, Google Sheets, or data science tools.
    """
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    snapshots = db.query(MetricsSnapshot).filter(
        MetricsSnapshot.timestamp >= cutoff_time
    ).order_by(MetricsSnapshot.timestamp.asc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'Timestamp',
        'CPU Usage %',
        'CPU Cores',
        'CPU Threads',
        'CPU Frequency MHz',
        'Memory Total GB',
        'Memory Used GB',
        'Memory Available GB',
        'Memory Usage %',
        'Disk Total GB',
        'Disk Used GB',
        'Disk Free GB',
        'Disk Usage %',
        'Battery %',
        'Battery Plugged',
        'Network Sent MB',
        'Network Received MB'
    ])
    
    # Write data rows
    for s in snapshots:
        writer.writerow([
            s.timestamp.isoformat() if s.timestamp else '',
            s.cpu_usage_percent,
            s.cpu_core_count,
            s.cpu_logical_count,
            s.cpu_frequency_mhz,
            s.memory_total_gb,
            s.memory_used_gb,
            s.memory_available_gb,
            s.memory_usage_percent,
            s.disk_total_gb,
            s.disk_used_gb,
            s.disk_free_gb,
            s.disk_usage_percent,
            s.battery_percent,
            s.battery_is_plugged,
            s.network_bytes_sent_mb,
            s.network_bytes_recv_mb
        ])
    
    # Prepare response
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=system_metrics_{hours}h.csv"
        }
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}