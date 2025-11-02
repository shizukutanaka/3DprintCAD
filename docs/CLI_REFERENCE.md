# CLIクイックリファレンス / CLI Quick Reference

## コマンド概要 / Command Overview

```bash
printcad [ファイル...] [オプション]
```

## 基本オプション / Basic Options

### 入力ファイル / Input Files
```
ファイル名          検証する3Dモデルファイル
--pattern PATTERN  ファイルパターンマッチ（例: "*.stl"）
--input-dir DIR    ディレクトリ内全ファイルを処理
```

### 出力制御 / Output Control
```
-o, --output FILE     結果出力ファイル（JSON）
--summary             サマリー表示
--verbose, -v         詳細出力
--quiet, -q           静粛モード
--progress            進捗表示（デフォルト有効）
--no-progress         進捗表示無効
```

### 処理モード / Processing Modes
```
-b, --batch           バッチ処理モード
-p, --parallel        並列処理
-w, --max-workers N   並列ワーカー数（デフォルト: 4）
--validate            検証実行（デフォルト）
--repair              メッシュ修復
--aggressive-repair   積極的修復
--slice               スライス実行
--gcode               G-code生成
```

## 検証設定 / Validation Settings

### 寸法閾値 / Dimensional Thresholds
```
--min-wall FLOAT      最小壁厚（mm、デフォルト: 0.8）
--min-feature FLOAT   最小特徴サイズ（mm、デフォルト: 0.4）
--overhang-angle FLOAT 最大オーバーハング角度（°、デフォルト: 60）
```

### 印刷設定 / Print Settings
```
--layer-height FLOAT  層厚（mm、デフォルト: 0.2）
--infill INT          インフィル率（%、デフォルト: 20）
--speed FLOAT         印刷速度（mm/s、デフォルト: 60）
--temp-nozzle INT     ノズル温度（°C、デフォルト: 210）
--temp-bed INT        ベッド温度（°C、デフォルト: 60）
```

## 高度なオプション / Advanced Options

### セキュリティ / Security
```
--hash-manifest FILE  SHA-256マニフェストファイル
--hash-policy strict|warn マニフェスト強制ポリシー
--read-only-output    ファイル書き込み禁止
```

### レポート / Reporting
```
--auto-summary        自動サマリー生成
--auto-metrics        自動メトリクス生成
--auto-failures       自動失敗レポート生成
--summary-output FILE サマリー出力ファイル
--metrics-output FILE メトリクス出力ファイル（JSONL/JSON）
--failure-output FILE 失敗レポート出力ファイル
```

### 品質管理 / Quality Control
```
--fail-on-warnings    警告時失敗扱い
--max-risk-score FLOAT 最大リスクスコア
--min-readiness-score FLOAT 最小準備スコア
--max-warning-count INT 最大警告数
--exit-on-first-failure 初回失敗時終了
```

### 言語設定 / Language Settings
```
--language en|ja|bilingual 出力言語
```

## 使用例 / Usage Examples

### 基本的な検証 / Basic Validation
```bash
# 単一ファイル検証
printcad model.stl

# 詳細出力付き
printcad model.stl --summary --verbose

# JSONレポート生成
printcad model.stl --output report.json
```

### バッチ処理 / Batch Processing
```bash
# 複数ファイル
printcad file1.stl file2.obj file3.3mf

# ワイルドカード使用
printcad models/*.stl

# 並列処理
printcad --batch "models/*.stl" --parallel --max-workers 8
```

### 修復処理 / Repair Processing
```bash
# 自動修復
printcad model.stl --repair

# 修復済みモデル保存
printcad model.stl --repair --save-repaired fixed.stl

# 積極的修復
printcad model.stl --aggressive-repair --save-repaired fixed.stl
```

### 完全ワークフロー / Complete Workflow
```bash
# 検証からG-code生成まで
printcad model.stl \
  --validate \
  --repair \
  --slice \
  --gcode \
  --output model.gcode \
  --summary
```

### 品質ゲート / Quality Gates
```bash
# 厳格な品質チェック
printcad model.stl \
  --fail-on-warnings \
  --max-risk-score 0.5 \
  --min-readiness-score 80 \
  --max-warning-count 5
```

### レポート生成 / Report Generation
```bash
# 全レポート自動生成
printcad --batch "models/*.stl" \
  --auto-summary \
  --auto-metrics \
  --auto-failures \
  --parallel
```

## 終了コード / Exit Codes

```
0  成功 / Success
1  一般エラー / General error
2  引数エラー / Argument error
3  ファイルエラー / File error
4  検証エラー / Validation error
5  メモリエラー / Memory error
```

## 設定ファイル / Configuration Files

### 場所 / Locations
- `config/production.yaml` - 本番設定
- `config/development.yaml` - 開発設定
- `~/.printcad/config.yaml` - ユーザ設定

### 環境変数 / Environment Variables
```
PRINTCAD_CONFIG_DIR     設定ファイルディレクトリ
MAX_UPLOAD_MB           最大ファイルサイズ（MB）
MAX_WORKERS             最大ワーカー数
SECRET_KEY              Flaskセッションキー
```

## トラブルシューティング / Troubleshooting

### 一般的な問題 / Common Issues

#### メモリ不足 / Out of Memory
```bash
# ワーカー数を減らす
printcad large_model.stl --max-workers 1

# チャンク処理を使用
printcad large_model.stl --chunk-size 1000000
```

#### 処理が遅い / Slow Processing
```bash
# 並列処理を有効化
printcad --batch "models/*.stl" --parallel --max-workers 8

# 詳細度を下げる
printcad model.stl --validation-level basic
```

#### ファイル形式エラー / File Format Error
```bash
# サポート形式を確認
printcad --list-formats

# ファイル変換
# STL変換ツール等を使用
```

### デバッグオプション / Debug Options
```bash
# 最大詳細出力
printcad model.stl --verbose --debug

# ログファイル出力
printcad model.stl --log-file debug.log --log-level DEBUG
```

## 関連コマンド / Related Commands

### Webインターフェース / Web Interface
```bash
# Webサーバー起動
python run_server.py --host 0.0.0.0 --port 5000

# ブラウザアクセス
# http://localhost:5000
```

### 開発ツール / Development Tools
```bash
# テスト実行
make test

# 品質チェック
make lint

# ベンチマーク
make benchmark
```

## キーボードショートカット / Keyboard Shortcuts

タブ補完が利用可能なシェルでは以下のショートカットが使用可能：

- **Tab**: オプション補完
- **Ctrl+R**: コマンド履歴検索
- **↑/↓**: コマンド履歴ナビゲーション

## ヘルプ / Help

```bash
# 全オプション表示
printcad --help

# 特定のオプション詳細
printcad --help | grep "特定のオプション"

# バージョン情報
printcad --version
```

---

**クイックリファレンス - 効率的な3Dプリント検証のために**

**Quick Reference - For efficient 3D print validation**
