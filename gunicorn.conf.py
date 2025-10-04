# Gunicorn configuration file for HTTPS deployment
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "infotherapy"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL Configuration (if using direct SSL termination)
# keyfile = "/path/to/your/private.key"
# certfile = "/path/to/your/certificate.crt"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Preload app for better performance
preload_app = True

# Environment variables
raw_env = [
    "FLASK_ENV=production",
]
