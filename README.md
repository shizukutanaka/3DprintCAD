# 3D Print CAD Assistant

A secure additive manufacturing validation, repair, and optimization platform engineered for national-scale and enterprise deployments.

国や大企業の調達要件に耐える 3D モデル検証・補修・最適化プラットフォームです。CLI 中心のワークフローを前提としつつ、Web UI や自動化スクリプトと統合できる構成になっています。セキュリティ、性能、保守性、ユーザー体験をバランス良く備えています。

---

## 利用シナリオ
- **単品検証**: 設計チームから受け取った STL／3MF を即時分析し、壁厚やサポート必要箇所を可視化した JSON レポートを配布します。
- **夜間バッチ**: 国防・航空案件など大量の CAD データを夜間に並列検証し、タイムアウト時は自動的に逐次処理へ切替えて完了させます。
- **規制産業向け監査**: 署名付き設定とハッシュマニフェストを必須化し、`src/core/compliance_manager.py` で証跡チェーンを検証します。
- **安全な共同作業**: 制限ネットワーク内に Web UI を立ち上げ、CLI と同一ポリシーでファイル検証・補修を実施します。

---

## 重点機能

### 信頼性の高い検証
- メッシュ検証 (`src/core/analysis`): 非多様体検出、穴・自己交差、オーバーハングのリスク評価
- 解析レポート: 体積・表面積・サポート推奨を JSON 形式で出力
- 自動補修: `repair_mesh()` によるトポロジ整形と再検証ループ

### セキュリティとガバナンス
- ハッシュマニフェスト強制 (`--hash-manifest`): サイズ・エントリ数の制限と署名付き設定ファイル検証
- ディレクトリ制限: `application.allowed_input_roots` と `application.allowed_output_root` による I/O ガード
- 監査証跡: 暗号化チェーン、鍵ローテーション、アクセスログの改ざん検知
- CLI ワーカー制御: CPU 構成に応じて `--max-workers` を自動的に安全値へ丸め込み

### 運用性とユーザー体験
- 二言語 CLI (`--language en|ja|bilingual`) と `README_JP.md` による現場対応
- 自動サマリー／メトリクス／失敗レポート生成 (`--auto-summary`, `--auto-metrics`, `--auto-failures`)
- プログレス表示、ROI 推計、キャッシュ整合性チェックによる運用効率化

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd 3DprintCAD

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install CLI tool
pip install -e .
```

### Basic Usage

**CLI - Validate a single model:**
```bash
printcad model.stl --output report.json --summary
```

**CLI - Batch processing:**
```bash
printcad --batch "models/*.stl" --parallel --auto-summary
```

**Web Interface:**
```bash
python run_server.py --host 0.0.0.0 --port 5000
# Open browser to http://localhost:5000
```

---

## What's Included

- **CLI Tool** (`printcad`): Validation, repair, batch processing with comprehensive reporting
- **Web Application**: Intuitive interface for file upload, validation, and 3D visualization
- **RESTful API**: Integration-ready endpoints for external systems
- **Health Monitoring**: System diagnostics and operational metrics
- **Compliance Manager**: Audit logging, encryption, and regulatory reporting
- **Security Layer**: Multi-tier protection with rate limiting and input validation

---

## Prerequisites

- Windows 10+, macOS 11+, or Ubuntu 20.04+
- Python 3.9+ (3.11 tested)
- 8 GB RAM minimum (16 GB recommended for large batches)
- Disk space for models, logs, and compliance artefacts (~2 GB to start)

---

## Installation (local CLI)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Confirm the command works:

```bash
printcad --help
python -m src.cli_main --help
```

---

## Secure configuration checklist

- **Hash manifest** (`--hash-manifest`): require SHA-256 digests before processing production data.
- **File size limits**: set `application.max_file_size_mb` in configuration or use CLI defaults (100 MB via `MAX_UPLOAD_MB`).
- **Batch upload limits**: cap concurrent uploads by setting `MAX_BATCH_FILES` (defaults to 20) to avoid resource exhaustion in `/api/batch`.
- **Language mode**: select `--language en|ja|bilingual`; defaults come from `self.language_mode` inside `CLIProcessor`.
- **Environment hardening**:
  - `SECRET_KEY` must be set for production CLI summaries and the web app (`src/web/app.py`).
  - `MAX_UPLOAD_MB`, `UPLOAD_DIR`, and `RESULTS_DIR` should point to storage you control.
  - `ALLOWED_UPLOAD_MIMETYPES` restricts uploads to approved CAD formats (comma-separated, e.g. `application/sla,model/stl`).
  - `PRINTCAD_COLLAB_BASE_URL` must reference the HTTPS endpoint of your collaboration API; optional `PRINTCAD_COLLAB_WS_URL` can override the derived WebSocket endpoint.
  - `CDN_RESOURCES_FILE` can point to a JSON catalog of CDN assets. It is also selectable at runtime with `--resources-file` when running `generate_cdn_hashes.py`.

---

## CLI workflows

### Single-model validation

```bash
printcad model.stl \
  --output reports/model.json \
  --summary \
  --hash-manifest manifests/production.json
```

### Batch with watchdog fallback

```bash
printcad --batch "models/*.stl" \
  --parallel \
  --max-workers 4 \
  --auto-summary \
  --auto-metrics \
  --failure-output reports/failures.json
```

`process_batch()` will cancel overdue workers, log a warning, add `"was_timeout": True` in the result, and rerun remaining meshes sequentially.

### Compliance evidence snapshots

```bash
python - <<'PY'
from src.core.compliance_manager import ComplianceManager, ComplianceStandard

manager = ComplianceManager()
assessment = manager.assess_compliance(ComplianceStandard.SOC2_TYPE2, "Security Officer")
print(assessment.overall_score)

report = manager.verify_audit_chain()
print(report)
PY
```

---

## Web application

1. Prepare environment variables:
   ```bash
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
   export MAX_UPLOAD_MB=200
   export MAX_BATCH_FILES=20
   export ALLOWED_UPLOAD_MIMETYPES="application/sla,model/stl"
   export UPLOAD_DIR="$(pwd)/uploads"
   export RESULTS_DIR="$(pwd)/results"
   # Set the collaboration API endpoint used by your organization
   export PRINTCAD_COLLAB_BASE_URL="<collaboration-api-url>"
   # Optional when WebSocket endpoint differs from the API host
   # export PRINTCAD_COLLAB_WS_URL="<realtime-endpoint>"
   mkdir -p "$UPLOAD_DIR" "$RESULTS_DIR"
   chmod 700 "$UPLOAD_DIR" "$RESULTS_DIR"  # POSIX systems
   ```
2. Launch:
   ```bash
   python run_server.py --host 0.0.0.0 --port 5000
   ```
3. Access `http://localhost:5000` and upload meshes. Each upload goes through `sanitize_filename()` and `secure_path_resolution()`; MIME types outside `ALLOWED_UPLOAD_MIMETYPES` are rejected.
4. Probes:
   - `GET /health` returns liveness information.
   - `GET /ready` verifies storage directories and secret configuration; it returns HTTP 503 until the instance is ready.

---

## Configuration management

Settings cascade in `src/core/config.py`:

1. Repository defaults (`default_config.yaml` embedded).
2. Files under `PRINTCAD_CONFIG_DIR` or the working directory.
3. Environment variables (e.g., `MAX_UPLOAD_MB`, `MAX_WORKERS`).
4. CLI arguments.

Edit `config/production.yaml` (example):

```yaml
application:
  environment: production
  enforce_hash_manifest: true

validation:
  min_wall_thickness: 0.4
  min_feature_size: 0.25

processing:
  max_workers: 8
  worker_timeout_seconds: 120

logging:
  log_file_path: logs/printcad.log
  redaction_rules:
    - "api_key"
```

---

## Deployment options

### Docker (local validation)

```bash
docker compose up --build
```

`docker-compose.yml` starts the app, Postgres, and Redis with development defaults. For hardened settings, use `docker-compose.production.yml` and supply an `.env` file for secrets.

### Kubernetes

`kubernetes/deployment.yaml` defines a reference deployment. Before applying, ensure:

- `SECRET_KEY` is stored in `3dcad-secrets`.
- Persistent volumes back `UPLOAD_DIR` and `RESULTS_DIR`.
- Network ingress is locked to trusted sources.

Apply with:

```bash
kubectl apply -f kubernetes/deployment.yaml
```

### Reverse proxy

`nginx.conf` ships an example configuration enforcing TLS, security headers, and request size limits. Adjust upstream paths if you run behind an external load balancer.

---

## Security operations

- **Hash manifest enforcement**: Provide a JSON manifest of file digests. When using `--hash-policy strict`, mismatches stop processing.
- **Upload isolation**: Keep `UPLOAD_DIR`/`RESULTS_DIR` on dedicated volumes. Inspect and purge old artefacts regularly.
- **Audit log integrity**:
  ```bash
  python - <<'PY'
  from src.core.compliance_manager import ComplianceManager
  manager = ComplianceManager()
  result = manager.verify_audit_chain()
  assert result["valid"], result
  PY
  ```
- **Key rotation**:
  ```bash
  python - <<'PY'
  from src.core.compliance_manager import ComplianceManager
  manager = ComplianceManager()
  manager.rotate_encryption_key()
  PY
  ```
  Back up encrypted evidence (`compliance_data/`) before rotating keys.

---

## CDN hash maintenance

- **Generate hashes**: Run `python generate_cdn_hashes.py --print-config` to review active settings and `python generate_cdn_hashes.py --list-resources` to inspect tracked assets.
- **Persist catalogue**: Maintain external definitions in a JSON file referenced by `CDN_RESOURCES_FILE` or the CLI flag `--resources-file`. Example:

  ```json
  {
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "threejs_custom": {
      "url": "https://cdn.example.com/threejs/custom.min.js"
    }
  }
  ```

- **Update hashes**: `python generate_cdn_hashes.py --resources-file cdn_resources.json --output cdn_hashes.json` writes the computed SRI hashes for deployment manifests.
- **Integrity comparison**: Use `--compare-integrity` to validate generated hashes against `src/core/cdn_manager.py` definitions before publishing.

---

## Monitoring and maintenance

- Enable structured logging via `application.log_file_path` and forward to your SIEM.
- Review `reports/auto-summary`, `reports/auto-metrics`, and `reports/failures` after each batch.
- Track timeout warnings from `process_batch()` to identify geometry workloads that exceed the configured watchdog.
- Schedule periodic clean-up of `uploads/` and `results/` according to retention policies.

---

## Quality checks

Run automated checks before release:

```bash
make lint       # flake8, mypy
make test       # pytest suite
make coverage   # coverage report
```

Add optional scanners to CI (examples): `pip-audit`, `bandit`, `trivy fs .`.

---

## Documentation

### For Users
        - **[Installation Guide](docs/PRODUCTION_DEPLOYMENT.md)**: Complete setup instructions for production
        - **[User Guide](docs/USER_GUIDE.md)**: End-to-end usage documentation
        - **[API Reference](docs/API.md)**: Complete API endpoint documentation
        - **[FAQ](docs/FAQ.md)**: Frequently asked questions

### For Administrators
- **[Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)**: Enterprise deployment with Kubernetes
- **[Security Hardening](docs/SECURITY_HARDENING.md)**: Government-grade security configuration
- **[Monitoring & Operations](docs/OPERATIONS.md)**: Operational runbooks and procedures
- **[Automation Guide](docs/AUTOMATION_GUIDE.md)**: End-to-end automation workflows and safeguards
- **[Improvements Implemented](docs/IMPROVEMENTS_IMPLEMENTED.md)**: Logged enhancements ready for rollout
- **[Improvement Backlog (High Priority)](docs/improvement_backlog_high_priority.md)**: Upcoming operational initiatives

### For Developers
- **[Architecture Overview](docs/overview.md)**: System design and component documentation
- **[Development Guide](docs/DEVELOPMENT.md)**: Contributing and development setup
- **[API Integration](docs/INTEGRATION.md)**: Integration examples and SDKs
- **[Changelog](CHANGELOG.md)**: Version history and release notes

---

## Security

Security is our top priority. This system implements:

- **Multi-layer input validation** (client and server-side)
- **SQL injection prevention** with parameterized queries
- **XSS protection** with CSP nonces and sanitization
- **Path traversal protection** with secure path resolution
- **Rate limiting** to prevent abuse and DDoS attacks
- **Encryption** for sensitive data (AES-256-GCM)
- **Audit logging** with tamper-proof chain verification
- **Regular security scanning** with automated vulnerability detection

### Reporting Security Issues

Please report security vulnerabilities through your organization's designated security channel. Do not open public issues for security concerns.

See [SECURITY_HARDENING.md](docs/SECURITY_HARDENING.md) for complete security documentation.

---

## Production Deployment

### Quick Deploy with Docker

```bash
# Build production image
docker compose -f docker-compose.production.yml build

# Start services
docker compose -f docker-compose.production.yml up -d

# Check health
curl "$PRODUCTION_BASE_URL/health"
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods -l app=3dcad-assistant
```

See [PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) for detailed production setup including:
- Database configuration (PostgreSQL)
- Cache setup (Redis)
- Load balancing (Nginx/HAProxy)
- SSL/TLS certificates
- Backup strategies
- Monitoring integration

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd 3DprintCAD
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements_dev.txt

# Run tests
pytest tests/ -v --cov=src

# Run linting
flake8 src/ tests/
mypy src/

# Run security scan
bandit -r src/
```

---

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+, Windows 10+, macOS 11+
- **Python**: 3.9 or higher
- **RAM**: 8 GB
- **Storage**: 50 GB
- **CPU**: 2 cores

### Recommended for Production
- **OS**: Ubuntu 22.04 LTS or RHEL 8+
- **Python**: 3.11+
- **RAM**: 16 GB+ (32 GB for large batches)
- **Storage**: 500 GB+ SSD
- **CPU**: 4+ cores
- **Network**: 1 Gbps+

---

## License

3D Print CAD Assistant is released under the **MIT License**. See [LICENSE](LICENSE) for details.

```
Copyright (c) 2025 Your Organization

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Full MIT License text in LICENSE file]
```

---

## Acknowledgments

Built with these excellent open-source projects:
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Trimesh](https://trimsh.org/) - 3D mesh processing
- [NumPy](https://numpy.org/) - Numerical computing
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Redis](https://redis.io/) - Caching and sessions

---

## Support

- **Documentation**: Refer to `docs/`
- **Issues**: Use your organization's issue tracker for this project
- **Security**: Escalate through the internal security response process
- **General**: Contact the support channels defined by your organization

---

## Roadmap

### Version 2.0 (Q2 2025)
- [ ] Machine learning-based defect detection
- [ ] Advanced support structure generation
- [ ] Multi-material optimization
- [ ] Cloud-native distributed processing

### Version 2.1 (Q3 2025)
- [ ] Real-time collaboration features
- [ ] Mobile application (iOS/Android)
- [ ] Advanced slicing algorithms
- [ ] Integration with popular CAD software

See [ROADMAP.md](docs/ROADMAP.md) for complete development plans.

---

**Built with ❤️ for the additive manufacturing community**