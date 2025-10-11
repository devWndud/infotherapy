import os

bind = "0.0.0.0:8000"
backlog = 2048

workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

max_requests = 1000
max_requests_jitter = 50

accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

proc_name = "infotherapy"

daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None


limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

preload_app = True

raw_env = [
    "FLASK_ENV=production",
]
