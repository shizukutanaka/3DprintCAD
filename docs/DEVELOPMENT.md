# 開発環境構築ガイド / Development Setup Guide

## 概要 / Overview

本プロジェクトの開発環境を構築するための手順を説明します。Windows、macOS、Linuxに対応しています。

This guide explains how to set up the development environment for this project. It supports Windows, macOS, and Linux.

## 前提条件 / Prerequisites

### システム要件 / System Requirements
- **OS**: Windows 10+ / macOS 11+ / Ubuntu 20.04+
- **Python**: 3.9 以上（3.11 推奨）
- **メモリ**: 8 GB 以上
- **ストレージ**: 2 GB 以上

### 必要なツール / Required Tools
- **Python 3.9+**: [python.org](https://python.org) からダウンロード
- **Git**: [git-scm.com](https://git-scm.com) からダウンロード
- **Visual Studio Code** (推奨): [code.visualstudio.com](https://code.visualstudio.com)

## インストール手順 / Installation Steps

### 1. リポジトリのクローン / Clone Repository

```bash
git clone <repository-url>
cd 3DprintCAD
```

### 2. Python仮想環境の作成 / Create Python Virtual Environment

#### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

#### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 依存関係のインストール / Install Dependencies

```bash
# 開発用依存関係を含む完全インストール
pip install -e ".[dev,full]"

# または最小限のインストール後、開発ツールを追加
pip install -r requirements.txt
pip install -e .
pip install pytest mypy flake8 black isort
```

### 4. 開発ツールの設定 / Setup Development Tools

#### Pre-commitフックのインストール / Install Pre-commit Hooks
```bash
pre-commit install
```

#### 設定ファイルの確認 / Verify Configuration Files
- `pyproject.toml`: プロジェクト設定
- `Makefile`: 開発タスク
- `.pre-commit-config.yaml`: コード品質チェック

## 開発ワークフロー / Development Workflow

### コードの実行 / Running Code

#### CLIツールの実行 / Run CLI Tool
```bash
# ヘルプ表示
python -m src.cli --help

# サンプルファイルの検証（model.stlが存在する場合）
python -m src.cli model.stl

# Webアプリケーションの起動
python run_server.py
```

### テストの実行 / Running Tests

```bash
# 全テスト実行
make test

# カバレッジレポート付きテスト
make coverage

# 特定のテストファイル実行
pytest tests/test_specific.py -v
```

### コード品質チェック / Code Quality Checks

```bash
# リンター実行
make lint

# フォーマッター実行
make format

# 全チェック実行
make check
```

### パフォーマンスベンチマーク / Performance Benchmarking

```bash
# ベンチマーク実行
make benchmark

# 詳細なプロファイリング
python -c "
import cProfile
from src.core.analysis import mesh_validator
import trimesh
mesh = trimesh.creation.icosphere(subdivisions=4)
cProfile.run('mesh_validator.validate_mesh(mesh)')
"
```

## IDE設定 / IDE Configuration

### Visual Studio Code

#### 推奨拡張機能 / Recommended Extensions
- Python (Microsoft)
- Pylance
- Black Formatter
- isort
- Python Docstring Generator

#### settings.json設定例 / Example settings.json
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

## トラブルシューティング / Troubleshooting

### 一般的な問題 / Common Issues

#### 仮想環境が正しく動作しない / Virtual Environment Not Working
```bash
# 仮想環境再作成
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -e ".[dev,full]"
```

#### 依存関係の競合 / Dependency Conflicts
```bash
# キャッシュクリア
pip cache purge
pip install --force-reinstall -e ".[dev,full]"
```

#### メモリ不足 / Out of Memory
- 大規模モデル処理時はメモリを8GB以上に増設
- バッチ処理では `--max-workers` を減らす

### プラットフォーム固有の注意事項 / Platform-Specific Notes

#### Windows
- WSL2を使用するとLinux環境と同様の操作が可能
- パス区切り文字に注意（`/` を `\` に変更）

#### macOS
- Xcode Command Line Toolsが必要
```bash
xcode-select --install
```

#### Linux
- システムパッケージのインストール
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-dev build-essential
```

## 貢献ガイドライン / Contribution Guidelines

### コーディング標準 / Coding Standards
- **Black**: コードフォーマッター
- **isort**: import文整理
- **flake8**: リンター
- **mypy**: 型チェック

### コミット前チェック / Pre-commit Checks
```bash
# 全チェック実行
make check

# 問題なければコミット
git add .
git commit -m "適切なコミットメッセージ"
```

### プルリクエスト / Pull Requests
1. テストが通ることを確認
2. ドキュメントを更新
3. 変更内容を明確に記述
4. レビュアーのコメントに対応

## 追加リソース / Additional Resources

- [プロジェクト概要](overview.md)
- [APIリファレンス](API.md)
- [セキュリティガイド](SECURITY_HARDENING.md)
- [ユーザーマニュアル](USER_GUIDE.md)
