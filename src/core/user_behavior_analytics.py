#!/usr/bin/env python3
"""
ユーザー行動分析とレコメンダーシステム
パーソナライズドな動的提案とガイド機能を提供
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, Counter
import hashlib

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class UserActionType(Enum):
    """ユーザー行動の種類"""
    FILE_UPLOAD = "file_upload"
    MESH_VALIDATION = "mesh_validation"
    MESH_REPAIR = "mesh_repair"
    PARAMETER_CHANGE = "parameter_change"
    MATERIAL_SELECTION = "material_selection"
    SLICING = "slicing"
    PREVIEW = "preview"
    EXPORT = "export"
    ERROR_ENCOUNTERED = "error_encountered"
    HELP_REQUESTED = "help_requested"
    SETTING_MODIFIED = "setting_modified"

class UserSkillLevel(Enum):
    """ユーザースキルレベル"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class UserAction:
    """ユーザー行動データ"""
    user_id: str
    action_type: UserActionType
    timestamp: float
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[str] = None  # "success", "failure", "cancelled"

@dataclass
class UserProfile:
    """ユーザープロファイル"""
    user_id: str
    skill_level: UserSkillLevel = UserSkillLevel.BEGINNER
    preferences: Dict[str, Any] = field(default_factory=dict)
    usage_patterns: Dict[str, Any] = field(default_factory=dict)
    error_patterns: List[str] = field(default_factory=list)
    successful_actions: List[str] = field(default_factory=list)
    last_activity: float = 0.0
    total_sessions: int = 0
    average_session_duration: float = 0.0

@dataclass
class PersonalizedRecommendation:
    """パーソナライズドな推奨事項"""
    recommendation_id: str
    user_id: str
    recommendation_type: str
    title: str
    description: str
    confidence: float
    priority: int
    action_items: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None

class UserBehaviorAnalyzer:
    """ユーザー行動分析システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.user_profiles: Dict[str, UserProfile] = {}
        self.action_history: List[UserAction] = []
        self.max_history_size = 10000  # 履歴サイズ制限

    def record_action(self, user_id: str, action_type: UserActionType,
                     session_id: str, metadata: Dict[str, Any] = None,
                     outcome: str = None) -> None:
        """ユーザー行動を記録"""
        action = UserAction(
            user_id=user_id,
            action_type=action_type,
            timestamp=time.time(),
            session_id=session_id,
            metadata=metadata or {},
            outcome=outcome
        )

        self.action_history.append(action)

        # 履歴サイズを制限
        if len(self.action_history) > self.max_history_size:
            self.action_history = self.action_history[-self.max_history_size:]

        # ユーザープロファイルを更新
        self._update_user_profile(user_id, action)

        self.logger.debug(f"Recorded action: {action_type.value} for user {user_id}")

    def _update_user_profile(self, user_id: str, action: UserAction) -> None:
        """ユーザープロファイルを更新"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)

        profile = self.user_profiles[user_id]

        # 最終アクティビティを更新
        profile.last_activity = action.timestamp

        # 行動パターンを分析
        action_key = action.action_type.value

        if action_key not in profile.usage_patterns:
            profile.usage_patterns[action_key] = {
                "count": 0,
                "success_rate": 0.0,
                "avg_metadata": {}
            }

        pattern = profile.usage_patterns[action_key]
        pattern["count"] += 1

        # 成功率を計算
        if action.outcome:
            success_count = pattern.get("success_count", 0)
            if action.outcome == "success":
                success_count += 1
            pattern["success_count"] = success_count
            pattern["success_rate"] = success_count / pattern["count"]

        # メタデータを蓄積
        for key, value in action.metadata.items():
            if key not in pattern["avg_metadata"]:
                pattern["avg_metadata"][key] = []
            pattern["avg_metadata"][key].append(value)

        # スキルレベルを推定
        self._estimate_skill_level(profile)

    def _estimate_skill_level(self, profile: UserProfile) -> None:
        """スキルレベルを推定"""
        # 行動パターンに基づくスキルレベル推定
        advanced_actions = ["mesh_repair", "parameter_change", "material_selection"]
        total_actions = sum([pattern["count"] for pattern in profile.usage_patterns.values()])
        advanced_action_count = sum([
            profile.usage_patterns.get(action, {}).get("count", 0)
            for action in advanced_actions
        ])

        # 成功率と行動の多様性に基づいてスキルレベルを決定
        if total_actions < 5:
            profile.skill_level = UserSkillLevel.BEGINNER
        elif advanced_action_count / max(total_actions, 1) > 0.3:
            # 上級行動が多い場合
            success_rate = sum([
                pattern.get("success_rate", 0) * pattern["count"]
                for pattern in profile.usage_patterns.values()
            ]) / max(total_actions, 1)

            if success_rate > 0.8:
                profile.skill_level = UserSkillLevel.EXPERT
            else:
                profile.skill_level = UserSkillLevel.ADVANCED
        else:
            profile.skill_level = UserSkillLevel.INTERMEDIATE

    def analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """ユーザー行動を分析"""
        if user_id not in self.user_profiles:
            return {"error": "User profile not found"}

        profile = self.user_profiles[user_id]

        # ユーザーの行動履歴を取得
        user_actions = [action for action in self.action_history if action.user_id == user_id]

        # 行動パターンの分析
        action_patterns = self._analyze_action_patterns(user_actions)

        # エラーパターンの分析
        error_patterns = self._analyze_error_patterns(user_actions)

        # 成功パターンの分析
        success_patterns = self._analyze_success_patterns(user_actions)

        return {
            "user_id": user_id,
            "skill_level": profile.skill_level.value,
            "total_actions": len(user_actions),
            "last_activity": profile.last_activity,
            "action_patterns": action_patterns,
            "error_patterns": error_patterns,
            "success_patterns": success_patterns,
            "preferences": profile.preferences
        }

    def _analyze_action_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """行動パターンを分析"""
        if not actions:
            return {}

        # 行動の頻度分布
        action_counts = Counter(action.action_type.value for action in actions)

        # 時間帯別の行動パターン
        hourly_patterns = defaultdict(int)
        for action in actions:
            hour = time.strftime("%H", time.localtime(action.timestamp))
            hourly_patterns[hour] += 1

        # セッション継続時間の分析
        session_durations = self._analyze_session_durations(actions)

        return {
            "frequent_actions": dict(action_counts.most_common(5)),
            "hourly_patterns": dict(hourly_patterns),
            "session_durations": session_durations,
            "unique_action_types": len(set(action.action_type.value for action in actions))
        }

    def _analyze_session_durations(self, actions: List[UserAction]) -> Dict[str, float]:
        """セッション継続時間を分析"""
        session_times = defaultdict(list)

        for action in actions:
            session_times[action.session_id].append(action.timestamp)

        durations = {}
        for session_id, timestamps in session_times.items():
            if len(timestamps) > 1:
                duration = max(timestamps) - min(timestamps)
                durations[session_id] = duration

        if durations:
            return {
                "average": sum(durations.values()) / len(durations),
                "median": sorted(durations.values())[len(durations) // 2],
                "max": max(durations.values()),
                "min": min(durations.values())
            }

        return {"average": 0, "median": 0, "max": 0, "min": 0}

    def _analyze_error_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """エラーパターンを分析"""
        error_actions = [action for action in actions if action.outcome == "failure"]

        if not error_actions:
            return {"error_count": 0, "error_rate": 0.0}

        # エラーの種類別分布
        error_types = Counter(action.metadata.get("error_type", "unknown") for action in error_actions)

        # 頻発するエラー
        frequent_errors = dict(error_types.most_common(3))

        return {
            "error_count": len(error_actions),
            "error_rate": len(error_actions) / len(actions),
            "frequent_errors": frequent_errors,
            "recent_errors": [
                {
                    "action": action.action_type.value,
                    "timestamp": action.timestamp,
                    "error_type": action.metadata.get("error_type", "unknown")
                }
                for action in error_actions[-5:]  # 最新5件
            ]
        }

    def _analyze_success_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """成功パターンを分析"""
        success_actions = [action for action in actions if action.outcome == "success"]

        if not success_actions:
            return {"success_count": 0, "success_rate": 0.0}

        # 成功行動の分布
        success_types = Counter(action.action_type.value for action in success_actions)

        return {
            "success_count": len(success_actions),
            "success_rate": len(success_actions) / len(actions),
            "successful_actions": dict(success_types.most_common(5))
        }

class PersonalizedRecommender:
    """パーソナライズドレコメンダーシステム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.recommendation_cache: Dict[str, List[PersonalizedRecommendation]] = {}

    def get_personalized_recommendations(self, user_id: str) -> List[PersonalizedRecommendation]:
        """パーソナライズドな推奨事項を取得"""
        # キャッシュチェック
        cache_key = f"user_{user_id}"
        if cache_key in self.recommendation_cache:
            cached_recs = self.recommendation_cache[cache_key]
            # 有効期限内のものをフィルタリング
            current_time = time.time()
            valid_recs = [rec for rec in cached_recs if not rec.expires_at or rec.expires_at > current_time]
            if valid_recs:
                return valid_recs

        # 新しい推奨事項を生成
        recommendations = []

        # ユーザー行動分析に基づく推奨
        behavior_analysis = self.behavior_analyzer.analyze_user_behavior(user_id)

        if behavior_analysis.get("skill_level") == UserSkillLevel.BEGINNER.value:
            recommendations.extend(self._get_beginner_recommendations(user_id, behavior_analysis))

        # エラーパターンに基づく推奨
        error_patterns = behavior_analysis.get("error_patterns", {})
        if error_patterns.get("error_rate", 0) > 0.3:  # エラー率が高い場合
            recommendations.extend(self._get_error_reduction_recommendations(user_id, error_patterns))

        # 成功パターンに基づく推奨
        success_patterns = behavior_analysis.get("success_patterns", {})
        if success_patterns.get("success_rate", 0) > 0.8:  # 成功率が高い場合
            recommendations.extend(self._get_advanced_feature_recommendations(user_id, success_patterns))

        # 優先度でソート
        recommendations.sort(key=lambda x: x.priority, reverse=True)

        # 上位5件に制限
        recommendations = recommendations[:5]

        # キャッシュに保存（1時間有効）
        self.recommendation_cache[cache_key] = recommendations

        return recommendations

    def _get_beginner_recommendations(self, user_id: str, behavior_analysis: Dict[str, Any]) -> List[PersonalizedRecommendation]:
        """初心者向けの推奨事項"""
        recommendations = []

        # ガイド付きワークフローの推奨
        if "file_upload" in behavior_analysis.get("action_patterns", {}).get("frequent_actions", {}):
            recommendations.append(PersonalizedRecommendation(
                recommendation_id=f"rec_{user_id}_guided_workflow",
                user_id=user_id,
                recommendation_type="feature_suggestion",
                title=_("ガイド付きワークフローを試してください", "Try the Guided Workflow"),
                description=_("初心者向けのステップバイステップガイドで簡単にモデルを作成できます", "Step-by-step guided workflow makes model creation easy for beginners"),
                confidence=0.9,
                priority=10,
                action_items=[
                    _("ガイド付きワークフローを開始する", "Start guided workflow"),
                    _("テンプレートから選択する", "Choose from templates"),
                    _("パラメータを入力する", "Enter parameters")
                ],
                related_features=["guided_workflow_engine"]
            ))

        # ビジュアルプログラミングの推奨
        recommendations.append(PersonalizedRecommendation(
            recommendation_id=f"rec_{user_id}_visual_programming",
            user_id=user_id,
            recommendation_type="feature_suggestion",
            title=_("ビジュアルプログラミングブロックを試してください", "Try Visual Programming Blocks"),
            description=_("ドラッグ&ドロップで簡単にデザインを作成できます", "Create designs easily with drag-and-drop blocks"),
            confidence=0.8,
            priority=9,
            action_items=[
                _("ブロックパレットを開く", "Open block palette"),
                _("ブロックをキャンバスに配置", "Place blocks on canvas"),
                _("ブロックを接続してプログラムを作成", "Connect blocks to create program")
            ],
            related_features=["visual_programming_engine"]
        ))

        return recommendations

    def _get_error_reduction_recommendations(self, user_id: str, error_patterns: Dict[str, Any]) -> List[PersonalizedRecommendation]:
        """エラー低減のための推奨事項"""
        recommendations = []

        frequent_errors = error_patterns.get("frequent_errors", {})

        if "validation" in str(frequent_errors):
            recommendations.append(PersonalizedRecommendation(
                recommendation_id=f"rec_{user_id}_validation_help",
                user_id=user_id,
                recommendation_type="troubleshooting",
                title=_("メッシュ検証エラーを解決しましょう", "Let's Fix Mesh Validation Errors"),
                description=_("メッシュの問題を検出して自動的に修復できます", "Detect and automatically repair mesh issues"),
                confidence=0.8,
                priority=8,
                action_items=[
                    _("メッシュ検証ツールを開く", "Open mesh validation tool"),
                    _("エラーを確認する", "Review detected errors"),
                    _("自動修復を試す", "Try automatic repair")
                ],
                related_features=["ai_mesh_repair"]
            ))

        if "material" in str(frequent_errors):
            recommendations.append(PersonalizedRecommendation(
                recommendation_id=f"rec_{user_id}_material_guide",
                user_id=user_id,
                recommendation_type="guidance",
                title=_("マテリアル選択ガイドを確認してください", "Check Material Selection Guide"),
                description=_("プリンターと用途に適したマテリアルを選択しましょう", "Choose materials suitable for your printer and application"),
                confidence=0.7,
                priority=7,
                action_items=[
                    _("マテリアルデータベースを閲覧", "Browse material database"),
                    _("互換性を確認する", "Check compatibility"),
                    _("テストプリントを推奨", "Recommend test prints")
                ],
                related_features=["materials"]
            ))

        return recommendations

    def _get_advanced_feature_recommendations(self, user_id: str, success_patterns: Dict[str, Any]) -> List[PersonalizedRecommendation]:
        """上級機能の推奨事項"""
        recommendations = []

        # 複合マテリアルシミュレーションの推奨
        recommendations.append(PersonalizedRecommendation(
            recommendation_id=f"rec_{user_id}_multi_material",
            user_id=user_id,
            recommendation_type="advanced_feature",
            title=_("複合マテリアルプリントを試してください", "Try Multi-Material Printing"),
            description=_("複数のマテリアルを使った高度なプリントが可能です", "Advanced printing with multiple materials"),
            confidence=0.6,
            priority=6,
            action_items=[
                _("マテリアルシミュレーションを実行", "Run material simulation"),
                _("互換性を確認する", "Check material compatibility"),
                _("高度な設定を調整する", "Adjust advanced settings")
            ],
            related_features=["multi_material_simulator"]
        ))

        # クラウドコラボレーションの推奨
        recommendations.append(PersonalizedRecommendation(
            recommendation_id=f"rec_{user_id}_collaboration",
            user_id=user_id,
            recommendation_type="collaboration",
            title=_("クラウドコラボレーションを活用してください", "Utilize Cloud Collaboration"),
            description=_("チームメンバーとリアルタイムで共同作業ができます", "Collaborate with team members in real-time"),
            confidence=0.7,
            priority=7,
            action_items=[
                _("プロジェクトを作成する", "Create a project"),
                _("メンバーを招待する", "Invite team members"),
                _("リアルタイム編集を試す", "Try real-time editing")
            ],
            related_features=["enhanced_cloud_collaboration"]
        ))

        return recommendations

    def record_recommendation_interaction(self, user_id: str, recommendation_id: str,
                                        interaction: str, metadata: Dict[str, Any] = None) -> None:
        """推奨事項とのインタラクションを記録"""
        # インタラクションをログに記録（実際にはデータベースに保存）
        self.logger.info(f"User {user_id} interacted with recommendation {recommendation_id}: {interaction}")

        # 推奨事項の効果を測定してアルゴリズムを改善
        if metadata:
            self._update_recommendation_effectiveness(recommendation_id, interaction, metadata)

    def _update_recommendation_effectiveness(self, recommendation_id: str,
                                           interaction: str, metadata: Dict[str, Any]) -> None:
        """推奨事項の効果を更新"""
        # 簡易的な効果測定（実際には機械学習モデルで改善）
        if interaction == "accepted" and metadata.get("success", False):
            # 成功した場合のスコアを向上
            pass
        elif interaction == "rejected":
            # 拒否された場合のスコアを低下
            pass

    def clear_user_cache(self, user_id: str) -> None:
        """ユーザーのキャッシュをクリア"""
        cache_key = f"user_{user_id}"
        if cache_key in self.recommendation_cache:
            del self.recommendation_cache[cache_key]
            self.logger.info(f"Cleared recommendation cache for user {user_id}")

# グローバルインスタンス
_user_behavior_analyzer = None
_personalized_recommender = None

def get_user_behavior_analyzer() -> UserBehaviorAnalyzer:
    """ユーザー行動分析システムのインスタンスを取得"""
    global _user_behavior_analyzer
    if _user_behavior_analyzer is None:
        _user_behavior_analyzer = UserBehaviorAnalyzer()
    return _user_behavior_analyzer

def get_personalized_recommender() -> PersonalizedRecommender:
    """パーソナライズドレコメンダーシステムのインスタンスを取得"""
    global _personalized_recommender
    if _personalized_recommender is None:
        _personalized_recommender = PersonalizedRecommender()
    return _personalized_recommender
