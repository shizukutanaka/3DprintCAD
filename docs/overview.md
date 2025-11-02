# Overview / 概要

## Purpose / 目的
This document introduces the 3D print CAD assistant MVP. It explains how the software assists operators from model validation to post-print review.

本ドキュメントは3DプリントCADアシスタントMVPの概要を紹介し、モデル検証から造形後のレビューまで使用者を支援する仕組みを説明します。

## Target users / 想定利用者
- Individual owners of desktop 3D printers.
- Small engineering teams conducting rapid prototyping.
- Internal engineers who need consistent print quality without advanced CAD expertise.

- デスクトップ3Dプリンタを所有する個人利用者。
- ラピッドプロトタイピングを行う小規模エンジニアリングチーム。
- 高度なCAD知識がなくても一定品質の造形を求める社内エンジニア。

## MVP capabilities / MVP機能
- Automated geometry checks (dimensions, wall thickness, support estimation).
- Detection of undersized features, self-intersections, thin tips, floating shells, high-aspect triangles, and unsupported overhangs with quantitative metrics.
- Sharp internal corner detection with stress risk indicators.
- Surface roughness proxy evaluation to highlight finishing concerns.
- Bed adhesion area estimation for build plate reliability.
- Auto-orientation suggestions balancing support reduction and bed contact.
- OBJ material validation to preserve assigned surface properties.
- Flatness analysis for critical mating faces.
- Targeted repair guidance summarizing high-risk findings.
- Center-of-gravity reporting to support build plate placement and fixturing decisions.
- Material presets with suggested print settings (temperature, layer height, speed).
- Post-print reporting for recording results, defects, and improvement proposals.

- 自動ジオメトリチェック（寸法、肉厚、サポート推定）。
- 定量指標に基づく微小フィーチャ、自己交差、細い突起、浮遊シェル、高アスペクト三角形、オーバーハングの検出。
- 応力集中リスクを伴う鋭い内角を検出。
- 仕上げ品質に影響する表面粗さ指標を算出。
- 造形プレートへの接地面積を推定し、密着性を評価。
- サポート量と接地面積を考慮した自動向き提案。
- OBJマテリアル設定を検証し、表面特性を保持。
- 重要な嵌合面の平面度を分析。
- 高リスク課題に対する修復ガイダンスを提示。
- 重心位置をレポートし、造形プレート配置や固定の判断を支援。
- 材料プリセットに基づく推奨造形条件（温度、層厚、造形速度）。
- 造形結果記録、欠陥ログ、改善案提示を含む造形レポート機能。

## Workflow / ワークフロー
1. Import model files (`STL`, `OBJ`) and run geometry validation.
2. Select a material preset to obtain recommended printer parameters.
3. Execute print and log print outcomes through the reporting module.
4. Review generated recommendations to iterate on design and settings.

1. モデルファイル（`STL`、`OBJ`）を取り込み、ジオメトリ検証を実行します。
2. 材料プリセットを選択し、推奨プリンタ設定を取得します。
3. 造形を実施し、レポートモジュールで造形結果を記録します。
4. 自動提案された改善内容を確認し、設計や設定を改善します。

## Command-line usage / コマンドライン利用
```
python -m src.cli path/to/model.stl --output report.json
python -m src.cli path/to/folder --list-files
python -m src.cli path/to/model.stl --no-progress
python -m src.cli --list-formats
python -m src.cli path/to/model.3mf
```

The commands above highlight the common workflows. Detailed argument descriptions are maintained centrally in `README.md` to avoid duplication. Refer to `README.md#command-line-usage` for the full option matrix, including threshold tuning (`--min-wall`, `--min-feature`, `--overhang-angle`), sorted file listing with `--list-files`, and quiet automation using `--no-progress`.

上記コマンドは主要な利用例を示しています。詳細な引数説明は重複を避けるため `README.md#command-line-usage` に集約しています。閾値調整（`--min-wall`、`--min-feature`、`--overhang-angle`）、`--list-files` によるソート済みファイル一覧、`--no-progress` を用いた静かな自動実行、`--list-formats` による対応拡張子確認、対応外拡張子を検出した際の二言語警告、3MF/AMF を含む最新フォーマット対応などの完全なオプション一覧は README を参照してください。

## Testing / テスト
Install development dependencies and execute the unit tests with `pytest`.

```
pip install pytest trimesh numpy
pytest
```

開発用依存関係を導入後、`pytest`でユニットテストを実行します。

```
pip install pytest trimesh numpy
pytest
```

## Extensibility / 拡張性
The architecture splits analysis, recommendation, and reporting into independent modules under `src/core/`. Adapters manage I/O formats, enabling future GUI or API frontends without core modifications.

アーキテクチャは`src/core/`配下で解析・推奨・レポートを独立モジュールに分割します。入出力はアダプタ層で管理し、コア処理を変更せずに将来のGUIやAPIフロントエンドを追加できます。

## Next steps / 今後の展開
- Build command-line tooling for running checks and reports.
- Expand material database and machine profiles.
- Integrate simulation-based validation for stress and temperature tolerances.

- チェックおよびレポートを実行できるコマンドラインツールを構築します。
- 材料データベースおよび機体プロファイルを拡充します。
- 応力や温度耐性を考慮したシミュレーション検証を統合します。
