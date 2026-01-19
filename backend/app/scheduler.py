"""
scheduler.py - Background Task Scheduler

This file runs a background job that automatically collects
and saves system metrics every 30 seconds, and checks for alerts.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.database import SessionLocal
from app.models import MetricsSnapshot
from app.collector import get_all_metrics
from app.alerts import check_and_create_alerts

# Create the scheduler instance
scheduler = BackgroundScheduler()


def collect_and_save_metrics():
    """
    The job that runs every 30 seconds.
    
    It:
    1. Collects current system metrics
    2. Saves them to the database
    3. Checks for any threshold violations and creates alerts
    """
    db = SessionLocal()
    
    try:
        # Collect current metrics
        metrics = get_all_metrics()
        
        # Create a new snapshot record
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
        
        # Check for alerts
        new_alerts = check_and_create_alerts(metrics, db)
        
        # Log output
        alert_info = f" | {len(new_alerts)} new alert(s)" if new_alerts else ""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved snapshot - CPU: {metrics['cpu']['usage_percent']}%, Memory: {metrics['memory']['usage_percent']}%{alert_info}")
        
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """
    Starts the background scheduler.
    """
    scheduler.add_job(
        collect_and_save_metrics,
        trigger='interval',
        seconds=30,
        id='metrics_collector',
        replace_existing=True
    )
    
    scheduler.start()
    print("📊 Metrics collector started - saving every 30 seconds")
    print("🔔 Alert monitoring enabled")


def stop_scheduler():
    """
    Stops the scheduler gracefully.
    """
    scheduler.shutdown()
    print("📊 Metrics collector stopped")