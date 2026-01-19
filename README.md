# System Monitor

A real-time system monitoring dashboard that tracks CPU, memory, disk, battery, and network usage.


## Features

- **Real-time Monitoring**: CPU, Memory, Disk, Battery, Network
- **Per-Core CPU Usage**: Visual breakdown of each CPU core
- **Network Interfaces**: IP addresses, MAC addresses, speeds
- **Process Monitoring**: Top processes by CPU and memory usage
- **Historical Charts**: Track usage over time
- **Alert System**: Warnings when thresholds are exceeded
- **CSV Export**: Download metrics data for analysis

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, SQLAlchemy
- **Frontend**: React, Recharts, Lucide Icons
- **Containerization**: Docker, Docker Compose

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/jeena-krishna/system-monitor.git
cd system-monitor
```

Open `http://localhost` in your browser.

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

Open `http://localhost:3000` in your browser.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Current system metrics |
| `GET /metrics/history?hours=24` | Historical metrics |
| `GET /alerts` | Active alerts |
| `POST /alerts/{id}/acknowledge` | Dismiss an alert |
| `GET /export/csv?hours=24` | Download CSV export |
| `GET /docs` | API documentation |

## Project Structure

```
system-monitor/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── collector.py     # System metrics collection
│   │   ├── database.py      # Database configuration
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── alerts.py        # Alert system
│   │   └── scheduler.py     # Background tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.js           # Main React component
│   │   └── App.css          # Styles
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

## Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU | 70% | 85% |
| Memory | 75% | 90% |
| Disk | 80% | 95% |
| Battery | <20% | <10% |
