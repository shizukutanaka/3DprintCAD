# Production Deployment Guide / 本番環境デプロイメントガイド

## 概要 / Overview

This comprehensive guide provides step-by-step instructions for deploying 3D Print CAD Assistant in production environments suitable for national-level usage. It covers infrastructure setup, security hardening, monitoring, and operational procedures.

本ガイドは、3D Print CAD Assistantを国家レベルで使用可能な本番環境にデプロイするための包括的な手順を提供します。インフラ設定、セキュリティ強化、監視、運用手順をカバーします。

---

## Prerequisites / 前提条件

### Infrastructure Requirements
- **Compute**: 4+ vCPU, 16GB+ RAM (per instance)
- **Storage**: 500GB+ SSD (for models, logs, backups)
- **Network**: 1Gbps+ bandwidth, static IP address
- **OS**: Ubuntu 22.04 LTS or RHEL 8+ (recommended)

### Software Requirements
- Python 3.11+
- PostgreSQL 15+ (for data persistence)
- Redis 7+ (for caching and sessions)
- Nginx 1.24+ (reverse proxy)
- Docker 24+ / Kubernetes 1.28+ (containerized deployment)

### Security Requirements
- SSL/TLS certificates (valid commercial CA)
- HSM or KMS for encryption keys
- SIEM integration capability
- Backup infrastructure with encryption

---

## Architecture Overview / アーキテクチャ概要

```
┌─────────────────────────────────────────────────────┐
│               Load Balancer (HA)                     │
│              (Nginx / AWS ALB)                       │
└─────────────────┬───────────────────────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼────┐  ┌───▼─────┐ ┌───▼─────┐
│ App     │  │ App     │ │ App     │
│ Server  │  │ Server  │ │ Server  │
│ (Flask) │  │ (Flask) │ │ (Flask) │
└────┬────┘  └───┬─────┘ └───┬─────┘
     │           │            │
     └───────────┼────────────┘
                 │
     ┌───────────┼────────────┐
     │           │            │
┌────▼────┐ ┌───▼─────┐ ┌───▼──────┐
│ PostgreSQL│ │ Redis  │ │ S3/Minio │
│ (Primary) │ │ Cluster│ │ Storage  │
└────┬────┘ └─────────┘ └──────────┘
     │
┌────▼────┐
│PostgreSQL│
│(Replica) │
└─────────┘
```

---

## Step 1: Environment Preparation / 環境準備

### 1.1 Create Application User
```bash
# Create dedicated application user
sudo useradd -r -s /bin/bash -m -d /opt/printcad printcad
sudo passwd printcad  # Set strong password

# Create directory structure
sudo -u printcad mkdir -p /opt/printcad/{app,data,logs,backups,config}
sudo chmod 700 /opt/printcad/config
sudo chmod 750 /opt/printcad/{data,logs,backups}
```

### 1.2 Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql-client \
    redis-tools \
    nginx \
    supervisor \
    fail2ban \
    ufw \
    unattended-upgrades

# Enable automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 1.3 Configure Firewall
```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Install and configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Step 2: Database Setup / データベース設定

### 2.1 PostgreSQL Installation and Configuration
```bash
# Install PostgreSQL
sudo apt install postgresql-15 postgresql-contrib-15

# Secure PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'STRONG_PASSWORD_HERE';"

# Create application database and user
sudo -u postgres psql <<EOF
CREATE DATABASE printcad_production;
CREATE USER printcad_app WITH ENCRYPTED PASSWORD 'APP_DB_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON DATABASE printcad_production TO printcad_app;
ALTER DATABASE printcad_production OWNER TO printcad_app;
\c printcad_production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOF
```

### 2.2 PostgreSQL Hardening
```bash
# Edit postgresql.conf
sudo vim /etc/postgresql/15/main/postgresql.conf

# Add/modify these settings:
ssl = on
ssl_ciphers = 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256'
password_encryption = scram-sha-256
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'all'
max_connections = 100
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 64MB

# Edit pg_hba.conf for secure access
sudo vim /etc/postgresql/15/main/pg_hba.conf

# Add/modify:
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     scram-sha-256
host    printcad_production  printcad_app    127.0.0.1/32       scram-sha-256
host    printcad_production  printcad_app    ::1/128            scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 2.3 Redis Setup
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo vim /etc/redis/redis.conf

# Modify these settings:
bind 127.0.0.1 ::1
protected-mode yes
requirepass YOUR_STRONG_REDIS_PASSWORD_HERE
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Enable Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server
```

---

## Step 3: Application Deployment / アプリケーションデプロイ

### 3.1 Clone and Setup Application
```bash
# Switch to printcad user
sudo -u printcad -i

# Clone repository (or copy application files)
cd /opt/printcad/app
git clone https://your-repository/3DprintCAD.git .
# Or: rsync -av /path/to/source/ /opt/printcad/app/

# Create virtual environment
python3.11 -m venv /opt/printcad/venv
source /opt/printcad/venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn gevent psycopg2-binary redis
```

### 3.2 Environment Configuration
```bash
# Create production environment file
cat > /opt/printcad/config/.env.production <<'EOF'
# Application Settings
FLASK_ENV=production
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
PYTHONUNBUFFERED=1

# Database Configuration
DATABASE_URL=postgresql://printcad_app:APP_DB_PASSWORD_HERE@localhost:5432/printcad_production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://:YOUR_REDIS_PASSWORD_HERE@localhost:6379/0
REDIS_SESSION_DB=1

# Security Settings
ENFORCE_TLS=1
ALLOWED_ORIGINS=https://your-production-domain.com
MAX_UPLOAD_MB=100
MAX_BATCH_FILES=20
REQUEST_TIMEOUT_SECONDS=60
ALLOWED_UPLOAD_MIMETYPES=application/sla,model/stl,model/obj,model/3mf

# Storage Configuration
UPLOAD_DIR=/opt/printcad/data/uploads
RESULTS_DIR=/opt/printcad/data/results
BACKUP_DIR=/opt/printcad/backups

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/printcad/logs/app.log
STRUCTURED_LOGGING=1

# Compliance and Audit
AUDIT_LOG_DIR=/opt/printcad/logs/audit
COMPLIANCE_DATA_DIR=/opt/printcad/data/compliance
PRINTCAD_CONFIG_HMAC_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')

# Encryption
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Monitoring
SENTRY_DSN=  # Add if using Sentry
STATSD_HOST=localhost
STATSD_PORT=8125

# Workers
MAX_WORKERS=8
WORKER_TIMEOUT_SECONDS=120

# Rate Limiting
RATE_LIMIT_STORAGE_URL=redis://:YOUR_REDIS_PASSWORD_HERE@localhost:6379/2
EOF

# Secure environment file
chmod 600 /opt/printcad/config/.env.production

# Create required directories
mkdir -p /opt/printcad/data/{uploads,results,compliance}
mkdir -p /opt/printcad/logs/audit
mkdir -p /opt/printcad/backups
chmod 700 /opt/printcad/data/compliance
chmod 750 /opt/printcad/data/{uploads,results}
chmod 750 /opt/printcad/logs
```

### 3.3 Database Migration
```bash
# Activate environment
source /opt/printcad/venv/bin/activate
export $(cat /opt/printcad/config/.env.production | xargs)

# Run database migrations (create tables)
python -c "
from src.core.config import get_config
from src.core.compliance_manager import ComplianceManager
# Initialize database schema
# Add your migration logic here
"
```

---

## Step 4: Gunicorn Configuration / Gunicorn設定

### 4.1 Create Gunicorn Configuration
```bash
# Create gunicorn config
cat > /opt/printcad/config/gunicorn.conf.py <<'EOF'
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Logging
accesslog = "/opt/printcad/logs/gunicorn_access.log"
errorlog = "/opt/printcad/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "printcad"

# Server mechanics
daemon = False
pidfile = "/opt/printcad/app/gunicorn.pid"
user = "printcad"
group = "printcad"
umask = 0o027

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (if terminating SSL at application level - not recommended)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
EOF
```

### 4.2 Create Systemd Service
```bash
# Create systemd service file
sudo cat > /etc/systemd/system/printcad.service <<'EOF'
[Unit]
Description=3D Print CAD Assistant Production Server
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=notify
User=printcad
Group=printcad
WorkingDirectory=/opt/printcad/app
EnvironmentFile=/opt/printcad/config/.env.production
ExecStart=/opt/printcad/venv/bin/gunicorn \
    --config /opt/printcad/config/gunicorn.conf.py \
    "run_server:app"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
PrivateTmp=true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=printcad

# Security hardening
NoNewPrivileges=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/printcad/data /opt/printcad/logs /opt/printcad/backups
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=false
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Resource limits
LimitNOFILE=65536
LimitNPROC=512

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable printcad.service
sudo systemctl start printcad.service
sudo systemctl status printcad.service
```

---

## Step 5: Nginx Configuration / Nginx設定

### 5.1 SSL Certificate Setup
```bash
# Option 1: Let's Encrypt (for public-facing servers)
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-production-domain.com

# Option 2: Commercial certificate
# Place your certificate files:
# /etc/ssl/certs/printcad.crt
# /etc/ssl/private/printcad.key
sudo chmod 600 /etc/ssl/private/printcad.key
```

### 5.2 Nginx Configuration
```bash
# Create Nginx configuration
sudo cat > /etc/nginx/sites-available/printcad <<'EOF'
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/m;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Upstream application servers
upstream printcad_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    # Add more backend servers for HA:
    # server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    # server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name your-production-domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-production-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-production-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-production-domain.com/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/your-production-domain.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Resource-Policy "same-origin" always;

    # Logging
    access_log /var/log/nginx/printcad_access.log combined;
    error_log /var/log/nginx/printcad_error.log warn;

    # Connection limits
    limit_conn conn_limit 10;

    # General settings
    client_max_body_size 100M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    keepalive_timeout 65s;
    send_timeout 60s;

    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_redirect off;

    # Root location
    location / {
        proxy_pass http://printcad_backend;
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://printcad_backend;
        proxy_read_timeout 120s;
    }

    # Upload endpoint with stricter rate limiting
    location /api/upload {
        limit_req zone=upload_limit burst=5 nodelay;
        proxy_pass http://printcad_backend;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Health check endpoint (no rate limiting for monitoring)
    location /health {
        access_log off;
        proxy_pass http://printcad_backend;
    }

    # Static files (if served by Nginx)
    location /static/ {
        alias /opt/printcad/app/src/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/printcad /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 6: Monitoring and Logging / 監視とログ記録

### 6.1 Log Rotation
```bash
# Create logrotate configuration
sudo cat > /etc/logrotate.d/printcad <<'EOF'
/opt/printcad/logs/*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 0640 printcad printcad
    sharedscripts
    postrotate
        systemctl reload printcad.service > /dev/null 2>&1 || true
    endscript
}

/opt/printcad/logs/audit/*.log {
    daily
    rotate 2555  # 7 years
    compress
    delaycompress
    notifempty
    create 0600 printcad printcad
    missingok
}
EOF
```

### 6.2 Health Check Script
```bash
# Create health check script
cat > /opt/printcad/scripts/health_check.sh <<'EOF'
#!/bin/bash
set -euo pipefail

HEALTH_URL="http://localhost:8000/health"
READY_URL="http://localhost:8000/ready"
LOG_FILE="/opt/printcad/logs/health_check.log"

check_health() {
    local url="$1"
    local name="$2"

    if response=$(curl -sf -m 5 "$url" 2>&1); then
        echo "[$(date -Iseconds)] $name OK" >> "$LOG_FILE"
        return 0
    else
        echo "[$(date -Iseconds)] $name FAILED: $response" >> "$LOG_FILE"
        return 1
    fi
}

# Check application health
if ! check_health "$HEALTH_URL" "Health"; then
    systemctl restart printcad.service
    sleep 10
fi

# Check readiness
check_health "$READY_URL" "Readiness" || exit 1

exit 0
EOF

chmod +x /opt/printcad/scripts/health_check.sh

# Add to cron
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/printcad/scripts/health_check.sh") | crontab -
```

---

## Step 7: Backup Strategy / バックアップ戦略

### 7.1 Database Backup
```bash
# Create backup script
cat > /opt/printcad/scripts/backup_database.sh <<'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/printcad/backups/database"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/printcad_db_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Export database password
export PGPASSWORD="APP_DB_PASSWORD_HERE"

# Perform backup
pg_dump -h localhost -U printcad_app -d printcad_production | gzip > "$BACKUP_FILE"

# Encrypt backup
openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" -out "$BACKUP_FILE.enc" -pass pass:"$ENCRYPTION_KEY"
rm "$BACKUP_FILE"

# Remove old backups
find "$BACKUP_DIR" -name "*.enc" -mtime +$RETENTION_DAYS -delete

echo "[$(date -Iseconds)] Database backup completed: $BACKUP_FILE.enc"
EOF

chmod +x /opt/printcad/scripts/backup_database.sh

# Schedule daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/printcad/scripts/backup_database.sh") | crontab -
```

### 7.2 Application Data Backup
```bash
# Create data backup script
cat > /opt/printcad/scripts/backup_data.sh <<'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/printcad/backups/data"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/printcad_data_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

# Backup uploads, results, and compliance data
tar -czf "$BACKUP_FILE" \
    -C /opt/printcad/data \
    uploads results compliance

# Encrypt backup
openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" -out "$BACKUP_FILE.enc" -pass pass:"$ENCRYPTION_KEY"
rm "$BACKUP_FILE"

# Remove old backups
find "$BACKUP_DIR" -name "*.enc" -mtime +$RETENTION_DAYS -delete

echo "[$(date -Iseconds)] Data backup completed: $BACKUP_FILE.enc"
EOF

chmod +x /opt/printcad/scripts/backup_data.sh

# Schedule weekly backups
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/printcad/scripts/backup_data.sh") | crontab -
```

---

## Step 8: Security Hardening / セキュリティ強化

### 8.1 System Hardening
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
sudo systemctl disable avahi-daemon.service

# Configure kernel parameters
sudo cat >> /etc/sysctl.conf <<'EOF'
# Network security
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0

# Connection limits
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
EOF

sudo sysctl -p
```

### 8.2 Intrusion Detection
```bash
# Install AIDE (Advanced Intrusion Detection Environment)
sudo apt install aide
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Schedule daily integrity checks
(sudo crontab -l 2>/dev/null; echo "0 5 * * * /usr/bin/aide --check") | sudo crontab -
```

---

## Step 9: Deployment Verification / デプロイ検証

### 9.1 Smoke Tests
```bash
# Test application health
curl -f https://your-production-domain.com/health

# Test readiness
curl -f https://your-production-domain.com/ready

# Test API (with authentication if required)
curl -X POST https://your-production-domain.com/api/upload \
    -F "file=@test_model.stl" \
    -H "Authorization: Bearer YOUR_TOKEN"

# Check logs
sudo journalctl -u printcad.service -n 50
tail -f /opt/printcad/logs/app.log
tail -f /var/log/nginx/printcad_access.log
```

### 9.2 Load Testing
```bash
# Install Apache Bench or similar
sudo apt install apache2-utils

# Perform load test
ab -n 1000 -c 10 https://your-production-domain.com/health

# Monitor resources during load test
htop
iotop
nethogs
```

---

## Step 10: Operational Procedures / 運用手順

### 10.1 Deployment Updates
```bash
# Update application code
sudo -u printcad -i
cd /opt/printcad/app
git pull origin main  # Or copy new files

# Install new dependencies
source /opt/printcad/venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
# python scripts/migrate.py

# Reload application (zero-downtime reload)
sudo systemctl reload printcad.service

# Verify deployment
curl -f https://your-production-domain.com/health
```

### 10.2 Emergency Rollback
```bash
# Revert to previous version
cd /opt/printcad/app
git reset --hard <previous-commit-hash>

# Reload application
sudo systemctl reload printcad.service
```

### 10.3 Log Analysis
```bash
# View application logs
sudo journalctl -u printcad.service --since "1 hour ago"

# Check for errors
grep -i error /opt/printcad/logs/app.log | tail -n 50

# Analyze Nginx access logs
awk '{print $1}' /var/log/nginx/printcad_access.log | sort | uniq -c | sort -rn | head -20
```

---

## Troubleshooting / トラブルシューティング

### Common Issues

**Issue**: Application fails to start
**Solution**:
```bash
# Check service status
sudo systemctl status printcad.service

# Check logs
sudo journalctl -u printcad.service -n 100

# Verify environment variables
sudo -u printcad cat /opt/printcad/config/.env.production

# Test manually
sudo -u printcad -i
cd /opt/printcad/app
source /opt/printcad/venv/bin/activate
export $(cat /opt/printcad/config/.env.production | xargs)
python run_server.py
```

**Issue**: Database connection failures
**Solution**:
```bash
# Test database connectivity
psql -h localhost -U printcad_app -d printcad_production

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Verify pg_hba.conf settings
sudo cat /etc/postgresql/15/main/pg_hba.conf
```

**Issue**: High memory usage
**Solution**:
```bash
# Check memory consumption
free -h
ps aux --sort=-%mem | head -20

# Adjust Gunicorn workers
# Edit /opt/printcad/config/gunicorn.conf.py
# Reduce workers or use worker_class = "sync" instead of "gevent"

# Restart service
sudo systemctl restart printcad.service
```

---

## Compliance Checklist / コンプライアンスチェックリスト

### Pre-Production Checklist

- [ ] All secrets stored in environment variables or secret management system
- [ ] SSL/TLS certificates installed and configured
- [ ] Database encrypted at rest and in transit
- [ ] Strong passwords set for all services
- [ ] Firewall configured and enabled
- [ ] Fail2ban configured and monitoring logs
- [ ] Log rotation configured
- [ ] Backup strategy implemented and tested
- [ ] Health checks and monitoring in place
- [ ] Security headers configured in Nginx
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] CSRF protection enabled
- [ ] CSP headers configured
- [ ] System hardening completed
- [ ] Intrusion detection system installed
- [ ] Audit logging enabled
- [ ] Compliance manager initialized
- [ ] Disaster recovery plan documented
- [ ] Incident response procedures documented

### Regular Maintenance Schedule

- **Daily**: Check health status, review error logs
- **Weekly**: Review security alerts, check disk space
- **Monthly**: Security patch updates, certificate expiration checks
- **Quarterly**: Full security audit, penetration testing
- **Annually**: Disaster recovery testing, compliance audit

---

## Contact and Support / 連絡先とサポート

For production deployment support:
- **Security Issues**: security@your-organization.com
- **Operations**: ops@your-organization.com
- **Emergency**: +1-800-EMERGENCY (24/7)

---

## Appendix: High Availability Setup / 付録: 高可用性設定

### Multi-Server Deployment

For national-level deployments requiring high availability:

1. **Load Balancer**: Deploy HAProxy or AWS ALB with health checks
2. **Application Servers**: 3+ instances across availability zones
3. **Database**: PostgreSQL replication (primary-standby or multi-master)
4. **Shared Storage**: NFS, GlusterFS, or S3-compatible object storage
5. **Session Management**: Redis Sentinel or Redis Cluster
6. **Monitoring**: Prometheus + Grafana for metrics and alerting

See `docs/HIGH_AVAILABILITY.md` for detailed HA deployment guide.

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-06
**Maintained By**: Infrastructure Team
