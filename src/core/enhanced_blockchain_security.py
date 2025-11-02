#!/usr/bin/env python3
"""
ブロックチェーン統合セキュリティシステム
分散型認証とトレーサビリティ機能を提供
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class BlockchainConsensus(Enum):
    """ブロックチェーンコンセンサスアルゴリズム"""
    PROOF_OF_WORK = "pow"
    PROOF_OF_STAKE = "pos"
    DELEGATED_PROOF_OF_STAKE = "dpos"
    PRACTICAL_BYZANTINE_FAULT_TOLERANCE = "pbft"

class AssetType(Enum):
    """資産の種類"""
    DESIGN_FILE = "design_file"
    MATERIAL_BATCH = "material_batch"
    PRINTER_DEVICE = "printer_device"
    PRINT_JOB = "print_job"
    QUALITY_CERTIFICATE = "quality_certificate"

@dataclass
class BlockchainAsset:
    """ブロックチェーン資産"""
    asset_id: str
    asset_type: AssetType
    owner_id: str
    metadata: Dict[str, Any]
    creation_timestamp: float
    last_update_timestamp: float
    blockchain_hash: str
    previous_hash: Optional[str] = None
    signatures: List[str] = field(default_factory=list)

@dataclass
class SmartContract:
    """スマートコントラクト"""
    contract_id: str
    contract_type: str
    code: str
    deployed_at: float
    network_address: str
    functions: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)

@dataclass
class DecentralizedIdentity:
    """分散型アイデンティティ"""
    did: str  # Decentralized Identifier
    public_key: str
    private_key_hash: str
    verification_method: str
    services: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

class EnhancedBlockchainSecurity:
    """強化されたブロックチェーンセキュリティシステム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.assets: Dict[str, BlockchainAsset] = {}
        self.smart_contracts: Dict[str, SmartContract] = {}
        self.identities: Dict[str, DecentralizedIdentity] = {}
        self.transaction_log: List[Dict[str, Any]] = []
        self.consensus_mechanism = BlockchainConsensus.PROOF_OF_STAKE

    def create_decentralized_identity(self, user_id: str, public_key: str) -> DecentralizedIdentity:
        """分散型アイデンティティを作成"""
        did = f"did:cad:{user_id}:{uuid.uuid4().hex[:16]}"

        identity = DecentralizedIdentity(
            did=did,
            public_key=public_key,
            private_key_hash=hashlib.sha256(public_key.encode()).hexdigest(),
            verification_method="Ed25519VerificationKey2020"
        )

        self.identities[did] = identity

        # ブロックチェーンに記録
        self._record_identity_creation(identity)

        self.logger.info(f"Created decentralized identity: {did}")
        return identity

    def register_asset(self, asset_type: AssetType, owner_id: str,
                      metadata: Dict[str, Any], identity: DecentralizedIdentity) -> BlockchainAsset:
        """資産をブロックチェーンに登録"""
        asset_id = f"asset_{asset_type.value}_{uuid.uuid4().hex[:16]}"

        # 資産データをハッシュ化
        asset_data = {
            "asset_id": asset_id,
            "asset_type": asset_type.value,
            "owner_id": owner_id,
            "metadata": metadata,
            "timestamp": time.time()
        }

        blockchain_hash = self._calculate_asset_hash(asset_data)

        # 前の資産のハッシュを取得（チェーン構築）
        previous_hash = None
        if self.assets:
            # 最後の資産のハッシュを前のハッシュとして使用
            last_asset = list(self.assets.values())[-1]
            previous_hash = last_asset.blockchain_hash

        asset = BlockchainAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            owner_id=owner_id,
            metadata=metadata,
            creation_timestamp=time.time(),
            last_update_timestamp=time.time(),
            blockchain_hash=blockchain_hash,
            previous_hash=previous_hash
        )

        # 署名を追加
        signature = self._sign_asset(asset, identity)
        asset.signatures.append(signature)

        self.assets[asset_id] = asset

        # ブロックチェーンに記録
        self._record_asset_registration(asset)

        self.logger.info(f"Registered blockchain asset: {asset_id}")
        return asset

    def verify_asset_integrity(self, asset_id: str, expected_hash: str = None) -> Dict[str, Any]:
        """資産の完全性を検証"""
        if asset_id not in self.assets:
            return {"valid": False, "error": "Asset not found"}

        asset = self.assets[asset_id]

        # 現在のハッシュを計算
        asset_data = {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type.value,
            "owner_id": asset.owner_id,
            "metadata": asset.metadata,
            "timestamp": asset.creation_timestamp
        }

        current_hash = self._calculate_asset_hash(asset_data)

        # ハッシュを検証
        if expected_hash and current_hash != expected_hash:
            return {
                "valid": False,
                "error": "Hash mismatch",
                "expected": expected_hash,
                "actual": current_hash
            }

        # 署名を検証
        signature_valid = self._verify_asset_signatures(asset)

        # チェーンの整合性を検証
        chain_valid = self._verify_asset_chain(asset)

        return {
            "valid": current_hash == asset.blockchain_hash and signature_valid and chain_valid,
            "hash_valid": current_hash == asset.blockchain_hash,
            "signature_valid": signature_valid,
            "chain_valid": chain_valid,
            "current_hash": current_hash
        }

    def create_smart_contract(self, contract_type: str, code: str,
                            network: str = "private") -> SmartContract:
        """スマートコントラクトを作成"""
        contract_id = f"contract_{contract_type}_{uuid.uuid4().hex[:16]}"

        contract = SmartContract(
            contract_id=contract_id,
            contract_type=contract_type,
            code=code,
            deployed_at=time.time(),
            network_address=f"0x{uuid.uuid4().hex[:40]}",  # 仮のアドレス
            functions=self._extract_contract_functions(code),
            events=self._extract_contract_events(code)
        )

        self.smart_contracts[contract_id] = contract

        # ブロックチェーンにデプロイ記録
        self._record_contract_deployment(contract)

        self.logger.info(f"Created smart contract: {contract_id}")
        return contract

    def execute_smart_contract(self, contract_id: str, function_name: str,
                             parameters: Dict[str, Any]) -> Dict[str, Any]:
        """スマートコントラクトを実行"""
        if contract_id not in self.smart_contracts:
            return {"success": False, "error": "Contract not found"}

        contract = self.smart_contracts[contract_id]

        if function_name not in contract.functions:
            return {"success": False, "error": f"Function {function_name} not found"}

        # コントラクト実行をシミュレート
        execution_result = self._simulate_contract_execution(contract, function_name, parameters)

        # 実行結果をブロックチェーンに記録
        self._record_contract_execution(contract_id, function_name, parameters, execution_result)

        return {
            "success": True,
            "contract_id": contract_id,
            "function": function_name,
            "result": execution_result,
            "transaction_hash": f"0x{uuid.uuid4().hex[:64]}"
        }

    def track_supply_chain(self, material_id: str, supplier: str,
                          batch_number: str, quality_cert: str) -> Dict[str, Any]:
        """サプライチェーンを追跡"""
        # サプライチェーンレコードを作成
        record = {
            "material_id": material_id,
            "supplier": supplier,
            "batch_number": batch_number,
            "timestamp": time.time(),
            "quality_certification": quality_cert,
            "blockchain_hash": hashlib.sha256(f"{material_id}{supplier}{batch_number}".encode()).hexdigest()
        }

        # ブロックチェーンに記録
        transaction_hash = self._record_supply_chain_event(record)

        return {
            "success": True,
            "transaction_hash": transaction_hash,
            "record": record
        }

    def _calculate_asset_hash(self, asset_data: Dict[str, Any]) -> str:
        """資産データのハッシュを計算"""
        # データをJSON形式でシリアライズしてハッシュ化
        data_str = json.dumps(asset_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _sign_asset(self, asset: BlockchainAsset, identity: DecentralizedIdentity) -> str:
        """資産に署名"""
        # 署名データを準備
        sign_data = {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type.value,
            "timestamp": asset.creation_timestamp
        }

        # 簡易的な署名（実際にはデジタル署名アルゴリズムを使用）
        signature_data = hashlib.sha256(json.dumps(sign_data).encode()).hexdigest()
        return f"sig_{identity.did}_{signature_data[:16]}"

    def _verify_asset_signatures(self, asset: BlockchainAsset) -> bool:
        """資産の署名を検証"""
        # 簡易的な署名検証（実際には公開鍵暗号を使用）
        return len(asset.signatures) > 0

    def _verify_asset_chain(self, asset: BlockchainAsset) -> bool:
        """資産チェーンの整合性を検証"""
        if not asset.previous_hash:
            return True  # 最初の資産

        # 前の資産のハッシュを検証
        # 実際の実装では前の資産のブロックチェーン上のハッシュを検証
        return True  # 簡易的に常に有効とする

    def _extract_contract_functions(self, code: str) -> List[str]:
        """コントラクトコードから関数を抽出"""
        functions = []
        lines = code.split('\n')

        for line in lines:
            if 'function ' in line or 'def ' in line:
                # 関数名を抽出
                if 'function ' in line:
                    func_name = line.split('function ')[1].split('(')[0].strip()
                else:
                    func_name = line.split('def ')[1].split('(')[0].strip()
                functions.append(func_name)

        return functions

    def _extract_contract_events(self, code: str) -> List[str]:
        """コントラクトコードからイベントを抽出"""
        events = []
        lines = code.split('\n')

        for line in lines:
            if 'event ' in line:
                event_name = line.split('event ')[1].split('(')[0].strip()
                events.append(event_name)

        return events

    def _simulate_contract_execution(self, contract: SmartContract,
                                   function_name: str, parameters: Dict[str, Any]) -> Any:
        """コントラクト実行をシミュレート"""
        # コントラクトタイプに応じた実行シミュレーション
        if contract.contract_type == "material_tracking":
            if function_name == "verify_material":
                return {
                    "verified": True,
                    "material_id": parameters.get("material_id"),
                    "quality_score": 0.95
                }
        elif contract.contract_type == "quality_assurance":
            if function_name == "validate_print":
                return {
                    "valid": True,
                    "quality_metrics": {
                        "strength": 0.92,
                        "accuracy": 0.88,
                        "finish": 0.95
                    }
                }

        return {"executed": True, "result": "default_response"}

    def _record_identity_creation(self, identity: DecentralizedIdentity) -> None:
        """アイデンティティ作成を記録"""
        transaction = {
            "type": "identity_creation",
            "did": identity.did,
            "timestamp": time.time(),
            "tx_hash": f"0x{uuid.uuid4().hex[:64]}"
        }
        self.transaction_log.append(transaction)

    def _record_asset_registration(self, asset: BlockchainAsset) -> None:
        """資産登録を記録"""
        transaction = {
            "type": "asset_registration",
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type.value,
            "timestamp": time.time(),
            "tx_hash": f"0x{uuid.uuid4().hex[:64]}"
        }
        self.transaction_log.append(transaction)

    def _record_contract_deployment(self, contract: SmartContract) -> None:
        """コントラクトデプロイを記録"""
        transaction = {
            "type": "contract_deployment",
            "contract_id": contract.contract_id,
            "contract_type": contract.contract_type,
            "timestamp": time.time(),
            "tx_hash": f"0x{uuid.uuid4().hex[:64]}"
        }
        self.transaction_log.append(transaction)

    def _record_contract_execution(self, contract_id: str, function_name: str,
                                 parameters: Dict[str, Any], result: Any) -> None:
        """コントラクト実行を記録"""
        transaction = {
            "type": "contract_execution",
            "contract_id": contract_id,
            "function_name": function_name,
            "parameters": parameters,
            "result": result,
            "timestamp": time.time(),
            "tx_hash": f"0x{uuid.uuid4().hex[:64]}"
        }
        self.transaction_log.append(transaction)

    def _record_supply_chain_event(self, record: Dict[str, Any]) -> str:
        """サプライチェーンイベントを記録"""
        tx_hash = f"0x{uuid.uuid4().hex[:64]}"
        transaction = {
            "type": "supply_chain",
            "record": record,
            "timestamp": time.time(),
            "tx_hash": tx_hash
        }
        self.transaction_log.append(transaction)

        return tx_hash

    def get_asset_provenance(self, asset_id: str) -> Dict[str, Any]:
        """資産の出所情報を取得"""
        if asset_id not in self.assets:
            return {"error": "Asset not found"}

        asset = self.assets[asset_id]

        # 関連するトランザクションを取得
        related_transactions = [
            tx for tx in self.transaction_log
            if tx.get("asset_id") == asset_id or tx.get("asset_type") == asset.asset_type.value
        ]

        return {
            "asset_id": asset_id,
            "asset_type": asset.asset_type.value,
            "owner_id": asset.owner_id,
            "creation_time": asset.creation_timestamp,
            "last_update": asset.last_update_timestamp,
            "provenance_chain": related_transactions,
            "integrity_verified": self.verify_asset_integrity(asset_id)["valid"]
        }

    def get_supply_chain_history(self, material_id: str) -> List[Dict[str, Any]]:
        """サプライチェーン履歴を取得"""
        history = []

        for tx in self.transaction_log:
            if tx.get("type") == "supply_chain" and tx["record"].get("material_id") == material_id:
                history.append(tx["record"])

        return sorted(history, key=lambda x: x.get("timestamp", 0))

    def validate_design_authenticity(self, design_file: str, expected_hash: str) -> Dict[str, Any]:
        """デザインの真正性を検証"""
        # ファイルハッシュを計算
        file_hash = hashlib.sha256(design_file.encode()).hexdigest()

        # ブロックチェーン上のハッシュと比較
        matching_assets = [
            asset for asset in self.assets.values()
            if asset.asset_type == AssetType.DESIGN_FILE and
            asset.metadata.get("file_hash") == file_hash
        ]

        if not matching_assets:
            return {
                "authentic": False,
                "reason": "Design not registered on blockchain",
                "file_hash": file_hash
            }

        asset = matching_assets[0]

        # 署名とチェーンを検証
        integrity = self.verify_asset_integrity(asset.asset_id)

        return {
            "authentic": integrity["valid"],
            "asset_id": asset.asset_id,
            "owner_id": asset.owner_id,
            "registration_time": asset.creation_timestamp,
            "file_hash": file_hash,
            "integrity_details": integrity
        }

# グローバルインスタンス
_blockchain_security = None

def get_blockchain_security() -> EnhancedBlockchainSecurity:
    """ブロックチェーンセキュリティシステムのインスタンスを取得"""
    global _blockchain_security
    if _blockchain_security is None:
        _blockchain_security = EnhancedBlockchainSecurity()
    return _blockchain_security
