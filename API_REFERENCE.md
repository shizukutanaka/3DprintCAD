# 3D Print CAD Assistant - APIリファレンス

## 概要

3D Print CAD Assistantは、RESTful APIを提供し、他のソフトウェアやシステムとの連携を可能にします。このAPIは、3Dモデルの検証、最適化、印刷準備をプログラム的に実行するための機能を提供します。

## APIエンドポイント

### ベースURL
```
http://localhost:5000/api/v1
```

### 認証
現在、APIは認証なしで利用可能です。セキュリティ要件に応じて、認証システムを追加できます。

## エンドポイント一覧

### 1. モデル検証

#### POST /validate

3Dモデルを検証します。

**リクエストボディ**
```json
{
  "file": "base64_encoded_stl_data",
  "filename": "model.stl",
  "validation_settings": {
    "min_wall_thickness_mm": 0.8,
    "min_feature_size_mm": 0.4,
    "support_overhang_angle_deg": 60
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "validation_results": {
    "is_watertight": true,
    "is_manifold": true,
    "issues": [
      {
        "code": "THIN_WALL",
        "severity": "warning",
        "message": "Thin wall detected",
        "location": [10.5, 20.3, 15.7]
      }
    ],
    "mesh_info": {
      "vertices": 15420,
      "faces": 30840,
      "volume": 125.67,
      "surface_area": 234.56
    }
  }
}
```

### 2. モデル修復

#### POST /repair

3Dモデルを修復します。

**リクエストボディ**
```json
{
  "file": "base64_encoded_stl_data",
  "filename": "model.stl",
  "repair_settings": {
    "aggressive_repair": false,
    "fill_holes": true,
    "fix_normals": true
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "repaired_file": "base64_encoded_repaired_stl_data",
  "repair_summary": {
    "operations_performed": ["hole_filling", "normal_fixing"],
    "issues_fixed": 3,
    "remaining_issues": 0
  }
}
```

### 3. スライス処理

#### POST /slice

モデルをスライスします。

**リクエストボディ**
```json
{
  "file": "base64_encoded_stl_data",
  "filename": "model.stl",
  "slice_settings": {
    "layer_height": 0.2,
    "infill_density": 20,
    "print_speed": 60,
    "nozzle_temperature": 210,
    "bed_temperature": 60
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "slice_results": {
    "total_layers": 150,
    "print_time_seconds": 7200,
    "material_grams": 45.67,
    "layer_data": [
      {
        "layer_number": 1,
        "z_height": 0.2,
        "perimeter_length": 45.23,
        "infill_length": 12.34
      }
    ]
  }
}
```

### 4. Gコード生成

#### POST /gcode

Gコードを生成します。

**リクエストボディ**
```json
{
  "file": "base64_encoded_stl_data",
  "filename": "model.stl",
  "gcode_settings": {
    "printer_profile": "prusa_i3_mk3",
    "nozzle_temperature": 210,
    "bed_temperature": 60,
    "print_speed": 60,
    "layer_height": 0.2
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "gcode": "G28\nG1 Z5 F5000\n; Generated G-code content...",
  "estimated_print_time": "2h 30m",
  "material_usage": "45.67g"
}
```

### 5. バッチ処理

#### POST /batch

複数のモデルを一括処理します。

**リクエストボディ**
```json
{
  "files": [
    {
      "data": "base64_encoded_stl_data_1",
      "filename": "model1.stl"
    },
    {
      "data": "base64_encoded_stl_data_2",
      "filename": "model2.stl"
    }
  ],
  "operations": ["validate", "repair", "slice"],
  "settings": {
    "parallel": true,
    "max_workers": 4
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "results": [
    {
      "filename": "model1.stl",
      "status": "completed",
      "validation_results": {...},
      "repair_results": {...}
    },
    {
      "filename": "model2.stl",
      "status": "completed",
      "validation_results": {...}
    }
  ],
  "summary": {
    "total_files": 2,
    "successful": 2,
    "failed": 0,
    "total_processing_time": 45.67
  }
}
```

## エラーレスポンス

すべてのエンドポイントで、エラー時は以下の形式でレスポンスを返します：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Model validation failed",
    "details": "Detailed error description"
  }
}
```

### エラーコード一覧

| コード | 説明 |
|--------|------|
| FILE_NOT_FOUND | 指定されたファイルが見つかりません |
| INVALID_FORMAT | サポートされていないファイル形式です |
| VALIDATION_FAILED | 検証処理でエラーが発生しました |
| REPAIR_FAILED | 修復処理でエラーが発生しました |
| SLICE_FAILED | スライス処理でエラーが発生しました |
| GCODE_FAILED | Gコード生成でエラーが発生しました |
| BATCH_FAILED | バッチ処理でエラーが発生しました |

## 使用例

### Pythonでの利用例

```python
import requests
import json

# モデル検証の例
with open('model.stl', 'rb') as f:
    stl_data = f.read()

response = requests.post('http://localhost:5000/api/v1/validate',
    json={
        'file': stl_data.decode('latin-1'),  # base64エンコードが必要な場合
        'filename': 'model.stl'
    }
)

if response.status_code == 200:
    result = response.json()
    if result['success']:
        print("検証結果:", result['validation_results'])
    else:
        print("エラー:", result['error'])
```

### JavaScriptでの利用例

```javascript
// モデル修復の例
async function repairModel(stlFile) {
  const formData = new FormData();
  formData.append('file', stlFile);

  const response = await fetch('/api/v1/repair', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();
  if (result.success) {
    // 修復されたファイルをダウンロード
    downloadFile(result.repaired_file, 'repaired_model.stl');
  } else {
    console.error('修復エラー:', result.error);
  }
}
```

## レート制限

デフォルトでは、以下のレート制限が適用されます：

- 1分あたり最大100リクエスト
- 1時間あたり最大1000リクエスト

レート制限を超えると、HTTP 429 (Too Many Requests)レスポンスを返します。

## レスポンス形式

### 成功レスポンス
```json
{
  "success": true,
  "data": {
    // レスポンスデータ
  },
  "metadata": {
    "processing_time": 1.23,
    "api_version": "1.0.0"
  }
}
```

### エラーレスポンス
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": "Additional error details"
  },
  "metadata": {
    "timestamp": "2025-01-01T12:00:00Z"
  }
}
```

## データ形式

### ファイルアップロード
ファイルは以下のいずれかの方法で送信できます：

1. **Base64エンコード**: JSONリクエストボディに含める場合
2. **マルチパートフォーム**: フォームデータとして送信する場合

### レスポンスデータサイズ
レスポンスデータのサイズは以下の制限があります：

- 検証結果: 最大1MB
- 修復データ: 最大50MB
- スライスデータ: 最大10MB
- Gコード: 最大5MB

## ベストプラクティス

1. **エラーハンドリング**: すべてのAPIコールでエラーレスポンスを適切に処理してください。
2. **レート制限**: 連続したリクエストの間に適切な間隔を置いてください。
3. **データサイズ**: 大きなファイルを処理する場合は、分割処理を検討してください。
4. **タイムアウト**: 長時間かかる処理には適切なタイムアウトを設定してください。

## バージョン情報

現在のAPIバージョン: v1.0.0

変更履歴はCHANGELOG.mdファイルをご覧ください。

---

このAPIリファレンスは、開発者が3D Print CAD Assistantをシステムに統合する際に必要な情報を提供します。追加の機能が必要な場合は、開発チームまでお問い合わせください。
