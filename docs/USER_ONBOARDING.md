# ユーザーオンボーディングガイド / User Onboarding Guide

## ようこそ / Welcome

3DプリントCADアシスタントへようこそ。本ガイドでは、初めての方でもすぐに使い始められるよう、ステップバイステップで説明します。

Welcome to 3D Print CAD Assistant. This guide will help you get started quickly, even if you're new to 3D printing or CAD validation.

---

## クイックスタート / Quick Start

### 5分で始める / Get Started in 5 Minutes

1. **インストール / Install**
   ```bash
   pip install printcad
   ```

2. **モデル検証 / Validate a Model**
   ```bash
   printcad your-model.stl
   ```

3. **結果確認 / Check Results**
   - コンソールに検証結果が表示されます
   - 問題点と改善提案を確認してください

---

## インストール方法 / Installation Methods

### 方法1: PyPIからインストール (推奨) / Method 1: Install from PyPI (Recommended)

```bash
# 基本インストール
pip install printcad

# 追加機能付きインストール
pip install printcad[full]
```

### 方法2: ソースからインストール / Method 2: Install from Source

```bash
# リポジトリをクローン
git clone <repository-url>
cd 3DprintCAD

# 仮想環境作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# インストール
pip install -e .
```

### 方法3: Docker使用 / Method 3: Using Docker

```bash
# Dockerイメージ取得
docker pull printcad/assistant

# 実行
docker run -v $(pwd):/data printcad/assistant model.stl
```

---

## 基本的な使い方 / Basic Usage

### 単一ファイル検証 / Single File Validation

```bash
# STLファイル検証
printcad model.stl

# 詳細出力
printcad model.stl --summary

# JSONレポート出力
printcad model.stl --output report.json
```

### バッチ処理 / Batch Processing

```bash
# 複数ファイル処理
printcad file1.stl file2.obj file3.3mf

# ディレクトリ内全ファイル処理
printcad --input-dir ./models/

# パターン指定
printcad --pattern "models/*.stl"
```

### 並列処理 / Parallel Processing

```bash
# 並列処理で高速化
printcad --batch "models/*.stl" --parallel --max-workers 4
```

---

## 出力形式 / Output Formats

### コンソール出力 / Console Output

デフォルトでは、問題の深刻度に応じて色分けされた出力が表示されます：

- 🔴 **エラー (Errors)**: 印刷を妨げる重大な問題
- 🟡 **警告 (Warnings)**: 品質に影響する可能性のある問題
- ℹ️ **情報 (Info)**: 推奨事項と提案

### JSONレポート / JSON Reports

```bash
printcad model.stl --output report.json
```

JSONレポートには以下の情報が含まれます：
- メッシュ統計情報
- 検出された問題点
- 改善提案
- 処理時間
- リスクスコア

### HTMLレポート / HTML Reports

```bash
printcad model.stl --output report.html
```

ブラウザで閲覧可能な詳細レポートを生成します。

---

## 問題の理解 / Understanding Issues

### 一般的な問題タイプ / Common Issue Types

#### 1. 幾何学的な問題 / Geometric Issues
- **非多様体エッジ**: メッシュの接続不良
- **自己交差**: 面が互いに貫通している
- **穴**: メッシュの欠損部分

#### 2. 寸法的な問題 / Dimensional Issues
- **薄い壁**: 印刷強度が不足する可能性
- **小さな特徴**: ノズルでは印刷できない細部
- **オーバーハング**: サポートが必要な突出部分

#### 3. 表面品質の問題 / Surface Quality Issues
- **アスペクト比**: 細長い三角形による品質低下
- **表面粗さ**: 滑らかな表面が得られない

#### 4. 印刷適性の問題 / Printability Issues
- **ベッド密着**: 印刷物がベッドから剥がれるリスク
- **スケール**: ビルド容積に収まらないサイズ

### リスクスコアの解釈 / Understanding Risk Scores

- **0.0-0.3**: 低リスク - ほとんどの場合問題なく印刷可能
- **0.3-0.7**: 中リスク - 設定調整を推奨
- **0.7-1.0**: 高リスク - 設計変更を検討

---

## 設定のカスタマイズ / Configuration Customization

### 設定ファイル / Configuration Files

1. **グローバル設定 / Global Configuration**
   ```yaml
   # config/production.yaml
   validation:
     min_wall_thickness: 0.8
     min_feature_size: 0.4
   ```

2. **環境変数 / Environment Variables**
   ```bash
   export MIN_WALL_THICKNESS=1.0
   export MIN_FEATURE_SIZE=0.5
   ```

### プリンタープロファイル / Printer Profiles

```yaml
# config/printers/my_printer.yaml
printer:
  name: "My Ender 3"
  build_volume_x: 220
  build_volume_y: 220
  build_volume_z: 250
  nozzle_diameter: 0.4
```

---

## 高度な機能 / Advanced Features

### 修復機能 / Repair Features

```bash
# 自動修復
printcad model.stl --repair --save-repaired fixed_model.stl

# 積極的な修復
printcad model.stl --aggressive-repair
```

### G-code生成 / G-code Generation

```bash
# スライスとG-code生成
printcad model.stl --slice --gcode --output model.gcode
```

### 推奨機能 / Recommendation Engine

```bash
# 印刷設定の推奨
printcad model.stl --recommendations

# 詳細な推奨レポート
printcad model.stl --recommendations --output recommendations.json
```

---

## Webインターフェース / Web Interface

### 起動方法 / Starting the Web Interface

```bash
# Webサーバー起動
python run_server.py

# ブラウザでアクセス
# http://localhost:5000
```

### Webインターフェースの機能 / Web Interface Features

- **ファイルアップロード**: ドラッグ&ドロップでファイルをアップロード
- **3Dビューア**: モデルをインタラクティブに表示
- **リアルタイム検証**: アップロード時に即時検証
- **レポート閲覧**: 詳細な検証レポートを表示

---

## トラブルシューティング / Troubleshooting

### 一般的な問題と解決法 / Common Issues and Solutions

#### ファイルが読み込めない / Cannot Load File
```
エラー: File not found or unsupported format
解決: ファイルパスを確認し、サポートされている形式（STL, OBJ, PLY, 3MF, AMF）を使用してください
```

#### メモリ不足 / Out of Memory
```
エラー: MemoryError
解決: 大きなファイルを小さなチャンクに分割するか、より多くのRAMを搭載したマシンを使用してください
```

#### 検証が遅い / Validation is Slow
```
解決: --parallel オプションを使用するか、--max-workers を増やしてください
```

#### 予期しない結果 / Unexpected Results
```
解決: --verbose オプションで詳細なログを確認してください
```

### ログの確認 / Checking Logs

```bash
# 詳細ログ出力
printcad model.stl --verbose

# ログファイル指定
printcad model.stl --log-file debug.log
```

---

## 次のステップ / Next Steps

### 学習リソース / Learning Resources

1. **[ユーザーマニュアル](USER_GUIDE.md)**: 詳細な使用方法
2. **[APIリファレンス](API.md)**: プログラムからの利用方法
3. **[FAQ](FAQ.md)**: よくある質問

### 高度なトピック / Advanced Topics

- **CI/CD統合**: 自動検証パイプラインの構築
- **カスタムプラグイン**: 独自の検証ルールの開発
- **バッチ処理の最適化**: 大規模処理の効率化

### サポート / Support

- **ドキュメント**: 詳細な技術文書
- **コミュニティ**: フォーラムやディスカッション
- **プロフェッショナルサービス**: エンタープライズ向けサポート

---

## 用語集 / Glossary

- **メッシュ (Mesh)**: 3Dモデルの表面を構成する三角形の集合
- **マニホールド (Manifold)**: 閉じた連続的な表面（穴や隙間がない）
- **オーバーハング (Overhang)**: 空中に浮いた部分（サポートが必要）
- **インフィル (Infill)**: モデルの内部構造
- **G-code**: 3Dプリンターの制御命令

---

**3DプリントCADアシスタントで、より良い印刷物を！**

**Create better prints with 3D Print CAD Assistant!**
