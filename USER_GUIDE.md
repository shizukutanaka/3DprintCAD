# 3D Print CAD Assistant - ユーザーマニュアル

## 概要

3D Print CAD Assistantは、3Dモデルの検証、最適化、印刷準備を支援するソフトウェアです。専門的な知識がなくても、簡単に高品質な3Dプリントモデルを作成できます。

## インストール

### システム要件
- Windows 10以上、macOS 11以上、またはUbuntu 20.04以上
- Python 3.9以上（3.11を推奨）
- 8GB以上のメモリ（大規模モデル処理時は16GB以上推奨）
- 2GB以上の空きディスク容量

### インストール手順
1. Pythonをインストールします。
2. コマンドプロンプトまたはターミナルで以下のコマンドを実行します：

```bash
# 仮想環境を作成
python -m venv printcad-env

# 仮想環境を有効化（Windows）
printcad-env\Scripts\activate

# 仮想環境を有効化（macOS/Linux）
source printcad-env/bin/activate

# 必要なパッケージをインストール
pip install -r requirements.txt

# ソフトウェアをインストール
pip install -e .
```

## 基本的な使い方

### コマンドラインインターフェース（CLI）

#### 単一ファイルの検証
```bash
printcad model.stl --validate --output result.json
```

#### 複数のファイルの一括処理
```bash
printcad --batch "models/*.stl" --parallel --output batch_results.json
```

#### 修復機能付きの処理
```bash
printcad model.stl --validate --repair --slice --gcode --output complete_result.json
```

### 利用可能なオプション

#### 基本オプション
- `--validate`: モデルを検証します（デフォルトで有効）
- `--repair`: 問題を自動修復します
- `--slice`: スライス設定でモデルを準備します
- `--gcode`: Gコードを生成します

#### 詳細設定
- `--min-wall 0.8`: 最小壁厚を設定（mm）
- `--min-feature 0.4`: 最小特徴サイズを設定（mm）
- `--layer-height 0.2`: レイヤー高さを設定（mm）
- `--infill 20`: インフィル密度を設定（%）

#### 出力オプション
- `--output result.json`: 結果をJSONファイルに保存
- `--summary`: 処理概要を表示
- `--verbose`: 詳細な情報を表示

## 検証機能

### 自動検証項目
ソフトウェアは以下の項目を自動的にチェックします：

1. **水密性**: モデルに穴がないか確認
2. **多様体性**: モデルが正しい形状か確認
3. **壁厚**: 印刷可能な厚さがあるか確認
4. **オーバーハング**: サポートが必要な角度か確認
5. **自己交差**: モデル内で干渉がないか確認

### 検証結果の見方
- **成功**: すべてのチェックに合格
- **警告**: 印刷は可能だが品質に影響する可能性
- **失敗**: 印刷が不可能または重大な問題

## 修復機能

### 自動修復可能な問題
- 小さな穴の充填
- 法線の修正
- 重複頂点の削除
- 軽度の自己交差の解決

### 修復の実行
```bash
printcad model.stl --repair --save-repaired fixed_model.stl
```

## 印刷準備

### スライス設定
ソフトウェアはモデルを印刷可能なレイヤーに変換します。

```bash
printcad model.stl --slice --layer-height 0.15 --infill 25
```

### Gコード生成
3Dプリンターで直接使用できるGコードを生成します。

```bash
printcad model.stl --gcode --temp-nozzle 200 --temp-bed 60
```

## 高度な機能

### バッチ処理
複数のモデルを一度に処理します。

```bash
printcad --batch "upload/*.stl" --parallel --max-workers 4
```

### カスタム設定
設定ファイルでデフォルト値を変更できます。

```yaml
# config.yaml
application:
  default_language_mode: "bilingual"

validation:
  min_wall_thickness_mm: 0.8
  min_feature_size_mm: 0.4
```

### 多言語対応
50言語に対応しています。言語は以下の方法で変更できます：

```bash
printcad model.stl --language ja  # 日本語
printcad model.stl --language es  # スペイン語
printcad model.stl --language de  # ドイツ語
```

## トラブルシューティング

### 一般的な問題と解決方法

#### ファイルが読み込めない
- ファイル形式がSTL、OBJ、PLYのいずれかであることを確認してください。
- ファイルサイズが大きすぎる場合は、`--max-file-size`オプションで制限を調整してください。

#### 検証で失敗する
- モデルに深刻な欠陥がある可能性があります。
- `--repair`オプションを追加して自動修復を試してください。

#### 印刷品質が悪い
- 壁厚や特徴サイズの設定を調整してください。
- オーバーハング角度を確認し、必要に応じてサポートを追加してください。

### エラーメッセージ一覧

| エラーコード | 説明 | 解決方法 |
|-------------|------|----------|
| FILE_NOT_FOUND | ファイルが見つかりません | ファイルパスを確認してください |
| INVALID_FORMAT | サポートされていないファイル形式です | STL、OBJ、PLY形式を使用してください |
| VALIDATION_FAILED | 検証に失敗しました | モデルを修復するか、再設計してください |

## 技術仕様

### 対応ファイル形式
- STL（Standard Triangle Language）
- OBJ（Wavefront OBJ）
- PLY（Stanford PLY）
- 3MF（3D Manufacturing Format）
- AMF（Additive Manufacturing File Format）

### 処理能力
- 最大ファイルサイズ: 500MB（設定で変更可能）
- 並列処理: CPUコア数に応じて自動調整
- 処理速度: モデルサイズにより変動（数秒〜数分）

### システム要件（詳細）
- CPU: 2コア以上（4コア以上推奨）
- メモリ: 8GB以上（16GB以上推奨）
- ディスク: SSD推奨（処理速度向上のため）

## サポートと連絡先

問題が発生した場合は、以下の情報を記載してサポートまでお問い合わせください：

1. 使用しているOSとバージョン
2. Pythonのバージョン
3. エラーメッセージの詳細
4. 使用したコマンドラインオプション
5. 処理対象のモデルファイル情報

## ライセンス

このソフトウェアはMITライセンスの下で提供されています。詳細はLICENSEファイルをご覧ください。

## 更新履歴

最新の更新情報はCHANGELOG.mdファイルをご覧ください。

---

このマニュアルはソフトウェアの使用を支援するためのものです。詳細な技術情報が必要な場合は、開発者ドキュメントを参照してください。
