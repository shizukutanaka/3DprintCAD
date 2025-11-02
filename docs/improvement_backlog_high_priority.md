# High-Priority Improvement Backlog / 優先改善バックログ

## Summary / 概要
- **[IMP-000]** Completed fix: `_configure_hash_manifest()` now validates manifest paths without redefining `_apply_language_mode`, ensuring stable bilingual output handling. / `_configure_hash_manifest()` が `_apply_language_mode` を再定義せずマニフェストパスを検証するよう修正し、二言語出力の安定性を確保しました。

## Security Hardening / セキュリティ強化
- **[IMP-001]** Enforce mandatory SHA-256 checksum validation before mesh parsing (Improvement Plan #1). Status: Planned. / メッシュ解析前にSHA-256チェックサム検証を必須化（改善計画項目#1）。状態：計画中。
- **[IMP-002]** Harden CLI argument handling against mixed encodings (Improvement Plan #31). Status: Planned. / 混在エンコーディングを拒否するCLI引数強化（改善計画項目#31）。状態：計画中。

## Reliability & Resilience / 信頼性・レジリエンス
- **[IMP-003]** Implement automatic fallback to sequential processing when parallel mode fails (Improvement Plan #205). Status: Planned. / 並列モード失敗時に逐次処理へ自動切替（改善計画項目#205）。状態：計画中。
- **[IMP-004]** Add watchdog timers to terminate hung mesh processing tasks safely (Improvement Plan #202). Status: Planned. / ハングしたメッシュ処理タスクを安全に終了するウォッチドッグタイマー追加（改善計画項目#202）。状態：計画中。

## Performance Optimization / 性能最適化
- **[IMP-005]** Introduce parallel file hashing to accelerate batch integrity verification (Improvement Plan #150). Status: Planned. / バッチ完全性確認を高速化する並列ファイルハッシュ導入（改善計画項目#150）。状態：計画中。
