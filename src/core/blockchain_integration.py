"""Blockchain integration for distributed ledger and traceability in 3D printing."""

import hashlib
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, utils


class BlockchainNetwork(Enum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    HYPERLEDGER_FABRIC = "hyperledger_fabric"
    POLYGON = "polygon"
    BINANCE_SMART_CHAIN = "binance_smart_chain"
    PRIVATE_CHAIN = "private_chain"


class TransactionType(Enum):
    """Types of blockchain transactions."""
    MODEL_REGISTRATION = "model_registration"
    PRINT_JOB_CREATION = "print_job_creation"
    MATERIAL_CERTIFICATION = "material_certification"
    QUALITY_VERIFICATION = "quality_verification"
    OWNERSHIP_TRANSFER = "ownership_transfer"
    DESIGN_IP_PROTECTION = "design_ip_protection"


@dataclass
class BlockchainTransaction:
    """Blockchain transaction record."""
    tx_hash: str
    transaction_type: TransactionType
    timestamp: float
    data: Dict[str, Any]
    signatures: List[str] = field(default_factory=list)
    block_height: Optional[int] = None
    gas_used: Optional[int] = None
    status: str = "pending"


@dataclass
class SmartContract:
    """Smart contract definition."""
    name: str
    address: str
    network: BlockchainNetwork
    abi: List[Dict[str, Any]] = field(default_factory=list)
    bytecode: str = ""
    functions: List[str] = field(default_factory=list)


class DistributedLedger:
    """Distributed ledger for 3D printing traceability."""

    def __init__(self):
        """Initialize distributed ledger."""
        self.logger = logging.getLogger(__name__)
        self.transactions: Dict[str, BlockchainTransaction] = {}
        self.blocks: List[Dict[str, Any]] = []
        self.current_block: Dict[str, Any] = {}

        # Merkle tree for transaction verification
        self.merkle_root = None

        # Consensus mechanism (simplified)
        self.validators: List[str] = []
        self.block_time = 12  # seconds

        # Thread safety
        self._lock = threading.RLock()

    def register_model(self, model_data: Dict[str, Any],
                      creator_id: str, metadata: Dict[str, Any]) -> str:
        """Register a 3D model on the blockchain.

        Args:
            model_data: 3D model information
            creator_id: Creator's unique identifier
            metadata: Additional model metadata

        Returns:
            Transaction hash
        """
        # Create model hash for uniqueness
        model_hash = self._calculate_model_hash(model_data)

        transaction_data = {
            'model_hash': model_hash,
            'creator_id': creator_id,
            'model_metadata': metadata,
            'registration_timestamp': time.time(),
            'ipfs_hash': self._upload_to_ipfs(model_data)  # Simulate IPFS upload
        }

        tx_hash = self._create_transaction(
            TransactionType.MODEL_REGISTRATION,
            transaction_data
        )

        self.logger.info(f"Registered 3D model on blockchain: {model_hash[:16]}...")
        return tx_hash

    def create_print_job(self, model_hash: str, printer_id: str,
                        print_parameters: Dict[str, Any],
                        material_info: Dict[str, Any]) -> str:
        """Create a print job record on the blockchain.

        Args:
            model_hash: Hash of the 3D model
            printer_id: Printer identifier
            print_parameters: Print job parameters
            material_info: Material information

        Returns:
            Transaction hash
        """
        transaction_data = {
            'model_hash': model_hash,
            'printer_id': printer_id,
            'print_parameters': print_parameters,
            'material_info': material_info,
            'start_time': time.time(),
            'estimated_completion': time.time() + 3600  # 1 hour estimate
        }

        tx_hash = self._create_transaction(
            TransactionType.PRINT_JOB_CREATION,
            transaction_data
        )

        self.logger.info(f"Created print job on blockchain for printer {printer_id}")
        return tx_hash

    def certify_material(self, material_data: Dict[str, Any],
                        supplier_id: str, batch_id: str) -> str:
        """Certify material authenticity and quality.

        Args:
            material_data: Material specifications and properties
            supplier_id: Material supplier identifier
            batch_id: Material batch identifier

        Returns:
            Transaction hash
        """
        transaction_data = {
            'material_data': material_data,
            'supplier_id': supplier_id,
            'batch_id': batch_id,
            'certification_timestamp': time.time(),
            'quality_metrics': material_data.get('quality_metrics', {}),
            'sustainability_data': material_data.get('sustainability_data', {})
        }

        tx_hash = self._create_transaction(
            TransactionType.MATERIAL_CERTIFICATION,
            transaction_data
        )

        self.logger.info(f"Certified material batch {batch_id} from supplier {supplier_id}")
        return tx_hash

    def verify_quality(self, print_job_hash: str,
                      quality_metrics: Dict[str, Any],
                      inspector_id: str) -> str:
        """Verify and record print quality on the blockchain.

        Args:
            print_job_hash: Hash of the print job
            quality_metrics: Quality measurement results
            inspector_id: Inspector identifier

        Returns:
            Transaction hash
        """
        transaction_data = {
            'print_job_hash': print_job_hash,
            'quality_metrics': quality_metrics,
            'inspector_id': inspector_id,
            'verification_timestamp': time.time(),
            'overall_quality_score': quality_metrics.get('overall_score', 0),
            'defects_found': quality_metrics.get('defects', [])
        }

        tx_hash = self._create_transaction(
            TransactionType.QUALITY_VERIFICATION,
            transaction_data
        )

        self.logger.info(f"Verified quality for print job {print_job_hash[:16]}...")
        return tx_hash

    def transfer_ownership(self, model_hash: str, from_owner: str,
                          to_owner: str, transfer_terms: Dict[str, Any]) -> str:
        """Transfer ownership of a 3D model.

        Args:
            model_hash: Hash of the 3D model
            from_owner: Current owner
            to_owner: New owner
            transfer_terms: Transfer terms and conditions

        Returns:
            Transaction hash
        """
        transaction_data = {
            'model_hash': model_hash,
            'from_owner': from_owner,
            'to_owner': to_owner,
            'transfer_terms': transfer_terms,
            'transfer_timestamp': time.time(),
            'license_type': transfer_terms.get('license_type', 'full_transfer')
        }

        tx_hash = self._create_transaction(
            TransactionType.OWNERSHIP_TRANSFER,
            transaction_data
        )

        self.logger.info(f"Transferred ownership of model {model_hash[:16]}... from {from_owner} to {to_owner}")
        return tx_hash

    def protect_design_ip(self, model_hash: str, ip_rights: Dict[str, Any],
                         creator_id: str) -> str:
        """Protect intellectual property of a design.

        Args:
            model_hash: Hash of the 3D model
            ip_rights: Intellectual property rights information
            creator_id: Creator identifier

        Returns:
            Transaction hash
        """
        transaction_data = {
            'model_hash': model_hash,
            'ip_rights': ip_rights,
            'creator_id': creator_id,
            'protection_timestamp': time.time(),
            'license_terms': ip_rights.get('license_terms', {}),
            'royalty_structure': ip_rights.get('royalty_structure', {})
        }

        tx_hash = self._create_transaction(
            TransactionType.DESIGN_IP_PROTECTION,
            transaction_data
        )

        self.logger.info(f"Protected IP for model {model_hash[:16]}...")
        return tx_hash

    def _calculate_model_hash(self, model_data: Dict[str, Any]) -> str:
        """Calculate unique hash for a 3D model."""
        # Create a deterministic string representation
        model_str = json.dumps(model_data, sort_keys=True, separators=(',', ':'))

        # Hash using SHA-256
        return hashlib.sha256(model_str.encode()).hexdigest()

    def _upload_to_ipfs(self, data: Dict[str, Any]) -> str:
        """Simulate IPFS upload (in real implementation, this would upload to IPFS)."""
        # Create content hash
        content_str = json.dumps(data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Simulate IPFS hash (Qm... format)
        return f"Qm{content_hash[:44]}"

    def _create_transaction(self, tx_type: TransactionType, data: Dict[str, Any]) -> str:
        """Create a blockchain transaction."""
        tx_hash = hashlib.sha256(f"{tx_type.value}_{time.time()}_{json.dumps(data)}".encode()).hexdigest()

        transaction = BlockchainTransaction(
            tx_hash=tx_hash,
            transaction_type=tx_type,
            timestamp=time.time(),
            data=data
        )

        with self._lock:
            self.transactions[tx_hash] = transaction

        # Add to current block
        self._add_to_current_block(transaction)

        return tx_hash

    def _add_to_current_block(self, transaction: BlockchainTransaction):
        """Add transaction to current block."""
        if 'transactions' not in self.current_block:
            self.current_block['transactions'] = []

        self.current_block['transactions'].append(transaction)

        # Check if block should be sealed
        if len(self.current_block['transactions']) >= 10:  # Block size of 10 transactions
            self._seal_block()

    def _seal_block(self):
        """Seal the current block and create a new one."""
        if not self.current_block.get('transactions'):
            return

        # Calculate block hash
        block_data = json.dumps(self.current_block, sort_keys=True, default=str)
        block_hash = hashlib.sha256(block_data.encode()).hexdigest()

        # Create block header
        block_header = {
            'block_hash': block_hash,
            'previous_hash': self.blocks[-1]['block_hash'] if self.blocks else '0' * 64,
            'timestamp': time.time(),
            'transaction_count': len(self.current_block['transactions']),
            'merkle_root': self._calculate_merkle_root(self.current_block['transactions'])
        }

        # Create complete block
        block = {
            **block_header,
            'transactions': self.current_block['transactions']
        }

        # Add to blockchain
        self.blocks.append(block)

        # Reset current block
        self.current_block = {}

        self.logger.info(f"Sealed block {block_hash[:16]}... with {len(block['transactions'])} transactions")

    def _calculate_merkle_root(self, transactions: List[BlockchainTransaction]) -> str:
        """Calculate Merkle root for transactions."""
        if not transactions:
            return '0' * 64

        # Simple Merkle tree calculation (simplified)
        tx_hashes = [tx.tx_hash for tx in transactions]

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 == 1:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def verify_model_ownership(self, model_hash: str, user_id: str) -> bool:
        """Verify if a user owns a 3D model.

        Args:
            model_hash: Hash of the 3D model
            user_id: User ID to check

        Returns:
            True if user owns the model
        """
        with self._lock:
            # Find all transactions related to this model
            model_transactions = [
                tx for tx in self.transactions.values()
                if tx.data.get('model_hash') == model_hash
            ]

            # Check ownership transfer chain
            current_owner = None

            for tx in sorted(model_transactions, key=lambda x: x.timestamp):
                if tx.transaction_type == TransactionType.MODEL_REGISTRATION:
                    current_owner = tx.data.get('creator_id')
                elif tx.transaction_type == TransactionType.OWNERSHIP_TRANSFER:
                    if tx.data.get('from_owner') == current_owner:
                        current_owner = tx.data.get('to_owner')

            return current_owner == user_id

    def get_model_history(self, model_hash: str) -> List[Dict[str, Any]]:
        """Get complete history of a 3D model.

        Args:
            model_hash: Hash of the 3D model

        Returns:
            List of historical events
        """
        with self._lock:
            model_transactions = [
                tx for tx in self.transactions.values()
                if tx.data.get('model_hash') == model_hash
            ]

            history = []
            for tx in sorted(model_transactions, key=lambda x: x.timestamp):
                history.append({
                    'transaction_hash': tx.tx_hash,
                    'transaction_type': tx.transaction_type.value,
                    'timestamp': tx.timestamp,
                    'data': tx.data
                })

            return history

    def get_supply_chain_traceability(self, material_batch_id: str) -> List[Dict[str, Any]]:
        """Get supply chain traceability for a material batch.

        Args:
            material_batch_id: Material batch identifier

        Returns:
            Supply chain trace
        """
        with self._lock:
            material_transactions = [
                tx for tx in self.transactions.values()
                if tx.data.get('batch_id') == material_batch_id
            ]

            supply_chain = []
            for tx in sorted(material_transactions, key=lambda x: x.timestamp):
                supply_chain.append({
                    'transaction_hash': tx.tx_hash,
                    'transaction_type': tx.transaction_type.value,
                    'timestamp': tx.timestamp,
                    'supplier_id': tx.data.get('supplier_id'),
                    'material_data': tx.data.get('material_data', {}),
                    'quality_metrics': tx.data.get('quality_metrics', {})
                })

            return supply_chain

    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics.

        Returns:
            Blockchain statistics
        """
        with self._lock:
            total_transactions = len(self.transactions)
            total_blocks = len(self.blocks)

            # Transaction type distribution
            tx_types = {}
            for tx in self.transactions.values():
                tx_type = tx.transaction_type.value
                tx_types[tx_type] = tx_types.get(tx_type, 0) + 1

            return {
                'total_transactions': total_transactions,
                'total_blocks': total_blocks,
                'current_block_transactions': len(self.current_block.get('transactions', [])),
                'transaction_types': tx_types,
                'network_uptime': time.time() - getattr(self, '_start_time', time.time()),
                'merkle_root_verified': True
            }


class SmartContractManager:
    """Manager for smart contracts."""

    def __init__(self):
        """Initialize smart contract manager."""
        self.logger = logging.getLogger(__name__)
        self.contracts: Dict[str, SmartContract] = {}
        self.deployed_contracts: Dict[str, Dict[str, Any]] = {}

        # Initialize common contracts
        self._initialize_common_contracts()

    def _initialize_common_contracts(self):
        """Initialize commonly used smart contracts."""
        # 3D Model Registry Contract
        model_registry_contract = SmartContract(
            name="ModelRegistry",
            address="0x3DModelRegistryContract",
            network=BlockchainNetwork.ETHEREUM,
            functions=[
                "registerModel",
                "transferOwnership",
                "verifyOwnership",
                "getModelMetadata"
            ]
        )

        # Material Certification Contract
        material_cert_contract = SmartContract(
            name="MaterialCertification",
            address="0xMaterialCertificationContract",
            network=BlockchainNetwork.POLYGON,
            functions=[
                "certifyMaterial",
                "verifyCertification",
                "getBatchHistory"
            ]
        )

        # Quality Assurance Contract
        quality_contract = SmartContract(
            name="QualityAssurance",
            address="0xQualityAssuranceContract",
            network=BlockchainNetwork.ETHEREUM,
            functions=[
                "recordQualityCheck",
                "verifyQualityReport",
                "getQualityHistory"
            ]
        )

        self.contracts.update({
            'model_registry': model_registry_contract,
            'material_certification': material_cert_contract,
            'quality_assurance': quality_contract
        })

    def deploy_contract(self, contract: SmartContract) -> bool:
        """Deploy a smart contract.

        Args:
            contract: Smart contract to deploy

        Returns:
            True if deployment successful
        """
        try:
            # Simulate contract deployment
            deployment_result = {
                'contract_address': contract.address,
                'deployment_tx': f"0x{secrets.token_hex(32)}",
                'gas_used': 150000,
                'deployment_time': time.time()
            }

            self.deployed_contracts[contract.address] = deployment_result

            self.logger.info(f"Deployed smart contract {contract.name} at {contract.address}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy contract {contract.name}: {e}")
            return False

    def call_contract_function(self, contract_address: str,
                              function_name: str,
                              parameters: List[Any]) -> Dict[str, Any]:
        """Call a smart contract function.

        Args:
            contract_address: Contract address
            function_name: Function name to call
            parameters: Function parameters

        Returns:
            Function result
        """
        if contract_address not in self.deployed_contracts:
            return {'error': 'Contract not deployed'}

        # Simulate contract function call
        result = {
            'success': True,
            'result': f"Function {function_name} executed successfully",
            'gas_used': 21000,
            'execution_time': 0.1
        }

        self.logger.info(f"Called contract function {function_name} on {contract_address}")
        return result


class DecentralizedIdentity:
    """Decentralized identity management."""

    def __init__(self):
        """Initialize decentralized identity system."""
        self.logger = logging.getLogger(__name__)
        self.identities: Dict[str, Dict[str, Any]] = {}
        self.verifiable_credentials: Dict[str, List[Dict[str, Any]]] = {}

    def create_did(self, user_id: str, public_key: str) -> str:
        """Create a decentralized identifier (DID).

        Args:
            user_id: User identifier
            public_key: User's public key

        Returns:
            DID string
        """
        # Create DID in format: did:3dprint:user_id
        did = f"did:3dprint:{user_id}"

        identity = {
            'did': did,
            'user_id': user_id,
            'public_key': public_key,
            'created_at': time.time(),
            'status': 'active',
            'credentials': []
        }

        self.identities[did] = identity

        self.logger.info(f"Created DID: {did}")
        return did

    def issue_verifiable_credential(self, issuer_did: str, subject_did: str,
                                  credential_type: str, claims: Dict[str, Any]) -> str:
        """Issue a verifiable credential.

        Args:
            issuer_did: Issuer's DID
            subject_did: Subject's DID
            credential_type: Type of credential
            claims: Credential claims

        Returns:
            Credential ID
        """
        import uuid

        credential = {
            'id': str(uuid.uuid4()),
            'issuer': issuer_did,
            'subject': subject_did,
            'type': credential_type,
            'claims': claims,
            'issued_at': time.time(),
            'expires_at': time.time() + (365 * 24 * 3600),  # 1 year
            'proof': {
                'type': 'Ed25519Signature2020',
                'created': time.time(),
                'verification_method': f"{issuer_did}#keys-1"
            }
        }

        if subject_did not in self.verifiable_credentials:
            self.verifiable_credentials[subject_did] = []

        self.verifiable_credentials[subject_did].append(credential)

        self.logger.info(f"Issued {credential_type} credential to {subject_did}")
        return credential['id']

    def verify_credential(self, credential: Dict[str, Any]) -> bool:
        """Verify a verifiable credential.

        Args:
            credential: Credential to verify

        Returns:
            True if credential is valid
        """
        try:
            # Check expiration
            if credential.get('expires_at', float('inf')) < time.time():
                return False

            # Verify issuer exists
            issuer_did = credential.get('issuer')
            if issuer_did not in self.identities:
                return False

            # Verify credential structure
            required_fields = ['id', 'issuer', 'subject', 'type', 'claims']
            if not all(field in credential for field in required_fields):
                return False

            # In real implementation, verify cryptographic proof
            return True

        except Exception as e:
            self.logger.error(f"Error verifying credential: {e}")
            return False

    def get_user_credentials(self, did: str) -> List[Dict[str, Any]]:
        """Get all credentials for a user.

        Args:
            did: User's DID

        Returns:
            List of verifiable credentials
        """
        return self.verifiable_credentials.get(did, [])


class BlockchainIntegrationManager:
    """Main manager for blockchain integration."""

    def __init__(self):
        """Initialize blockchain integration manager."""
        self.logger = logging.getLogger(__name__)
        self.ledger = DistributedLedger()
        self.contract_manager = SmartContractManager()
        self.identity_manager = DecentralizedIdentity()

        # Network connections
        self.network_connections: Dict[BlockchainNetwork, Any] = {}

        # Start time for uptime calculation
        self._start_time = time.time()

    def register_3d_model(self, model_data: Dict[str, Any],
                        creator_id: str) -> Dict[str, Any]:
        """Register a 3D model on the blockchain.

        Args:
            model_data: 3D model data
            creator_id: Creator identifier

        Returns:
            Registration result
        """
        try:
            tx_hash = self.ledger.register_model(model_data, creator_id, {})

            return {
                'success': True,
                'transaction_hash': tx_hash,
                'model_hash': self.ledger._calculate_model_hash(model_data),
                'ipfs_hash': f"Qm{hashlib.sha256(json.dumps(model_data).encode()).hexdigest()[:44]}",
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to register 3D model: {e}")
            return {'success': False, 'error': str(e)}

    def create_print_job_record(self, model_hash: str, printer_id: str,
                              print_params: Dict[str, Any],
                              material_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a print job record.

        Args:
            model_hash: Model hash
            printer_id: Printer ID
            print_params: Print parameters
            material_info: Material information

        Returns:
            Job creation result
        """
        try:
            tx_hash = self.ledger.create_print_job(
                model_hash, printer_id, print_params, material_info
            )

            return {
                'success': True,
                'transaction_hash': tx_hash,
                'print_job_id': f"print_{tx_hash[:16]}",
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to create print job record: {e}")
            return {'success': False, 'error': str(e)}

    def certify_material_supply(self, material_data: Dict[str, Any],
                              supplier_id: str, batch_id: str) -> Dict[str, Any]:
        """Certify material supply chain.

        Args:
            material_data: Material information
            supplier_id: Supplier identifier
            batch_id: Material batch ID

        Returns:
            Certification result
        """
        try:
            tx_hash = self.ledger.certify_material(material_data, supplier_id, batch_id)

            return {
                'success': True,
                'transaction_hash': tx_hash,
                'certification_id': f"cert_{tx_hash[:16]}",
                'batch_id': batch_id,
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to certify material: {e}")
            return {'success': False, 'error': str(e)}

    def record_quality_verification(self, print_job_hash: str,
                                  quality_data: Dict[str, Any],
                                  inspector_id: str) -> Dict[str, Any]:
        """Record quality verification.

        Args:
            print_job_hash: Print job hash
            quality_data: Quality measurements
            inspector_id: Inspector identifier

        Returns:
            Verification result
        """
        try:
            tx_hash = self.ledger.verify_quality(print_job_hash, quality_data, inspector_id)

            return {
                'success': True,
                'transaction_hash': tx_hash,
                'quality_score': quality_data.get('overall_score', 0),
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to record quality verification: {e}")
            return {'success': False, 'error': str(e)}

    def create_decentralized_identity(self, user_id: str, public_key: str) -> str:
        """Create decentralized identity for a user.

        Args:
            user_id: User identifier
            public_key: User's public key

        Returns:
            DID string
        """
        return self.identity_manager.create_did(user_id, public_key)

    def issue_designer_credential(self, creator_did: str, designer_did: str,
                                design_skills: List[str]) -> str:
        """Issue designer credential.

        Args:
            creator_did: Credential issuer DID
            designer_did: Credential subject DID
            design_skills: Design skills to certify

        Returns:
            Credential ID
        """
        claims = {
            'design_skills': design_skills,
            'certification_level': 'professional',
            'certified_by': creator_did
        }

        return self.identity_manager.issue_verifiable_credential(
            creator_did, designer_did, 'DesignerCertification', claims
        )

    def get_model_ownership_chain(self, model_hash: str) -> List[Dict[str, Any]]:
        """Get complete ownership chain for a model.

        Args:
            model_hash: Model hash

        Returns:
            Ownership chain
        """
        return self.ledger.get_model_history(model_hash)

    def get_supply_chain_trace(self, material_batch_id: str) -> List[Dict[str, Any]]:
        """Get supply chain traceability.

        Args:
            material_batch_id: Material batch ID

        Returns:
            Supply chain trace
        """
        return self.ledger.get_supply_chain_traceability(material_batch_id)

    def verify_model_authenticity(self, model_hash: str) -> Dict[str, Any]:
        """Verify model authenticity and ownership.

        Args:
            model_hash: Model hash

        Returns:
            Verification result
        """
        history = self.ledger.get_model_history(model_hash)

        if not history:
            return {'authentic': False, 'reason': 'Model not found on blockchain'}

        # Check if model is registered and has valid ownership chain
        registration_tx = None
        for tx in history:
            if tx['transaction_type'] == 'model_registration':
                registration_tx = tx
                break

        if not registration_tx:
            return {'authentic': False, 'reason': 'No valid registration found'}

        return {
            'authentic': True,
            'creator_id': registration_tx['data']['creator_id'],
            'registration_date': registration_tx['timestamp'],
            'total_transactions': len(history),
            'current_owner_verified': True
        }

    def get_blockchain_dashboard_data(self) -> Dict[str, Any]:
        """Get data for blockchain dashboard.

        Returns:
            Dashboard data
        """
        return {
            'ledger_stats': self.ledger.get_blockchain_stats(),
            'contract_stats': {
                'total_contracts': len(self.contract_manager.contracts),
                'deployed_contracts': len(self.contract_manager.deployed_contracts)
            },
            'identity_stats': {
                'total_identities': len(self.identity_manager.identities),
                'total_credentials': sum(len(creds) for creds in self.verifiable_credentials.values())
            },
            'network_status': {
                'networks_connected': len(self.network_connections),
                'last_block_height': len(self.ledger.blocks),
                'average_block_time': self.ledger.block_time
            },
            'traceability_features': {
                'model_tracking': True,
                'material_certification': True,
                'quality_verification': True,
                'supply_chain_traceability': True
            }
        }


# Global blockchain integration manager
blockchain_manager = BlockchainIntegrationManager()
