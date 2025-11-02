# データ保持方針 / Data Retention Policy

## 概要 / Overview

本プロジェクトにおけるデータの収集、保存、削除に関する方針を定義します。法的要件、セキュリティ、プライバシーを考慮した適切なデータ管理を実現します。

This document defines policies for data collection, storage, and deletion in this project. It ensures appropriate data management considering legal requirements, security, and privacy.

---

## 1. 方針の目的 / Purpose of Policy

### 目標 / Goals
- 法的・規制要件の遵守
- プライバシー保護
- ストレージコストの最適化
- データセキュリティの確保

### 適用範囲 / Scope
- ユーザー提供データ（3Dモデルファイル）
- システム生成データ（ログ、レポート、分析結果）
- 運用データ（監査ログ、監視データ）
- バックアップデータ

---

## 2. データ分類 / Data Classification

### 機密レベル定義 / Confidentiality Levels

#### レベル1: 公開データ / Public Data
```
説明: 一般に公開可能なデータ
例: 公開ドキュメント、READMEファイル
保持期間: 無期限
保管場所: 公開リポジトリ
```

#### レベル2: 内部データ / Internal Data
```
説明: 内部業務で使用するデータ
例: 開発ドキュメント、テストデータ
保持期間: 7年（税務・法的要件）
保管場所: 内部ストレージ
```

#### レベル3: 機密データ / Confidential Data
```
説明: 制限されたアクセスが必要なデータ
例: ユーザー個人情報、セキュリティログ
保持期間: 3年（プライバシー規制）
保管場所: 暗号化ストレージ
```

#### レベル4: 極秘データ / Highly Sensitive Data
```
説明: 厳格な保護が必要なデータ
例: 暗号鍵、認証情報、医療データ
保持期間: 1年（セキュリティ要件）
保管場所: HSM（Hardware Security Module）
```

---

## 3. データタイプ別保持期間 / Retention Periods by Data Type

### ユーザー提供データ / User-Provided Data

#### 3Dモデルファイル / 3D Model Files
```
保持期間: プロジェクト完了後30日
理由: 法的監査要件と品質保証
例外: アクティブプロジェクトは無期限保持
削除方法: 安全削除（複数回上書き）
```

#### アップロードメタデータ / Upload Metadata
```
保持期間: 3年
理由: 監査証跡と法的要件
例外: セキュリティインシデント時は7年保持
削除方法: データベースからの論理削除
```

### システム生成データ / System-Generated Data

#### 処理ログ / Processing Logs
```
保持期間: 1年
理由: トラブルシューティングと性能分析
例外: エラー関連ログは3年保持
削除方法: ログローテーションと圧縮
```

#### 分析レポート / Analysis Reports
```
保持期間: プロジェクト完了後1年
理由: 品質管理と改善分析
例外: 法的調査時は7年保持
削除方法: 自動削除スクリプト
```

#### パフォーマンスメトリクス / Performance Metrics
```
保持期間: 2年
理由: トレンド分析と容量計画
例外: なし
削除方法: 時系列データベースでの自動削除
```

### 運用データ / Operational Data

#### 監査ログ / Audit Logs
```
保持期間: 7年
理由: SOX、GDPR等の規制遵守
例外: 金融データ関連は10年保持
削除方法: WORM（Write Once Read Many）ストレージ
```

#### バックアップデータ / Backup Data
```
保持期間: 30日（日次バックアップ）
         1年（週次バックアップ）
         7年（月次バックアップ）
理由: 災害復旧と規制遵守
例外: なし
削除方法: 暗号化されたバックアップからの削除
```

#### セキュリティイベントログ / Security Event Logs
```
保持期間: 3年
理由: セキュリティ監査とインシデント調査
例外: 重大インシデント時は無期限保持
削除方法: セキュリティ情報イベント管理（SIEM）システム
```

### 一時データ / Temporary Data

#### セッションデータ / Session Data
```
保持期間: セッション終了時まで（最大24時間）
理由: ユーザーエクスペリエンス維持
例外: なし
削除方法: Redis TTL設定
```

#### キャッシュデータ / Cache Data
```
保持期間: 最大7日
理由: パフォーマンス最適化
例外: なし
削除方法: LRU（Least Recently Used）アルゴリズム
```

---

## 4. データ保持の法的根拠 / Legal Basis for Data Retention

### 規制遵守 / Regulatory Compliance

#### GDPR (EU一般データ保護規則) / GDPR
```
個人データ保持: 必要最小限の期間
データ主体の権利: 削除請求への対応
記録保持: 法的義務がある場合
```

#### SOX (Sarbanes-Oxley Act)
```
財務記録: 7年保持
監査証跡: 変更履歴の完全保持
内部統制: システムログの保持
```

#### ISO 27001
```
情報セキュリティ: リスクベースの保持期間
アクセス制御: ログの保持と監視
インシデント対応: 証拠データの保持
```

### 業界固有要件 / Industry-Specific Requirements

#### 製造業 / Manufacturing
```
製品データ: 製品ライフサイクル＋5年
品質記録: ISO 9001準拠期間
変更管理: 設計変更履歴
```

#### 医療機器 / Medical Devices
```
患者データ: HIPAA準拠期間
機器トレーサビリティ: 機器寿命＋10年
検証記録: 規制当局要求期間
```

---

## 5. データ削除手順 / Data Deletion Procedures

### 自動削除 / Automatic Deletion

#### スクリプトベース削除 / Script-Based Deletion
```bash
# 日次削除スクリプト実行例
#!/bin/bash
# 30日以上前のログを削除
find /var/log/printcad -name "*.log" -mtime +30 -delete

# 古いバックアップを削除
find /backup/printcad -name "*.tar.gz" -mtime +365 -delete
```

#### データベース自動削除 / Database Auto-Deletion
```sql
-- PostgreSQLでの自動削除設定例
CREATE OR REPLACE FUNCTION cleanup_old_data() RETURNS void AS $$
BEGIN
    -- 30日以上前のセッションデータを削除
    DELETE FROM user_sessions WHERE created_at < NOW() - INTERVAL '30 days';

    -- 1年以上前の分析レポートを削除
    DELETE FROM analysis_reports WHERE created_at < NOW() - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;
```

### 手動削除 / Manual Deletion

#### 安全削除プロセス / Secure Deletion Process
1. **データ特定**: 削除対象データの特定
2. **バックアップ**: 必要な場合はバックアップ作成
3. **削除実行**: 安全削除ツールを使用
4. **検証**: 削除完了の確認
5. **記録**: 削除操作のログ記録

#### 安全削除ツール / Secure Deletion Tools
```bash
# Linuxでの安全削除
shred -u -v -n 3 file_to_delete  # 3回上書きして削除

# Windowsでの安全削除
cipher /w:C:\path\to\folder     # 空き領域の安全消去

# データベースでの安全削除
DELETE FROM sensitive_table WHERE retention_period_expired = true;
-- 監査ログに削除記録
INSERT INTO audit_log (action, table_name, record_count) VALUES ('DELETE', 'sensitive_table', affected_rows);
```

---

## 6. データアクセスと監査 / Data Access and Auditing

### アクセス制御 / Access Controls

#### ロールベースアクセス / Role-Based Access Control
```
管理者: 全データアクセス可能
開発者: 開発関連データのみアクセス可能
監査人: 読み取り専用アクセス
ユーザー: 自身のデータのみアクセス可能
```

#### 最小権限の原則 / Principle of Least Privilege
- 必要なデータのみアクセス可能
- 必要な期間のみアクセス可能
- 監査ログによるアクセス追跡

### 監査手順 / Auditing Procedures

#### 定期監査 / Regular Audits
- **月次**: データ保持遵守状況の確認
- **四半期**: アクセス権限の見直し
- **年次**: 包括的なデータ管理監査

#### 監査ログ内容 / Audit Log Contents
```
- アクセス日時
- アクセスユーザー
- アクセスデータ
- 操作タイプ（読み取り/書き込み/削除）
- IPアドレスとユーザーエージェント
- 成功/失敗ステータス
```

---

## 7. 例外処理 / Exception Handling

### 保持期間延長 / Retention Period Extensions

#### 法的要請 / Legal Requests
```
裁判所命令、規制当局要求の場合、保持期間を無期限に延長
理由: 法的義務の履行
プロセス: 法務部門の承認を得て延長
```

#### セキュリティインシデント / Security Incidents
```
インシデント調査のために、関連データを無期限保持
理由: 根本原因分析と再発防止
プロセス: セキュリティチームの判断で延長
```

#### ビジネス継続 / Business Continuity
```
システム移行や統合のために、一時的に保持期間を延長
理由: 業務継続性の確保
プロセス: プロジェクトマネージャーの承認
```

### 早期削除 / Early Deletion

#### データ主体の権利 / Data Subject Rights
```
GDPRに基づく削除請求への対応
理由: 個人のプライバシー権利
プロセス: 検証後に即時削除
```

#### セキュリティリスク / Security Risks
```
データ侵害リスクがある場合、早期削除を検討
理由: リスク低減
プロセス: セキュリティチームの評価
```

---

## 8. 技術的実装 / Technical Implementation

### データライフサイクル管理 / Data Lifecycle Management

#### タグ付けシステム / Tagging System
```python
@dataclass
class DataMetadata:
    created_at: datetime
    retention_period_days: int
    confidentiality_level: int
    legal_hold: bool = False
    auto_delete: bool = True
```

#### 自動分類 / Automatic Classification
```python
def classify_data(file_path: Path) -> DataClassification:
    """ファイルパスに基づいてデータを自動分類"""
    if 'medical' in str(file_path).lower():
        return DataClassification.HIGHLY_SENSITIVE
    elif 'user' in str(file_path).lower():
        return DataClassification.CONFIDENTIAL
    else:
        return DataClassification.INTERNAL
```

### ストレージ階層化 / Storage Tiering

#### ホットストレージ / Hot Storage
```
- 使用頻度の高いデータ
- 高速アクセスが必要
- 高可用性
- 高コスト
```

#### コールドストレージ / Cold Storage
```
- 長期保存データ
- 低頻度アクセス
- 低コスト
- 高耐久性
```

#### アーカイブストレージ / Archive Storage
```
- 法的保持データ
- 非常に低頻度アクセス
- 最低コスト
- 最高耐久性
```

---

## 9. 監視と報告 / Monitoring and Reporting

### メトリクス監視 / Metrics Monitoring

#### 保持遵守メトリクス / Retention Compliance Metrics
- データ削除率
- 保持期間遵守率
- ストレージ使用量
- 削除エラー率

#### アラート設定 / Alert Configuration
```yaml
# 保持ポリシー違反アラート
retention_violation_alert:
  condition: retention_days_exceeded > 0
  severity: high
  notification: security_team

# ストレージ使用量アラート
storage_usage_alert:
  condition: usage_percent > 85
  severity: medium
  notification: operations_team
```

### 報告プロセス / Reporting Process

#### 月次報告 / Monthly Reports
- データ保持遵守状況
- ストレージ使用量レポート
- 削除操作の要約
- コンプライアンス監査結果

#### 年次報告 / Annual Reports
- データ保持方針の見直し
- 規制変更への対応
- 技術的改善の検討

---

## 10. 方針の更新 / Policy Updates

### レビュープロセス / Review Process
- **年次レビュー**: 方針全体の見直し
- **変更トリガー**: 規制変更、技術革新、インシデント発生
- **承認プロセス**: 法務・セキュリティ・経営層の承認

### 変更管理 / Change Management
1. **変更提案**: 関係部門からの提案
2. **影響評価**: 変更による影響の評価
3. **承認取得**: 必要な承認の取得
4. **実施計画**: 変更の実施計画
5. **コミュニケーション**: 関係者への通知

---

## 11. 責任者と連絡先 / Responsibilities and Contacts

### データ保持責任者 / Data Retention Officer
```
名前: [担当者名]
役割: データ保持方針の実施と監視
連絡先: retention@company.com
バックアップ: [副担当者名]
```

### 関連部門 / Related Departments
```
- 法務部門: 法的要件の確認
- セキュリティ部門: セキュリティ要件の確認
- IT部門: 技術的実装
- コンプライアンス部門: 監査と報告
```

---

## 12. 参考資料 / References

### 関連ドキュメント / Related Documents
- [プライバシーポリシー](PRIVACY_POLICY.md)
- [セキュリティポリシー](SECURITY_POLICY.md)
- [バックアップ方針](BACKUP_POLICY.md)

### 外部リソース / External Resources
- [GDPR Data Retention Guidelines](https://gdpr.eu/data-retention/)
- [NIST Data Retention Practices](https://csrc.nist.gov/publications/detail/sp/800-88/rev-1/final)
- [ISO 27001 Data Retention Controls](https://www.iso.org/isoiec-27001-information-security.html)

---

**適切なデータ管理でコンプライアンスと効率を両立**

**Balance compliance and efficiency with appropriate data management**
