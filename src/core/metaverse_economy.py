"""Metaverse economy with cryptocurrency and NFTs for virtual manufacturing."""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid
import hashlib
import secrets


class VirtualCurrency(Enum):
    """Virtual currencies in the metaverse."""
    METACOIN = "metacoin"
    DESIGN_TOKEN = "design_token"
    MANUFACTURE_CREDIT = "manufacture_credit"
    QUALITY_CERTIFICATE = "quality_certificate"


class NFTCategory(Enum):
    """NFT categories in the metaverse."""
    DESIGN_BLUEPRINT = "design_blueprint"
    MATERIAL_SAMPLE = "material_sample"
    FINISHED_PRODUCT = "finished_product"
    MANUFACTURING_TOOL = "manufacturing_tool"
    VIRTUAL_LAND = "virtual_land"


@dataclass
class VirtualWallet:
    """Virtual wallet for metaverse currency."""
    wallet_id: str
    owner_id: str
    balances: Dict[VirtualCurrency, float] = field(default_factory=dict)
    nft_holdings: List[str] = field(default_factory=list)
    transaction_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class NFTAsset:
    """NFT asset in the metaverse."""
    nft_id: str
    category: NFTCategory
    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    owner_id: str = ""
    creator_id: str = ""
    mint_timestamp: float = field(default_factory=time.time)
    blockchain_hash: str = ""
    rarity: str = "common"
    utility_value: Dict[str, Any] = field(default_factory=dict)


class MetaverseEconomy:
    """Metaverse economy system with cryptocurrency and NFTs."""

    def __init__(self):
        """Initialize metaverse economy."""
        self.logger = logging.getLogger(__name__)
        self.virtual_wallets: Dict[str, VirtualWallet] = {}
        self.nft_assets: Dict[str, NFTAsset] = {}
        self.currency_exchange_rates: Dict[Tuple[VirtualCurrency, VirtualCurrency], float] = {}

        # Marketplace
        self.nft_marketplace: Dict[str, Dict[str, Any]] = {}
        self.active_listings: List[Dict[str, Any]] = []

        # Economic indicators
        self.economic_metrics = {
            'total_circulation': {currency.value: 0.0 for currency in VirtualCurrency},
            'nft_market_volume': 0.0,
            'active_users': 0,
            'transaction_volume_24h': 0.0
        }

    def create_virtual_wallet(self, owner_id: str) -> str:
        """Create a virtual wallet for a user.

        Args:
            owner_id: User identifier

        Returns:
            Wallet ID
        """
        wallet_id = str(uuid.uuid4())

        wallet = VirtualWallet(
            wallet_id=wallet_id,
            owner_id=owner_id,
            balances={currency: 100.0 for currency in VirtualCurrency}  # Initial balance
        )

        self.virtual_wallets[wallet_id] = wallet

        self.logger.info(f"Created virtual wallet {wallet_id} for user {owner_id}")
        return wallet_id

    def mint_nft_asset(self, category: NFTCategory, name: str, description: str,
                      creator_id: str, metadata: Dict[str, Any] = None) -> str:
        """Mint an NFT asset.

        Args:
            category: NFT category
            name: Asset name
            description: Asset description
            creator_id: Creator identifier
            metadata: Additional metadata

        Returns:
            NFT ID
        """
        nft_id = str(uuid.uuid4())

        # Generate blockchain hash (simplified)
        nft_data = {
            'nft_id': nft_id,
            'category': category.value,
            'name': name,
            'description': description,
            'creator_id': creator_id,
            'metadata': metadata or {}
        }

        blockchain_hash = hashlib.sha256(json.dumps(nft_data, sort_keys=True).encode()).hexdigest()

        nft_asset = NFTAsset(
            nft_id=nft_id,
            category=category,
            name=name,
            description=description,
            metadata=metadata or {},
            creator_id=creator_id,
            blockchain_hash=blockchain_hash,
            rarity=self._determine_rarity(metadata),
            utility_value=self._calculate_utility_value(category, metadata)
        )

        self.nft_assets[nft_id] = nft_asset

        # Add to creator's wallet
        creator_wallet = self._find_wallet_by_owner(creator_id)
        if creator_wallet:
            creator_wallet.nft_holdings.append(nft_id)

        self.logger.info(f"Minted NFT {nft_id}: {name} ({category.value})")
        return nft_id

    def _determine_rarity(self, metadata: Dict[str, Any]) -> str:
        """Determine NFT rarity."""
        # Simple rarity determination based on metadata
        quality_score = metadata.get('quality_score', 50)

        if quality_score >= 90:
            return 'legendary'
        elif quality_score >= 75:
            return 'rare'
        elif quality_score >= 60:
            return 'uncommon'
        else:
            return 'common'

    def _calculate_utility_value(self, category: NFTCategory, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate utility value for NFT."""
        utility = {}

        if category == NFTCategory.DESIGN_BLUEPRINT:
            utility['design_bonus'] = metadata.get('design_efficiency', 1.0)
            utility['material_savings'] = metadata.get('material_optimization', 0.0)

        elif category == NFTCategory.MATERIAL_SAMPLE:
            utility['strength_bonus'] = metadata.get('strength_multiplier', 1.0)
            utility['durability_bonus'] = metadata.get('durability_multiplier', 1.0)

        elif category == NFTCategory.MANUFACTURING_TOOL:
            utility['speed_bonus'] = metadata.get('speed_multiplier', 1.0)
            utility['quality_bonus'] = metadata.get('quality_multiplier', 1.0)

        return utility

    def transfer_nft(self, nft_id: str, from_wallet_id: str, to_wallet_id: str,
                    transfer_fee: float = 0.1) -> bool:
        """Transfer NFT between wallets.

        Args:
            nft_id: NFT identifier
            from_wallet_id: Source wallet
            to_wallet_id: Target wallet
            transfer_fee: Transfer fee in METACOIN

        Returns:
            True if transfer successful
        """
        if nft_id not in self.nft_assets:
            return False

        from_wallet = self.virtual_wallets.get(from_wallet_id)
        to_wallet = self.virtual_wallets.get(to_wallet_id)

        if not from_wallet or not to_wallet:
            return False

        nft_asset = self.nft_assets[nft_id]

        # Check ownership
        if nft_id not in from_wallet.nft_holdings:
            return False

        # Process transfer fee
        if from_wallet.balances.get(VirtualCurrency.METACOIN, 0) < transfer_fee:
            return False

        from_wallet.balances[VirtualCurrency.METACOIN] -= transfer_fee

        # Transfer NFT
        from_wallet.nft_holdings.remove(nft_id)
        to_wallet.nft_holdings.append(nft_id)
        nft_asset.owner_id = to_wallet.owner_id

        # Record transaction
        transaction_record = {
            'transaction_id': str(uuid.uuid4()),
            'type': 'nft_transfer',
            'nft_id': nft_id,
            'from_wallet': from_wallet_id,
            'to_wallet': to_wallet_id,
            'transfer_fee': transfer_fee,
            'timestamp': time.time()
        }

        from_wallet.transaction_history.append(transaction_record)
        to_wallet.transaction_history.append(transaction_record)

        self.logger.info(f"Transferred NFT {nft_id} from {from_wallet_id} to {to_wallet_id}")
        return True

    def list_nft_for_sale(self, nft_id: str, seller_wallet_id: str,
                         price: float, currency: VirtualCurrency) -> str:
        """List NFT for sale in marketplace.

        Args:
            nft_id: NFT identifier
            seller_wallet_id: Seller's wallet
            price: Sale price
            currency: Currency for sale

        Returns:
            Listing ID
        """
        listing_id = str(uuid.uuid4())

        if nft_id not in self.nft_assets:
            return ""

        seller_wallet = self.virtual_wallets.get(seller_wallet_id)
        if not seller_wallet or nft_id not in seller_wallet.nft_holdings:
            return ""

        listing = {
            'listing_id': listing_id,
            'nft_id': nft_id,
            'seller_wallet': seller_wallet_id,
            'price': price,
            'currency': currency.value,
            'listed_at': time.time(),
            'status': 'active'
        }

        self.active_listings.append(listing)
        self.nft_marketplace[listing_id] = listing

        self.logger.info(f"Listed NFT {nft_id} for sale: {price} {currency.value}")
        return listing_id

    def purchase_nft(self, listing_id: str, buyer_wallet_id: str) -> bool:
        """Purchase NFT from marketplace.

        Args:
            listing_id: Marketplace listing ID
            buyer_wallet_id: Buyer's wallet

        Returns:
            True if purchase successful
        """
        if listing_id not in self.nft_marketplace:
            return False

        listing = self.nft_marketplace[listing_id]
        buyer_wallet = self.virtual_wallets.get(buyer_wallet_id)

        if not buyer_wallet or listing['status'] != 'active':
            return False

        price = listing['price']
        currency = VirtualCurrency(listing['currency'])

        # Check buyer balance
        if buyer_wallet.balances.get(currency, 0) < price:
            return False

        # Process payment
        buyer_wallet.balances[currency] -= price

        seller_wallet_id = listing['seller_wallet']
        seller_wallet = self.virtual_wallets.get(seller_wallet_id)
        if seller_wallet:
            seller_wallet.balances[currency] += price

        # Transfer NFT
        success = self.transfer_nft(
            listing['nft_id'],
            seller_wallet_id,
            buyer_wallet_id,
            transfer_fee=0.05  # 5% marketplace fee
        )

        if success:
            listing['status'] = 'sold'
            listing['sold_at'] = time.time()
            listing['buyer_wallet'] = buyer_wallet_id

            # Update economic metrics
            self.economic_metrics['nft_market_volume'] += price
            self.economic_metrics['transaction_volume_24h'] += price

            self.logger.info(f"NFT {listing['nft_id']} purchased for {price} {currency.value}")
            return True

        return False

    def exchange_currency(self, from_wallet_id: str, from_currency: VirtualCurrency,
                         to_currency: VirtualCurrency, amount: float) -> bool:
        """Exchange virtual currencies.

        Args:
            from_wallet_id: Source wallet
            from_currency: Source currency
            to_currency: Target currency
            amount: Amount to exchange

        Returns:
            True if exchange successful
        """
        wallet = self.virtual_wallets.get(from_wallet_id)
        if not wallet:
            return False

        # Check balance
        if wallet.balances.get(from_currency, 0) < amount:
            return False

        # Get exchange rate
        exchange_rate = self.currency_exchange_rates.get((from_currency, to_currency), 1.0)
        exchanged_amount = amount * exchange_rate

        # Perform exchange
        wallet.balances[from_currency] -= amount
        wallet.balances[to_currency] = wallet.balances.get(to_currency, 0) + exchanged_amount

        # Record transaction
        transaction_record = {
            'transaction_id': str(uuid.uuid4()),
            'type': 'currency_exchange',
            'from_currency': from_currency.value,
            'to_currency': to_currency.value,
            'amount': amount,
            'exchanged_amount': exchanged_amount,
            'exchange_rate': exchange_rate,
            'timestamp': time.time()
        }

        wallet.transaction_history.append(transaction_record)

        self.logger.info(f"Exchanged {amount} {from_currency.value} to {exchanged_amount:.2f} {to_currency.value}")
        return True

    def reward_user_activity(self, user_id: str, activity_type: str,
                           reward_amount: float = 10.0) -> bool:
        """Reward user for metaverse activities.

        Args:
            user_id: User identifier
            activity_type: Type of activity
            reward_amount: Reward amount in METACOIN

        Returns:
            True if reward granted
        """
        wallet = self._find_wallet_by_owner(user_id)
        if not wallet:
            return False

        # Different rewards for different activities
        reward_multipliers = {
            'design_creation': 2.0,
            'quality_print': 1.5,
            'community_contribution': 1.2,
            'daily_login': 1.0
        }

        multiplier = reward_multipliers.get(activity_type, 1.0)
        actual_reward = reward_amount * multiplier

        wallet.balances[VirtualCurrency.METACOIN] += actual_reward

        # Record reward transaction
        transaction_record = {
            'transaction_id': str(uuid.uuid4()),
            'type': 'activity_reward',
            'activity_type': activity_type,
            'reward_amount': actual_reward,
            'multiplier': multiplier,
            'timestamp': time.time()
        }

        wallet.transaction_history.append(transaction_record)

        self.logger.info(f"Rewarded user {user_id} with {actual_reward} METACOIN for {activity_type}")
        return True

    def _find_wallet_by_owner(self, owner_id: str) -> Optional[VirtualWallet]:
        """Find wallet by owner ID."""
        for wallet in self.virtual_wallets.values():
            if wallet.owner_id == owner_id:
                return wallet
        return None

    def get_economic_indicators(self) -> Dict[str, Any]:
        """Get metaverse economic indicators.

        Returns:
            Economic indicators
        """
        return {
            'currency_circulation': self.economic_metrics['total_circulation'],
            'nft_market_activity': {
                'active_listings': len([l for l in self.active_listings if l['status'] == 'active']),
                'total_volume': self.economic_metrics['nft_market_volume'],
                '24h_volume': self.economic_metrics['transaction_volume_24h']
            },
            'user_engagement': {
                'active_wallets': len(self.virtual_wallets),
                'nft_owners': len(set(
                    asset.owner_id for asset in self.nft_assets.values()
                    if asset.owner_id
                )),
                'daily_active_users': self.economic_metrics['active_users']
            },
            'market_trends': self._calculate_market_trends()
        }

    def _calculate_market_trends(self) -> Dict[str, Any]:
        """Calculate market trends."""
        # Analyze recent transactions
        recent_transactions = [
            record for wallet in self.virtual_wallets.values()
            for record in wallet.transaction_history[-10:]  # Last 10 transactions per wallet
        ]

        trends = {
            'transaction_volume_trend': 'increasing',
            'popular_nft_categories': self._get_popular_categories(),
            'average_transaction_value': 25.0,  # Placeholder
            'market_volatility': 0.15  # Placeholder
        }

        return trends

    def _get_popular_categories(self) -> List[Dict[str, Any]]:
        """Get popular NFT categories."""
        category_counts = {}

        for nft in self.nft_assets.values():
            category = nft.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        # Sort by popularity
        popular_categories = [
            {'category': category, 'count': count}
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return popular_categories[:5]  # Top 5

    def get_wallet_balance(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet balance and holdings.

        Args:
            wallet_id: Wallet identifier

        Returns:
            Wallet information
        """
        wallet = self.virtual_wallets.get(wallet_id)
        if not wallet:
            return {'error': 'Wallet not found'}

        # Get NFT details
        nft_details = []
        for nft_id in wallet.nft_holdings:
            if nft_id in self.nft_assets:
                nft = self.nft_assets[nft_id]
                nft_details.append({
                    'nft_id': nft.nft_id,
                    'name': nft.name,
                    'category': nft.category.value,
                    'rarity': nft.rarity,
                    'utility_value': nft.utility_value
                })

        return {
            'wallet_id': wallet_id,
            'owner_id': wallet.owner_id,
            'balances': wallet.balances,
            'nft_holdings': nft_details,
            'transaction_count': len(wallet.transaction_history)
        }


class NFTMarketplace:
    """NFT marketplace for virtual assets."""

    def __init__(self, economy: MetaverseEconomy):
        """Initialize NFT marketplace.

        Args:
            economy: Metaverse economy instance
        """
        self.logger = logging.getLogger(__name__)
        self.economy = economy
        self.market_categories: Dict[NFTCategory, List[str]] = {}
        self.market_analytics: Dict[str, Any] = {}

    def create_market_category(self, category: NFTCategory, category_config: Dict[str, Any]):
        """Create a marketplace category.

        Args:
            category: NFT category
            category_config: Category configuration
        """
        self.market_categories[category] = category_config.get('featured_listings', [])

        self.logger.info(f"Created marketplace category: {category.value}")

    def get_featured_nfts(self, category: NFTCategory) -> List[Dict[str, Any]]:
        """Get featured NFTs in a category.

        Args:
            category: NFT category

        Returns:
            List of featured NFTs
        """
        featured_nft_ids = self.market_categories.get(category, [])
        featured_nfts = []

        for nft_id in featured_nft_ids:
            if nft_id in self.economy.nft_assets:
                nft = self.economy.nft_assets[nft_id]
                featured_nfts.append({
                    'nft_id': nft.nft_id,
                    'name': nft.name,
                    'description': nft.description,
                    'rarity': nft.rarity,
                    'utility_value': nft.utility_value,
                    'market_price': self._estimate_market_price(nft)
                })

        return featured_nfts

    def _estimate_market_price(self, nft: NFTAsset) -> float:
        """Estimate market price for an NFT."""
        # Simple price estimation based on rarity and utility
        base_price = 50.0  # METACOIN

        rarity_multipliers = {
            'common': 1.0,
            'uncommon': 1.5,
            'rare': 2.5,
            'legendary': 5.0
        }

        rarity_multiplier = rarity_multipliers.get(nft.rarity, 1.0)

        # Utility value bonus
        utility_bonus = 0.0
        for value in nft.utility_value.values():
            if isinstance(value, (int, float)):
                utility_bonus += value * 10

        return base_price * rarity_multiplier + utility_bonus

    def get_market_analytics(self) -> Dict[str, Any]:
        """Get marketplace analytics.

        Returns:
            Market analytics
        """
        return {
            'total_listings': len(self.economy.active_listings),
            'active_listings': len([l for l in self.economy.active_listings if l['status'] == 'active']),
            'total_volume': self.economy.economic_metrics['nft_market_volume'],
            'categories': {
                category.value: len(listings)
                for category, listings in self.market_categories.items()
            },
            'price_trends': self._calculate_price_trends()
        }

    def _calculate_price_trends(self) -> Dict[str, Any]:
        """Calculate NFT price trends."""
        # Analyze recent transactions
        recent_listings = [
            listing for listing in self.economy.active_listings
            if time.time() - listing['listed_at'] < 86400  # Last 24 hours
        ]

        if not recent_listings:
            return {'trend': 'stable', 'average_price': 0}

        total_volume = sum(listing['price'] for listing in recent_listings)
        average_price = total_volume / len(recent_listings)

        return {
            'trend': 'increasing' if average_price > 50 else 'decreasing' if average_price < 30 else 'stable',
            'average_price': average_price,
            'listing_count_24h': len(recent_listings)
        }


class VirtualAssetManager:
    """Manager for virtual assets and digital ownership."""

    def __init__(self):
        """Initialize virtual asset manager."""
        self.logger = logging.getLogger(__name__)
        self.asset_ownership: Dict[str, str] = {}  # asset_id -> owner_id
        self.asset_metadata: Dict[str, Dict[str, Any]] = {}
        self.royalty_distributions: Dict[str, List[Dict[str, Any]]] = {}

    def register_digital_asset(self, asset_id: str, asset_type: str,
                             creator_id: str, metadata: Dict[str, Any]) -> bool:
        """Register a digital asset.

        Args:
            asset_id: Asset identifier
            asset_type: Type of asset
            creator_id: Creator identifier
            metadata: Asset metadata

        Returns:
            True if registered successfully
        """
        self.asset_ownership[asset_id] = creator_id
        self.asset_metadata[asset_id] = {
            **metadata,
            'asset_type': asset_type,
            'creator_id': creator_id,
            'registered_at': time.time(),
            'usage_rights': metadata.get('usage_rights', 'personal')
        }

        self.logger.info(f"Registered digital asset: {asset_id} ({asset_type})")
        return True

    def transfer_asset_ownership(self, asset_id: str, new_owner_id: str,
                               transfer_terms: Dict[str, Any]) -> bool:
        """Transfer asset ownership.

        Args:
            asset_id: Asset identifier
            new_owner_id: New owner identifier
            transfer_terms: Transfer terms

        Returns:
            True if transfer successful
        """
        if asset_id not in self.asset_ownership:
            return False

        current_owner = self.asset_ownership[asset_id]

        # Process royalty distribution if applicable
        if 'royalty_percentage' in transfer_terms:
            royalty_amount = transfer_terms.get('sale_price', 0) * transfer_terms['royalty_percentage']
            self._distribute_royalty(asset_id, current_owner, royalty_amount)

        # Transfer ownership
        self.asset_ownership[asset_id] = new_owner_id

        self.logger.info(f"Transferred asset {asset_id} from {current_owner} to {new_owner_id}")
        return True

    def _distribute_royalty(self, asset_id: str, creator_id: str, royalty_amount: float):
        """Distribute royalty to creator."""
        if asset_id not in self.royalty_distributions:
            self.royalty_distributions[asset_id] = []

        royalty_record = {
            'creator_id': creator_id,
            'royalty_amount': royalty_amount,
            'distributed_at': time.time(),
            'distribution_method': 'automatic'
        }

        self.royalty_distributions[asset_id].append(royalty_record)

    def verify_asset_authenticity(self, asset_id: str) -> Dict[str, Any]:
        """Verify asset authenticity and ownership.

        Args:
            asset_id: Asset identifier

        Returns:
            Authenticity verification result
        """
        if asset_id not in self.asset_ownership:
            return {'authentic': False, 'error': 'Asset not registered'}

        asset_metadata = self.asset_metadata.get(asset_id, {})

        return {
            'authentic': True,
            'owner_id': self.asset_ownership[asset_id],
            'creator_id': asset_metadata.get('creator_id'),
            'registration_date': asset_metadata.get('registered_at'),
            'asset_type': asset_metadata.get('asset_type'),
            'usage_rights': asset_metadata.get('usage_rights')
        }


class MetaverseEconomyManager:
    """Main manager for metaverse economy operations."""

    def __init__(self):
        """Initialize metaverse economy manager."""
        self.logger = logging.getLogger(__name__)
        self.economy = MetaverseEconomy()
        self.marketplace = NFTMarketplace(self.economy)
        self.asset_manager = VirtualAssetManager()

        # Initialize marketplace categories
        self._initialize_marketplace()

    def _initialize_marketplace(self):
        """Initialize NFT marketplace categories."""
        for category in NFTCategory:
            self.marketplace.create_market_category(
                category,
                {'featured_listings': [], 'category_description': f'NFTs for {category.value}'}
            )

    def create_user_economy_profile(self, user_id: str) -> str:
        """Create economy profile for a user.

        Args:
            user_id: User identifier

        Returns:
            Wallet ID
        """
        return self.economy.create_virtual_wallet(user_id)

    def mint_design_nft(self, design_data: Dict[str, Any], creator_id: str) -> str:
        """Mint NFT for a design.

        Args:
            design_data: Design information
            creator_id: Creator identifier

        Returns:
            NFT ID
        """
        nft_metadata = {
            'design_hash': design_data.get('design_hash', ''),
            'design_complexity': design_data.get('complexity', 'medium'),
            'estimated_value': design_data.get('estimated_value', 100),
            'design_category': design_data.get('category', 'general')
        }

        return self.economy.mint_nft_asset(
            NFTCategory.DESIGN_BLUEPRINT,
            design_data.get('name', 'Unnamed Design'),
            design_data.get('description', 'Design blueprint'),
            creator_id,
            nft_metadata
        )

    def purchase_manufacturing_service(self, service_type: str,
                                     provider_id: str,
                                     buyer_wallet_id: str,
                                     service_cost: float) -> bool:
        """Purchase manufacturing service.

        Args:
            service_type: Type of manufacturing service
            provider_id: Service provider
            buyer_wallet_id: Buyer's wallet
            service_cost: Service cost

        Returns:
            True if purchase successful
        """
        wallet = self.economy.virtual_wallets.get(buyer_wallet_id)
        if not wallet:
            return False

        # Check balance
        if wallet.balances.get(VirtualCurrency.MANUFACTURE_CREDIT, 0) < service_cost:
            return False

        # Process payment
        wallet.balances[VirtualCurrency.MANUFACTURE_CREDIT] -= service_cost

        # Reward provider
        provider_wallet = self.economy._find_wallet_by_owner(provider_id)
        if provider_wallet:
            provider_wallet.balances[VirtualCurrency.MANUFACTURE_CREDIT] += service_cost * 0.9  # 10% platform fee

        return True

    def reward_design_contribution(self, user_id: str, contribution_type: str,
                                 impact_score: float) -> bool:
        """Reward user for design contributions.

        Args:
            user_id: User identifier
            contribution_type: Type of contribution
            impact_score: Impact score (0-1)

        Returns:
            True if reward granted
        """
        reward_amount = 10.0 + impact_score * 50  # 10-60 METACOIN based on impact
        return self.economy.reward_user_activity(user_id, contribution_type, reward_amount)

    def get_metaverse_economy_status(self) -> Dict[str, Any]:
        """Get metaverse economy status.

        Returns:
            Economy status
        """
        economic_indicators = self.economy.get_economic_indicators()
        market_analytics = self.marketplace.get_market_analytics()

        return {
            'economic_indicators': economic_indicators,
            'market_analytics': market_analytics,
            'supported_currencies': [currency.value for currency in VirtualCurrency],
            'nft_categories': [category.value for category in NFTCategory],
            'total_assets': len(self.economy.nft_assets),
            'marketplace_activity': {
                'active_listings': len([l for l in self.economy.active_listings if l['status'] == 'active']),
                'recent_sales': len([l for l in self.economy.active_listings if l['status'] == 'sold'])
            }
        }


# Global metaverse economy manager
metaverse_economy_manager = MetaverseEconomyManager()


# Convenience functions
def create_metaverse_wallet(user_id: str) -> str:
    """Create a metaverse wallet for a user."""
    return metaverse_economy_manager.create_user_economy_profile(user_id)


def mint_design_nft(design_data: Dict[str, Any], creator_id: str) -> str:
    """Mint NFT for a design."""
    return metaverse_economy_manager.mint_design_nft(design_data, creator_id)


def reward_design_activity(user_id: str, activity_type: str, impact_score: float = 0.5) -> bool:
    """Reward user for design activities."""
    return metaverse_economy_manager.reward_design_contribution(user_id, activity_type, impact_score)


def get_metaverse_economy_status() -> Dict[str, Any]:
    """Get metaverse economy status."""
    return metaverse_economy_manager.get_metaverse_economy_status()
