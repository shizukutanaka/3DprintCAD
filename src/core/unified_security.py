"""統合セキュリティマネージャー - 全てのセキュリティ機能を統合

このモジュールは、以下のセキュリティ機能を統合的に提供します：
- 基本的なセキュリティ機能 (security.py から)
- 高度なセキュリティ機能 (advanced_security.py から)
- ブロックチェーンセキュリティ (blockchain_security.py から)
- セキュリティスキャナー (security_scanner.py から)

重複を排除し、統一されたインターフェースを提供します。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from werkzeug.datastructures import FileStorage

import base64


class SecurityLevel(Enum):
    """セキュリティレベル"""
    BASIC = "basic"
    STANDARD = "standard"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"


class EncryptionAlgorithm(Enum):
    """暗号化アルゴリズム"""
    AES_256_GCM = "aes_256_gcm"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    KYBER = "kyber"  # 量子耐性
    DILITHIUM = "dilithium"  # 量子耐性


class ZeroTrustPolicy(Enum):
    """ゼロトラストポリシー"""
    DENY_BY_DEFAULT = "deny_by_default"
    LEAST_PRIVILEGE = "least_privilege"
    CONTINUOUS_VERIFICATION = "continuous_verification"
    MICRO_SEGMENTATION = "micro_segmentation"


@dataclass
class SecurityContext:
    """セキュリティコンテキスト"""
    user_id: str
    session_id: str
    device_fingerprint: str
    ip_address: str
    user_agent: str
    risk_score: float = 0.0
    security_level: str = SecurityLevel.STANDARD.value
    access_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AccessRequest:
    """アクセスリクエスト"""
    resource: str
    action: str
    context: SecurityContext
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SecurityEvent:
    """セキュリティイベント"""
    event_id: str
    timestamp: float
    event_type: str
    severity: str
    description: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityManagerBase(ABC):
    """セキュリティマネージャーの基底クラス"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def initialize(self) -> bool:
        """初期化"""
        pass

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """検証"""
        pass

    @abstractmethod
    def get_security_info(self) -> Dict[str, Any]:
        """セキュリティ情報を取得"""
        pass


class UnifiedSecurityManager(SecurityManagerBase):
    """統合セキュリティマネージャー"""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STANDARD):
        super().__init__()
        self.security_level = security_level
        self._initialized = False

        # コンポーネント
        self.crypto_manager: Optional[CryptographyManager] = None
        self.zero_trust_manager: Optional[ZeroTrustSecurityManager] = None
        self.threat_intelligence: Optional[ThreatIntelligenceManager] = None
        self.blockchain_security: Optional[BlockchainSecurityManager] = None
        self.security_scanner: Optional[SecurityScanner] = None

        # セキュリティ設定
        self.config = {
            'max_file_size_mb': 500,
            'allowed_extensions': {'.stl', '.obj', '.3mf', '.gcode'},
            'scan_for_malware': True,
            'require_integrity_check': True,
            'enable_quantum_resistance': security_level in [SecurityLevel.ADVANCED, SecurityLevel.ENTERPRISE],
            'enable_blockchain': security_level in [SecurityLevel.ENTERPRISE],
            'log_security_events': True,
            'risk_threshold': 0.7
        }

        # セキュリティイベント
        self.security_events: List[SecurityEvent] = []
        self.max_events = 10000

        # スレッドセーフティ
        self._lock = threading.RLock()

        # 初期化
        self.initialize()

    def initialize(self) -> bool:
        """セキュリティマネージャーを初期化"""
        try:
            with self._lock:
                # 基本コンポーネントの初期化
                self.crypto_manager = CryptographyManager(self.security_level)
                self.zero_trust_manager = ZeroTrustSecurityManager()
                self.threat_intelligence = ThreatIntelligenceManager()

                # レベルに応じた追加コンポーネント
                if self.config['enable_quantum_resistance']:
                    # 量子耐性暗号の初期化はcrypto_manager内で処理

                if self.config['enable_blockchain']:
                    self.blockchain_security = BlockchainSecurityManager()

                # セキュリティスキャナーの初期化
                self.security_scanner = SecurityScanner(str(Path(__file__).parent.parent.parent))

                self._initialized = True
                self.logger.info(f"セキュリティマネージャーを初期化しました (レベル: {self.security_level.value})")
                return True

        except Exception as e:
            self.logger.error(f"セキュリティマネージャーの初期化に失敗しました: {e}")
            return False

    def validate_file(self, file_path: Path, expected_hash: Optional[str] = None) -> Dict[str, Any]:
        """ファイルを包括的に検証"""
        if not self._initialized:
            raise RuntimeError("セキュリティマネージャーが初期化されていません")

        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'security_checks': {},
            'file_hash': None,
            'risk_score': 0.0
        }

        try:
            # 1. 基本ファイル検証
            basic_validation = self._validate_file_basic(file_path)
            result.update(basic_validation)

            # 2. 脅威インテリジェンスチェック
            if result['file_hash']:
                threat_check = self.threat_intelligence.check_for_known_threats(
                    result['file_hash'], str(file_path)
                )
                result['security_checks']['threat_intelligence'] = not threat_check

            # 3. ゼロトラスト検証
            trust_check = self.zero_trust_manager.verify_file_access(
                str(file_path), "read"
            )
            result['security_checks']['zero_trust'] = trust_check

            # 4. ブロックチェーン検証（有効な場合）
            if self.blockchain_security and result['file_hash']:
                blockchain_check = self.blockchain_security.verify_file_integrity(
                    result['file_hash'], str(file_path)
                )
                result['security_checks']['blockchain'] = blockchain_check

            # 5. セキュリティスキャン
            if self.security_scanner:
                scan_result = self.security_scanner.scan_file(str(file_path))
                result['security_checks']['vulnerability_scan'] = len(scan_result.vulnerabilities) == 0
                if scan_result.vulnerabilities:
                    result['warnings'].extend([v.description for v in scan_result.vulnerabilities])

            # 6. リスクスコア計算
            result['risk_score'] = self._calculate_risk_score(result)

            # 7. ログ記録
            self._log_security_event(
                SecurityEvent(
                    event_id=secrets.token_hex(8),
                    timestamp=time.time(),
                    event_type='file_validation',
                    severity='info' if result['valid'] else 'warning',
                    description=f"ファイル検証完了: {file_path.name}",
                    metadata={
                        'file_path': str(file_path),
                        'risk_score': result['risk_score'],
                        'validation_result': result['valid']
                    }
                )
            )

        except Exception as e:
            result['errors'].append(f"検証中にエラーが発生しました: {e}")
            result['valid'] = False

        return result

    def authorize_access(self, request: AccessRequest) -> Tuple[bool, str]:
        """アクセスを承認"""
        if not self._initialized:
            return False, "セキュリティマネージャーが初期化されていません"

        try:
            # ゼロトラスト評価
            authorized, reason = self.zero_trust_manager.evaluate_access_request(request)

            # ログ記録
            self._log_security_event(
                SecurityEvent(
                    event_id=secrets.token_hex(8),
                    timestamp=time.time(),
                    event_type='access_request',
                    severity='info' if authorized else 'warning',
                    description=f"アクセス要求: {request.resource} - {request.action}",
                    user_id=request.context.user_id,
                    session_id=request.context.session_id,
                    ip_address=request.context.ip_address,
                    metadata={'authorized': authorized, 'reason': reason}
                )
            )

            return authorized, reason

        except Exception as e:
            self.logger.error(f"アクセス承認中にエラーが発生しました: {e}")
            return False, f"承認処理でエラーが発生しました: {e}"

    def encrypt_data(self, data: str, context: str = "default") -> str:
        """データを暗号化"""
        if not self.crypto_manager:
            raise RuntimeError("暗号化マネージャーが初期化されていません")
        return self.crypto_manager.encrypt_sensitive_data(data, context)

    def decrypt_data(self, encrypted_data: str, context: str = "default") -> str:
        """データを復号化"""
        if not self.crypto_manager:
            raise RuntimeError("暗号化マネージャーが初期化されていません")
        return self.crypto_manager.decrypt_sensitive_data(encrypted_data, context)

    def get_security_dashboard(self) -> Dict[str, Any]:
        """セキュリティダッシュボードデータを取得"""
        if not self._initialized:
            return {'status': 'not_initialized'}

        dashboard_data = {
            'status': 'active',
            'security_level': self.security_level.value,
            'components_status': {},
            'recent_events': self._get_recent_events(10),
            'risk_summary': self._calculate_risk_summary(),
            'compliance_status': self._check_compliance_status()
        }

        # コンポーネントステータス
        dashboard_data['components_status'] = {
            'crypto_manager': self.crypto_manager is not None,
            'zero_trust': self.zero_trust_manager is not None,
            'threat_intelligence': self.threat_intelligence is not None,
            'blockchain_security': self.blockchain_security is not None,
            'security_scanner': self.security_scanner is not None
        }

        return dashboard_data

    def _validate_file_basic(self, file_path: Path) -> Dict[str, Any]:
        """基本的なファイル検証"""
        result = {'valid': True, 'errors': [], 'warnings': [], 'file_hash': None}

        try:
            # ファイル存在チェック
            if not file_path.exists():
                result['errors'].append(f"ファイルが存在しません: {file_path}")
                result['valid'] = False
                return result

            # ファイルサイズチェック
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config['max_file_size_mb']:
                result['errors'].append(
                    f"ファイルサイズ ({file_size_mb:.2f} MB) が制限 ({self.config['max_file_size_mb']} MB) を超えています"
                )
                result['valid'] = False

            # 拡張子チェック
            if file_path.suffix.lower() not in self.config['allowed_extensions']:
                result['warnings'].append(
                    f"サポートされていない拡張子: {file_path.suffix}"
                )

            # ハッシュ計算
            try:
                result['file_hash'] = self._calculate_file_hash(file_path)
            except Exception as e:
                result['warnings'].append(f"ハッシュ計算に失敗しました: {e}")

        except Exception as e:
            result['errors'].append(f"検証中にエラーが発生しました: {e}")
            result['valid'] = False

        return result

    def _calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """ファイルのハッシュを計算"""
        hash_func = getattr(hashlib, algorithm.lower())
        hash_obj = hash_func()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def _calculate_risk_score(self, validation_result: Dict[str, Any]) -> float:
        """リスクスコアを計算"""
        risk_score = 0.0

        # 検証エラーによるリスク
        risk_score += len(validation_result.get('errors', [])) * 0.3

        # 警告によるリスク
        risk_score += len(validation_result.get('warnings', [])) * 0.1

        # セキュリティチェックによるリスク
        security_checks = validation_result.get('security_checks', {})
        failed_checks = [check for check, passed in security_checks.items() if not passed]
        risk_score += len(failed_checks) * 0.2

        return min(risk_score, 1.0)

    def _get_recent_events(self, limit: int) -> List[Dict[str, Any]]:
        """最近のセキュリティイベントを取得"""
        with self._lock:
            recent_events = self.security_events[-limit:]
            return [
                {
                    'event_id': event.event_id,
                    'timestamp': event.timestamp,
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'description': event.description,
                    'user_id': event.user_id,
                    'ip_address': event.ip_address
                }
                for event in recent_events
            ]

    def _calculate_risk_summary(self) -> Dict[str, Any]:
        """リスクサマリーを計算"""
        events = self.security_events[-1000:]  # 最近1000件
        risk_levels = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}

        for event in events:
            if event.severity.lower() in risk_levels:
                risk_levels[event.severity.lower()] += 1

        total_events = sum(risk_levels.values())
        if total_events == 0:
            return {'overall_risk': 'low', 'distribution': risk_levels}

        # 全体リスクの計算
        risk_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        weighted_risk = sum(risk_weights.get(level, 1) * count for level, count in risk_levels.items())
        average_risk = weighted_risk / total_events

        if average_risk <= 1.5:
            overall_risk = 'low'
        elif average_risk <= 2.5:
            overall_risk = 'medium'
        elif average_risk <= 3.5:
            overall_risk = 'high'
        else:
            overall_risk = 'critical'

        return {
            'overall_risk': overall_risk,
            'average_risk': average_risk,
            'distribution': risk_levels,
            'total_events': total_events
        }

    def _check_compliance_status(self) -> Dict[str, bool]:
        """コンプライアンスステータスをチェック"""
        compliance = {
            'file_integrity': self.config['require_integrity_check'],
            'threat_intelligence': self.threat_intelligence is not None,
            'access_control': self.zero_trust_manager is not None,
            'encryption': self.crypto_manager is not None,
            'audit_logging': self.config['log_security_events']
        }

        if self.config['enable_blockchain']:
            compliance['blockchain_verification'] = self.blockchain_security is not None

        return compliance

    def _log_security_event(self, event: SecurityEvent):
        """セキュリティイベントをログ記録"""
        if not self.config['log_security_events']:
            return

        with self._lock:
            self.security_events.append(event)

            # イベント数の制限
            if len(self.security_events) > self.max_events:
                self.security_events = self.security_events[-self.max_events:]

        # ログ出力
        self.logger.log(
            getattr(logging, event.severity.upper(), logging.INFO),
            f"[{event.severity}] {event.description}",
            extra={
                'event_id': event.event_id,
                'user_id': event.user_id,
                'session_id': event.session_id,
                'ip_address': event.ip_address
            }
        )

    def validate(self, data: Any) -> bool:
        """基本検証"""
        return self._initialized and isinstance(data, (str, Path))

    def get_security_info(self) -> Dict[str, Any]:
        """セキュリティ情報を取得"""
        return {
            'manager_type': 'UnifiedSecurityManager',
            'security_level': self.security_level.value,
            'initialized': self._initialized,
            'components': {
                'crypto': self.crypto_manager is not None,
                'zero_trust': self.zero_trust_manager is not None,
                'threat_intel': self.threat_intelligence is not None,
                'blockchain': self.blockchain_security is not None,
                'scanner': self.security_scanner is not None
            },
            'config': self.config
        }


# 以下に各コンポーネントクラスを実装
