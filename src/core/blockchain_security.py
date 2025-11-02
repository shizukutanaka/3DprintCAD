"""Blockchain-based security for supply chain tracking and tamper detection.

This module provides blockchain integration for secure tracking of 3D printing
processes, material provenance, and design integrity verification.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

class BlockchainNetwork(Enum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "bsc"
    POLYGON = "polygon"
    PRIVATE_CHAIN = "private"

@dataclass
class BlockchainTransaction:
    """Represents a blockchain transaction for tracking."""
    tx_hash: str
    timestamp: float
    data_hash: str
    previous_tx: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SupplyChainRecord:
    """Supply chain tracking record."""
    material_id: str
    supplier: str
    batch_number: str
    timestamp: float
    quality_certification: str
    blockchain_tx: Optional[str] = None

class BlockchainSecurityManager:
    """Manages blockchain-based security features."""

    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.PRIVATE_CHAIN):
        self.network = network
        self.transaction_history: List[BlockchainTransaction] = []
        self.supply_chain_records: Dict[str, SupplyChainRecord] = {}
        self.logger = logging.getLogger(__name__)

    def register_supply_chain_record(self, record: SupplyChainRecord) -> str:
        """Register a supply chain record on the blockchain."""
        # Create data hash for the record
        record_data = f"{record.material_id}_{record.supplier}_{record.batch_number}_{record.timestamp}"
        data_hash = hashlib.sha256(record_data.encode()).hexdigest()

        # Create blockchain transaction (simplified simulation)
        tx = BlockchainTransaction(
            tx_hash=self._generate_tx_hash(),
            timestamp=time.time(),
            data_hash=data_hash,
            metadata={
                'material_id': record.material_id,
                'type': 'supply_chain_registration'
            }
        )

        self.transaction_history.append(tx)
        record.blockchain_tx = tx.tx_hash
        self.supply_chain_records[record.material_id] = record

        self.logger.info(f"Registered supply chain record: {record.material_id}")
        return tx.tx_hash

    def verify_design_integrity(self, mesh: trimesh.Trimesh, design_metadata: Dict[str, Any]) -> bool:
        """Verify design integrity using blockchain."""
        # Calculate current hash of the mesh and metadata
        current_hash = self._calculate_design_hash(mesh, design_metadata)

        # Check against stored blockchain records
        for tx in self.transaction_history:
            if tx.data_hash == current_hash and tx.metadata.get('type') == 'design_registration':
                self.logger.info(f"Design integrity verified for hash: {current_hash}")
                return True

        self.logger.warning(f"Design integrity check failed for hash: {current_hash}")
        return False

    def register_design_on_blockchain(self, mesh: trimesh.Trimesh, design_metadata: Dict[str, Any]) -> str:
        """Register a design on the blockchain for tamper detection."""
        # Calculate design hash
        design_hash = self._calculate_design_hash(mesh, design_metadata)

        # Create transaction
        tx = BlockchainTransaction(
            tx_hash=self._generate_tx_hash(),
            timestamp=time.time(),
            data_hash=design_hash,
            metadata={
                'type': 'design_registration',
                'designer': design_metadata.get('designer', 'unknown'),
                'version': design_metadata.get('version', '1.0')
            }
        )

        self.transaction_history.append(tx)
        self.logger.info(f"Registered design on blockchain: {tx.tx_hash}")
        return tx.tx_hash

    def _calculate_design_hash(self, mesh: trimesh.Trimesh, metadata: Dict[str, Any]) -> str:
        """Calculate hash for design verification."""
        # Combine mesh data and metadata
        vertices_str = str(mesh.vertices.tolist())
        faces_str = str(mesh.faces.tolist())
        metadata_str = json.dumps(metadata, sort_keys=True)

        combined_data = f"{vertices_str}_{faces_str}_{metadata_str}"
        return hashlib.sha256(combined_data.encode()).hexdigest()

    def _generate_tx_hash(self) -> str:
        """Generate a unique transaction hash."""
        return hashlib.sha256(str(time.time()).encode()).hexdigest()

    def get_supply_chain_history(self, material_id: str) -> Optional[SupplyChainRecord]:
        """Get supply chain history for a material."""
        return self.supply_chain_records.get(material_id)

    def verify_material_authenticity(self, material_id: str) -> bool:
        """Verify material authenticity using blockchain records."""
        if material_id not in self.supply_chain_records:
            return False

        record = self.supply_chain_records[material_id]

        # Check if blockchain transaction exists
        tx_exists = any(tx.tx_hash == record.blockchain_tx for tx in self.transaction_history)

        if not tx_exists:
            self.logger.warning(f"Invalid blockchain transaction for material: {material_id}")
            return False

        return True

    def create_tamper_proof_log(self, event_type: str, data: Dict[str, Any]) -> str:
        """Create a tamper-proof log entry on the blockchain."""
        # Calculate data hash
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        # Create transaction
        tx = BlockchainTransaction(
            tx_hash=self._generate_tx_hash(),
            timestamp=time.time(),
            data_hash=data_hash,
            metadata={
                'type': 'security_log',
                'event_type': event_type
            }
        )

        self.transaction_history.append(tx)
        self.logger.info(f"Created tamper-proof log: {event_type}")
        return tx.tx_hash
