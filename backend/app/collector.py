"""
collector.py - System Metrics Collector (Extended)

This module gathers comprehensive system information:
- CPU: usage, per-core usage, model, frequency
- Memory: RAM and Swap
- Disk: usage and partitions
- Battery: status and time remaining
- Network: I/O stats, IP addresses, MAC addresses
- System: hostname, OS, uptime
- Processes: top processes by CPU/memory
"""

import psutil
import platform
import socket
from datetime import datetime


def get_cpu_metrics():
    """
    Collects comprehensive CPU information.
    """
    # Per-core CPU usage
    per_core = psutil.cpu_percent(interval=1, percpu=True)
    
    # CPU frequency (current, min, max)
    freq = psutil.cpu_freq()
    
    # CPU times (for more detailed analysis)
    cpu_times = psutil.cpu_times_percent(interval=0)
    
    return {
        "usage_percent": psutil.cpu_percent(interval=0),
        "core_count": psutil.cpu_count(logical=False),
        "logical_count": psutil.cpu_count(logical=True),
        "frequency_mhz": freq.current if freq else None,
        "frequency_min_mhz": freq.min if freq else None,
        "frequency_max_mhz": freq.max if freq else None,
        "per_core_percent": per_core,
        "cpu_times": {
            "user": cpu_times.user,
            "system": cpu_times.system,
            "idle": cpu_times.idle
        }
    }


def get_memory_metrics():
    """
    Collects RAM and Swap memory information.
    """
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        "ram": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "usage_percent": mem.percent,
            "cached_gb": round(getattr(mem, 'cached', 0) / (1024**3), 2),
            "buffers_gb": round(getattr(mem, 'buffers', 0) / (1024**3), 2)
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "free_gb": round(swap.free / (1024**3), 2),
            "usage_percent": swap.percent
        },
        # Keep these for backward compatibility
        "total_gb": round(mem.total / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "usage_percent": mem.percent
    }


def get_disk_metrics():
    """
    Collects disk usage and partition information.
    """
    # Main disk
    disk = psutil.disk_usage('/')
    
    # All partitions
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_percent": round(usage.percent, 1)
            })
        except (PermissionError, OSError):
            # Skip partitions we can't access
            continue
    
    # Disk I/O
    disk_io = psutil.disk_io_counters()
    
    return {
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "usage_percent": round(disk.percent, 1),
        "partitions": partitions,
        "io": {
            "read_mb": round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
            "write_mb": round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0,
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0
        }
    }


def get_battery_metrics():
    """
    Collects battery information (for laptops).
    """
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    
    return {
        "percent": battery.percent,
        "is_plugged": battery.power_plugged,
        "time_remaining_mins": round(battery.secsleft / 60) if battery.secsleft > 0 else None
    }


def get_network_metrics():
    """
    Collects network I/O and interface information.
    """
    # Network I/O
    net = psutil.net_io_counters()
    
    # Network interfaces with IP and MAC addresses
    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    
    for iface_name, iface_addrs in addrs.items():
        iface_info = {
            "name": iface_name,
            "ipv4": None,
            "ipv6": None,
            "mac": None,
            "is_up": stats[iface_name].isup if iface_name in stats else False,
            "speed_mbps": stats[iface_name].speed if iface_name in stats else 0
        }
        
        for addr in iface_addrs:
            if addr.family == socket.AF_INET:  # IPv4
                iface_info["ipv4"] = addr.address
                iface_info["netmask"] = addr.netmask
            elif addr.family == socket.AF_INET6:  # IPv6
                iface_info["ipv6"] = addr.address
            elif addr.family == psutil.AF_LINK:  # MAC address
                iface_info["mac"] = addr.address
        
        interfaces.append(iface_info)
    
    return {
        "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
        "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "errors_in": net.errin,
        "errors_out": net.errout,
        "interfaces": interfaces
    }


def get_system_info():
    """
    Collects general system information.
    """
    # Boot time and uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.now() - boot_time).total_seconds()
    
    # Convert uptime to readable format
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    # Get primary IP address
    primary_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except:
        primary_ip = "Unknown"
    
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "boot_time": boot_time.isoformat(),
        "uptime": {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "total_seconds": int(uptime_seconds)
        },
        "primary_ip": primary_ip
    }


def get_top_processes(limit=10):
    """
    Gets the top processes by CPU and memory usage.
    """
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
        try:
            pinfo = proc.info
            processes.append({
                "pid": pinfo['pid'],
                "name": pinfo['name'],
                "cpu_percent": pinfo['cpu_percent'] or 0,
                "memory_percent": round(pinfo['memory_percent'] or 0, 2),
                "status": pinfo['status'],
                "username": pinfo['username']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Sort by CPU usage and get top N
    top_by_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
    
    # Sort by memory usage and get top N
    top_by_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]
    
    return {
        "total_count": len(processes),
        "top_by_cpu": top_by_cpu,
        "top_by_memory": top_by_memory
    }


def get_all_metrics():
    """
    Collects ALL system metrics at once.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "cpu": get_cpu_metrics(),
        "memory": get_memory_metrics(),
        "disk": get_disk_metrics(),
        "battery": get_battery_metrics(),
        "network": get_network_metrics(),
        "processes": get_top_processes(10)
    }


# For testing
if __name__ == "__main__":
    import json
    metrics = get_all_metrics()
    print(json.dumps(metrics, indent=2))