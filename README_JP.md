# 3Dプリント CADアシスタント

本ドキュメントは、3Dプリント CADアシスタント（コマンド名 `printcad`）を規制産業の実務に展開する際に必要な手順と運用ポイントをまとめています。利用者目線で、セットアップから日常運用、セキュリティ管制までを網羅しています。

---

## クイックサマリー

- **CLIが主軸**: `printcad`（`pyproject.toml` のエントリーポイント）は検証・修復・スライス・レポート出力を統合。実装は `src/cli_main.py`。
- **Web補助**: `run_server.py` が `src/web/app.py` を起動し、CLIと同じ検証ルールでアップロードを受け付け。`ALLOWED_UPLOAD_MIMETYPES` による MIME 制限に対応。
- **コンプライアンス対応**: `src/core/compliance_manager.py` が暗号化証跡と連鎖ハッシュを保持し、鍵ローテーションで運用を継続。
- **バッチ耐障害性**: `process_batch()` がタイムアウトワーカーをキャンセルし、警告ログと共に残件を逐次再処理。
- **アップロード衛生**: `sanitize_filename()` と `secure_path_resolution()` でディレクトリ逸脱を防止し、保存先を隔離。

---

## 必要環境

- **OS**: Windows 10 以上 / macOS 11 以上 / Ubuntu 20.04 以上
- **Python**: 3.9 以上（3.11 動作確認済み）
- **メモリ**: 8 GB 以上（大規模バッチは 16 GB 推奨）
- **ストレージ**: 2 GB 以上（モデル、レポート、証跡ファイル用）

---

## インストール（CLI ローカル）

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

起動確認:

```bash
printcad --help
python -m src.cli_main --help
```

---

## セキュア設定チェックリスト

- **ハッシュマニフェスト**: `--hash-manifest` で SHA-256 マニフェストを必須化。厳格モード（`--hash-policy strict`）が既定。
- **最大ファイルサイズ**: 設定ファイルの `application.max_file_size_mb` または環境変数 `MAX_UPLOAD_MB` で制御。
- **言語設定**: `--language en|ja|bilingual` を指定。既定値は `CLIProcessor` の初期設定。
- **環境変数**:
  - `SECRET_KEY`: CLI サマリーと Flask セッションの暗号鍵（本番必須）。
  - `UPLOAD_DIR` / `RESULTS_DIR`: ファイル保存先。専用ディレクトリを用意。
  - `ALLOWED_UPLOAD_MIMETYPES`: `src/web/api.py` が参照する MIME ホワイトリスト（例 `application/sla,model/stl`）。
  - `CDN_RESOURCES_FILE`: `generate_cdn_hashes.py` 実行時に読み込む CDN リソース定義 JSON を指示。CLI の `--resources-file` でも指定可能。

---

## CLI ワークフロー

### 単一モデル検証

```bash
printcad model.stl \
  --output reports/model.json \
  --summary \
  --hash-manifest manifests/production.json
```

### ウォッチドッグ付きバッチ

```bash
printcad --batch "models/*.stl" \
  --parallel \
  --max-workers 4 \
  --auto-summary \
  --auto-metrics \
  --failure-output reports/failures.json
```

タイムアウト発生時は `"was_timeout": True` を付けてログ出力し、残りのファイルを逐次再処理します。

### コンプライアンス証跡

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

   ```bash
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
   export MAX_UPLOAD_MB=200
   export MAX_BATCH_FILES=20
   export ALLOWED_UPLOAD_MIMETYPES="application/sla,model/stl"
   export UPLOAD_DIR="$(pwd)/uploads"
   export RESULTS_DIR="$(pwd)/results"
   # 組織で運用しているコラボレーションAPIエンドポイントを設定
   export PRINTCAD_COLLAB_BASE_URL="<コラボレーションAPIのURL>"
   # WebSocketエンドポイントが異なる場合のみ設定
   # export PRINTCAD_COLLAB_WS_URL="<リアルタイムエンドポイント>"
   mkdir -p "$UPLOAD_DIR" "$RESULTS_DIR"
   chmod 700 "$UPLOAD_DIR" "$RESULTS_DIR"  # POSIX
   ```
2. サーバーを起動:
   ```bash
   python run_server.py --host 0.0.0.0 --port 5000
   ```
3. ブラウザで `http://localhost:5000` にアクセス。非許可 MIME やディレクトリ逸脱は `secure_path_resolution()` が拒否します。
4. プローブ:
   - `GET /health` は稼働状態を返します。
   - `GET /ready` はストレージディレクトリとシークレット設定を検証し、準備完了までは HTTP 503 を返します。

---

## 設定管理

- **階層構造**: `src/core/config.py` が既定値 → 設定ファイル → 環境変数 → CLI 引数の順で反映。
- **例: `config/production.yaml`**

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

## デプロイメント

### Docker（ローカル検証）

```bash
docker compose up --build
```

`docker-compose.yml` がアプリ・Postgres・Redis を開発向け設定で起動します。本番用途は `docker-compose.production.yml` と `.env` で機密情報を供給してください。

### Kubernetes

`kubernetes/deployment.yaml` を適用する前に、以下を確認します。

- `SECRET_KEY` を `3dcad-secrets` に格納。
- 永続ボリュームを `UPLOAD_DIR` と `RESULTS_DIR` に割り当て。
- 信頼済みネットワークのみからアクセス可能に制限。

```bash
kubectl apply -f kubernetes/deployment.yaml
```

### リバースプロキシ

`nginx.conf` は TLS、セキュリティヘッダー、リクエスト制限の参考設定です。実際のインフラに合わせてアップストリーム定義を調整してください。

---

## セキュリティ運用

- **ハッシュ確認**: `--hash-manifest` と厳格モードで未承認ファイルを即時遮断。
- **アップロード隔離**: `UPLOAD_DIR` と `RESULTS_DIR` を専用ボリュームに分離し、定期的に棚卸し。
- **監査チェーン検証**:
  ```bash
  python - <<'PY'
  from src.core.compliance_manager import ComplianceManager
  manager = ComplianceManager()
  result = manager.verify_audit_chain()
  assert result["valid"], result
  PY
  ```
- **鍵ローテーション**:
  ```bash
  python - <<'PY'
  from src.core.compliance_manager import ComplianceManager
  manager = ComplianceManager()
  manager.rotate_encryption_key()
  PY
  ```
  実施前に `compliance_data/` をバックアップしてください。

---

## CDNハッシュ保守

- **設定確認**: `python generate_cdn_hashes.py --print-config` で有効な設定を確認し、`--list-resources` で対象リソースを一覧表示。
- **カタログ管理**: `CDN_RESOURCES_FILE`（または CLI の `--resources-file`）で外部 JSON カタログを指定。例:

  ```json
  {
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "threejs_custom": {
      "url": "https://cdn.example.com/threejs/custom.min.js"
    }
  }
  ```

- **ハッシュ生成**: `python generate_cdn_hashes.py --resources-file cdn_resources.json --output cdn_hashes.json` を実行し、配布用 JSON を更新。
- **整合性検証**: `--compare-integrity` を併用し、`src/core/cdn_manager.py` の既存定義と照合してからデプロイに反映。

---

## 運用・保守

- **ログ管理**: `application.log_file_path` を設定し、SIEM 等へ転送。
- **レポート確認**: `reports/auto-summary`、`reports/auto-metrics`、`reports/failures` を業務フローに取り込み。
- **タイムアウト分析**: `process_batch()` の警告ログから難処理モデルを特定し、しきい値やワーカー数を調整。
- **ディレクトリ整備**: アップロード済みデータは保持期間に応じてアーカイブまたは削除。

---

## 品質チェック

```bash
make lint       # flake8 と mypy
make test       # pytest 一式
make coverage   # カバレッジレポート
```

CI には `pip-audit` や `bandit`、`trivy fs .` 等の追加スキャンを推奨します。

---

## ドキュメント構成

- **`docs/overview.md`**: システム全体の俯瞰
- **`docs/SECURITY_HARDENING.md`**: 配備ハードニング手順
- **`docs/improvement_plan.md`**: 改善計画と進捗
- **`docs/backlog.md`**: 詳細な改善候補リスト

---

## ライセンス

3Dプリント CADアシスタントは MIT ライセンスで提供されています。詳細は `LICENSE` を参照してください。