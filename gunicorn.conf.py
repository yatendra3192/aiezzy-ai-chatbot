# Gunicorn configuration for production deployment
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000

# Timeouts
timeout = 1800  # 30 minutes for large file downloads
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "aiezzy"

# Server mechanics
preload_app = True
max_requests = 1000
max_requests_jitter = 100

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190