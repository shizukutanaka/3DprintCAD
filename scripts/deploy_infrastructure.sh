#!/bin/bash

# 3D Print CAD Assistant - Infrastructure Deployment Script
# Automated deployment for government-grade, enterprise-ready infrastructure
# Supports AWS, Azure, GCP, and on-premises Kubernetes clusters

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_ROOT/deployment/config.yaml}"
LOG_FILE="${LOG_FILE:-/tmp/3dcad-deploy-$(date +%Y%m%d-%H%M%S).log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
            ;;
    esac
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    local missing_tools=()

    # Check required tools
    for tool in kubectl helm docker terraform aws; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        error_exit "Missing required tools: ${missing_tools[*]}"
    fi

    # Check Kubernetes access
    if ! kubectl cluster-info &> /dev/null; then
        error_exit "Cannot access Kubernetes cluster. Please configure kubectl."
    fi

    # Check Helm
    if ! helm version &> /dev/null; then
        error_exit "Helm is not properly installed or configured."
    fi

    log "INFO" "Prerequisites check passed"
}

# Load configuration
load_config() {
    log "INFO" "Loading configuration from $CONFIG_FILE"

    if [ ! -f "$CONFIG_FILE" ]; then
        log "WARN" "Config file not found. Creating default configuration..."
        create_default_config
    fi

    # Parse YAML configuration (simplified - use yq in production)
    export ENVIRONMENT=$(grep "environment:" "$CONFIG_FILE" | cut -d: -f2 | xargs)
    export NAMESPACE=$(grep "namespace:" "$CONFIG_FILE" | cut -d: -f2 | xargs)
    export DOMAIN=$(grep "domain:" "$CONFIG_FILE" | cut -d: -f2 | xargs)
    export ENABLE_MONITORING=$(grep "enable_monitoring:" "$CONFIG_FILE" | cut -d: -f2 | xargs)
    export ENABLE_BACKUP=$(grep "enable_backup:" "$CONFIG_FILE" | cut -d: -f2 | xargs)
    export CLOUD_PROVIDER=$(grep "cloud_provider:" "$CONFIG_FILE" | cut -d: -f2 | xargs)

    log "INFO" "Configuration loaded: Environment=$ENVIRONMENT, Namespace=$NAMESPACE"
}

# Create default configuration
create_default_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"

    cat > "$CONFIG_FILE" << EOF
# 3D Print CAD Assistant Deployment Configuration
environment: production
namespace: 3dcad
domain: 3dcad.example.org
cloud_provider: aws

# Features
enable_monitoring: true
enable_backup: true
enable_security_scanning: true
enable_compliance: true

# Scaling
min_replicas: 3
max_replicas: 10
target_cpu_utilization: 70

# Security
enable_network_policies: true
enable_pod_security_policies: true
enable_rbac: true

# Monitoring
prometheus_retention: 30d
grafana_admin_password: CHANGE_ME

# Backup
backup_schedule: "0 2 * * *"
backup_retention_days: 30
s3_bucket: 3dcad-backups

# Database
postgres_version: "15"
postgres_storage_size: "100Gi"
postgres_backup_schedule: "0 1 * * *"

# Redis
redis_version: "7"
redis_storage_size: "10Gi"
EOF

    log "INFO" "Default configuration created at $CONFIG_FILE"
    log "WARN" "Please review and update the configuration before proceeding"
}

# Setup namespace and RBAC
setup_namespace() {
    log "INFO" "Setting up namespace and RBAC..."

    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    # Apply RBAC
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: 3dcad-service-account
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: 3dcad-cluster-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: 3dcad-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: 3dcad-cluster-role
subjects:
- kind: ServiceAccount
  name: 3dcad-service-account
  namespace: $NAMESPACE
EOF

    log "INFO" "Namespace and RBAC configured"
}

# Setup secrets
setup_secrets() {
    log "INFO" "Setting up secrets..."

    # Generate secure random passwords
    local secret_key=$(openssl rand -base64 32)
    local db_password=$(openssl rand -base64 32)
    local redis_password=$(openssl rand -base64 32)
    local grafana_password=$(openssl rand -base64 16)

    # Create application secrets
    kubectl create secret generic 3dcad-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=secret-key="$secret_key" \
        --from-literal=database-url="postgresql://postgres:$db_password@postgres-service:5432/3dcad" \
        --from-literal=redis-url="redis://:$redis_password@redis-service:6379/0" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Create monitoring secrets
    if [ "$ENABLE_MONITORING" = "true" ]; then
        kubectl create secret generic monitoring-secrets \
            --namespace="$NAMESPACE" \
            --from-literal=grafana-admin-password="$grafana_password" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi

    # Create TLS secrets (placeholder - replace with actual certificates)
    kubectl create secret tls 3dcad-tls-secret \
        --namespace="$NAMESPACE" \
        --cert=/dev/null \
        --key=/dev/null \
        --dry-run=client -o yaml | kubectl apply -f - || true

    log "INFO" "Secrets configured"
    log "WARN" "Please update TLS certificates with real certificates"
}

# Deploy PostgreSQL
deploy_postgresql() {
    log "INFO" "Deploying PostgreSQL..."

    # Add Bitnami Helm repository
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update

    # Deploy PostgreSQL
    helm upgrade --install postgres bitnami/postgresql \
        --namespace="$NAMESPACE" \
        --set auth.postgresPassword="$(kubectl get secret 3dcad-secrets -n $NAMESPACE -o jsonpath='{.data.database-url}' | base64 -d | cut -d: -f3 | cut -d@ -f1)" \
        --set auth.database=3dcad \
        --set persistence.size=100Gi \
        --set persistence.storageClass=gp2 \
        --set metrics.enabled=true \
        --set metrics.serviceMonitor.enabled="$ENABLE_MONITORING" \
        --wait

    log "INFO" "PostgreSQL deployed"
}

# Deploy Redis
deploy_redis() {
    log "INFO" "Deploying Redis..."

    helm upgrade --install redis bitnami/redis \
        --namespace="$NAMESPACE" \
        --set auth.password="$(kubectl get secret 3dcad-secrets -n $NAMESPACE -o jsonpath='{.data.redis-url}' | base64 -d | cut -d: -f3 | cut -d@ -f1)" \
        --set persistence.size=10Gi \
        --set persistence.storageClass=gp2 \
        --set metrics.enabled=true \
        --set metrics.serviceMonitor.enabled="$ENABLE_MONITORING" \
        --wait

    log "INFO" "Redis deployed"
}

# Deploy monitoring stack
deploy_monitoring() {
    if [ "$ENABLE_MONITORING" != "true" ]; then
        log "INFO" "Monitoring disabled, skipping..."
        return
    fi

    log "INFO" "Deploying monitoring stack..."

    # Add Prometheus community Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update

    # Deploy Prometheus
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace="$NAMESPACE" \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp2 \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set grafana.adminPassword="$(kubectl get secret monitoring-secrets -n $NAMESPACE -o jsonpath='{.data.grafana-admin-password}' | base64 -d)" \
        --set grafana.persistence.enabled=true \
        --set grafana.persistence.size=10Gi \
        --wait

    # Deploy custom dashboards
    deploy_custom_dashboards

    log "INFO" "Monitoring stack deployed"
}

# Deploy custom Grafana dashboards
deploy_custom_dashboards() {
    log "INFO" "Deploying custom dashboards..."

    # Create dashboard ConfigMap
    cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: 3dcad-dashboards
  namespace: $NAMESPACE
  labels:
    grafana_dashboard: "1"
data:
  3dcad-overview.json: |
    {
      "dashboard": {
        "title": "3D CAD Assistant Overview",
        "tags": ["3dcad"],
        "panels": [
          {
            "title": "Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{job=\"3dcad-assistant\"}[5m])"
              }
            ]
          },
          {
            "title": "Response Time",
            "type": "graph",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=\"3dcad-assistant\"}[5m]))"
              }
            ]
          },
          {
            "title": "Error Rate",
            "type": "singlestat",
            "targets": [
              {
                "expr": "rate(http_requests_total{job=\"3dcad-assistant\",status=~\"5..\"}[5m])"
              }
            ]
          }
        ]
      }
    }
EOF
}

# Deploy backup system
deploy_backup() {
    if [ "$ENABLE_BACKUP" != "true" ]; then
        log "INFO" "Backup disabled, skipping..."
        return
    fi

    log "INFO" "Deploying backup system..."

    # Create backup job
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: 3dcad-backup
  namespace: $NAMESPACE
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump \$DATABASE_URL > /backup/backup-\$(date +%Y%m%d-%H%M%S).sql
              aws s3 cp /backup/backup-\$(date +%Y%m%d-%H%M%S).sql s3://\$S3_BUCKET/
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: 3dcad-secrets
                  key: database-url
            - name: S3_BUCKET
              value: "3dcad-backups"
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            emptyDir: {}
          restartPolicy: OnFailure
EOF

    log "INFO" "Backup system deployed"
}

# Deploy main application
deploy_application() {
    log "INFO" "Deploying main application..."

    # Apply Kubernetes manifests
    kubectl apply -f "$PROJECT_ROOT/kubernetes/" -n "$NAMESPACE"

    # Wait for deployment to be ready
    kubectl rollout status deployment/3dcad-assistant -n "$NAMESPACE" --timeout=600s

    log "INFO" "Main application deployed"
}

# Setup ingress and TLS
setup_ingress() {
    log "INFO" "Setting up ingress and TLS..."

    # Install NGINX Ingress Controller
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update

    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --wait

    # Install cert-manager for automatic TLS certificates
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

    # Wait for cert-manager to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager

    # Create ClusterIssuer for Let's Encrypt
    cat << EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@${DOMAIN}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

    log "INFO" "Ingress and TLS configured"
}

# Setup network policies
setup_network_policies() {
    log "INFO" "Setting up network policies..."

    cat << EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: 3dcad-network-policy
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: 3dcad-assistant
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
    - protocol: UDP
      port: 53
EOF

    log "INFO" "Network policies configured"
}

# Run health checks
run_health_checks() {
    log "INFO" "Running health checks..."

    # Check application health
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if kubectl get pods -n "$NAMESPACE" -l app=3dcad-assistant --field-selector=status.phase=Running | grep -q Running; then
            log "INFO" "Application pods are running"
            break
        fi

        log "DEBUG" "Attempt $attempt/$max_attempts: Waiting for application pods..."
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        error_exit "Application failed to start within expected time"
    fi

    # Check database connectivity
    if kubectl exec -n "$NAMESPACE" deployment/3dcad-assistant -- python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; then
        log "INFO" "Database connectivity check passed"
    else
        error_exit "Database connectivity check failed"
    fi

    # Check Redis connectivity
    if kubectl exec -n "$NAMESPACE" deployment/3dcad-assistant -- python -c "
import redis
import os
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    exit(1)
" 2>/dev/null; then
        log "INFO" "Redis connectivity check passed"
    else
        error_exit "Redis connectivity check failed"
    fi

    log "INFO" "All health checks passed"
}

# Generate deployment report
generate_report() {
    log "INFO" "Generating deployment report..."

    local report_file="/tmp/3dcad-deployment-report-$(date +%Y%m%d-%H%M%S).txt"

    cat > "$report_file" << EOF
3D Print CAD Assistant Deployment Report
========================================
Deployment Date: $(date)
Environment: $ENVIRONMENT
Namespace: $NAMESPACE
Domain: $DOMAIN

Components Deployed:
- Main Application: ✅
- PostgreSQL Database: ✅
- Redis Cache: ✅
- Monitoring Stack: $([ "$ENABLE_MONITORING" = "true" ] && echo "✅" || echo "❌")
- Backup System: $([ "$ENABLE_BACKUP" = "true" ] && echo "✅" || echo "❌")
- Ingress Controller: ✅
- TLS Certificates: ✅
- Network Policies: ✅

Application URLs:
- Main Application: https://$DOMAIN
- Grafana Dashboard: https://$DOMAIN/grafana (if monitoring enabled)
- Prometheus: https://$DOMAIN/prometheus (if monitoring enabled)

Next Steps:
1. Update DNS records to point $DOMAIN to the LoadBalancer IP
2. Review and update TLS certificates if needed
3. Configure monitoring alerts
4. Set up backup verification
5. Perform security audit
6. Configure compliance monitoring

Credentials:
- Database password: Stored in secret '3dcad-secrets'
- Redis password: Stored in secret '3dcad-secrets'
- Grafana admin password: Stored in secret 'monitoring-secrets'

Support:
- Logs: kubectl logs -n $NAMESPACE -l app=3dcad-assistant
- Status: kubectl get all -n $NAMESPACE
- Monitoring: kubectl port-forward -n $NAMESPACE svc/prometheus-server 9090:80

For additional support, refer to the documentation or contact the development team.
EOF

    log "INFO" "Deployment report generated: $report_file"
    cat "$report_file"
}

# Main deployment function
main() {
    local start_time=$(date +%s)

    log "INFO" "Starting 3D Print CAD Assistant infrastructure deployment"
    log "INFO" "Deployment log: $LOG_FILE"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --skip-monitoring)
                ENABLE_MONITORING="false"
                shift
                ;;
            --skip-backup)
                ENABLE_BACKUP="false"
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --config FILE          Configuration file path"
                echo "  --environment ENV      Environment (production, staging, development)"
                echo "  --namespace NS         Kubernetes namespace"
                echo "  --domain DOMAIN        Application domain"
                echo "  --skip-monitoring      Skip monitoring stack deployment"
                echo "  --skip-backup          Skip backup system deployment"
                echo "  --help                 Show this help message"
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done

    # Execute deployment steps
    check_prerequisites
    load_config
    setup_namespace
    setup_secrets
    deploy_postgresql
    deploy_redis
    deploy_monitoring
    deploy_backup
    deploy_application
    setup_ingress
    setup_network_policies
    run_health_checks
    generate_report

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log "INFO" "Deployment completed successfully in ${duration} seconds"
    log "INFO" "Application should be available at: https://$DOMAIN"
}

# Run main function with all arguments
main "$@"