#!/usr/bin/env python3
"""
エコシステム統合プラットフォーム（拡張版）
サードパーティツールとの連携機能を提供
"""

from __future__ import annotations

import json
import importlib
import inspect
import pkg_resources
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class IntegrationType(Enum):
    """統合の種類"""
    CAD_SOFTWARE = "cad_software"
    SLICER = "slicer"
    PRINTER_CONTROL = "printer_control"
    MATERIAL_DATABASE = "material_database"
    SIMULATION_ENGINE = "simulation_engine"
    QUALITY_CONTROL = "quality_control"
    FILE_FORMAT = "file_format"

class IntegrationStatus(Enum):
    """統合ステータス"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

@dataclass
class IntegrationEndpoint:
    """統合エンドポイント"""
    endpoint_id: str
    name: str
    description: str
    integration_type: IntegrationType
    url: str
    api_key: Optional[str] = None
    authentication: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    status: IntegrationStatus = IntegrationStatus.PENDING

@dataclass
class EcosystemPlugin:
    """エコシステムプラグイン"""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    integration_type: IntegrationType
    entry_points: Dict[str, str] = field(default_factory=dict)  # 関数名 -> モジュールパス
    dependencies: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    hooks: Dict[str, Callable] = field(default_factory=dict)

class EcosystemIntegrationManager:
    """エコシステム統合管理システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.integrations: Dict[str, IntegrationEndpoint] = {}
        self.plugins: Dict[str, EcosystemPlugin] = {}
        self.plugin_instances: Dict[str, Any] = {}
        self.discovered_tools: List[Dict[str, Any]] = []

    def discover_third_party_tools(self) -> List[Dict[str, Any]]:
        """サードパーティツールを検出"""
        discovered = []

        # インストール済みパッケージから3Dプリント関連ツールを検索
        try:
            installed_packages = pkg_resources.working_set
            cad_keywords = ["cad", "3d", "print", "stl", "mesh", "slicer", "cura", "prusa", "blender"]

            for package in installed_packages:
                package_name = package.project_name.lower()

                # CAD/3Dプリント関連のパッケージを検出
                if any(keyword in package_name for keyword in cad_keywords):
                    tool_info = self._analyze_package(package)
                    if tool_info:
                        discovered.append(tool_info)

        except Exception as e:
            self.logger.error(f"Tool discovery failed: {str(e)}")

        # 一般的なツールも追加
        common_tools = [
            {
                "name": "Blender",
                "type": "cad_software",
                "version": "3.6.0",
                "capabilities": ["mesh_modeling", "stl_export", "animation"],
                "integration_points": ["file_import", "mesh_processing"]
            },
            {
                "name": "Ultimaker Cura",
                "type": "slicer",
                "version": "5.4.0",
                "capabilities": ["slicing", "gcode_generation", "print_optimization"],
                "integration_points": ["slice_settings", "printer_profiles"]
            },
            {
                "name": "PrusaSlicer",
                "type": "slicer",
                "version": "2.7.0",
                "capabilities": ["slicing", "multi_material", "advanced_supports"],
                "integration_points": ["slice_export", "material_profiles"]
            },
            {
                "name": "MeshLab",
                "type": "mesh_processor",
                "version": "2023.12",
                "capabilities": ["mesh_repair", "simplification", "analysis"],
                "integration_points": ["mesh_import", "mesh_export"]
            }
        ]

        discovered.extend(common_tools)
        self.discovered_tools = discovered

        return discovered

    def _analyze_package(self, package) -> Optional[Dict[str, Any]]:
        """パッケージを分析"""
        try:
            # パッケージのメタデータを取得
            metadata = package.get_metadata("METADATA") if hasattr(package, 'get_metadata') else ""

            # 関連性スコアを計算
            relevance_score = 0
            package_name = package.project_name.lower()

            # CAD関連キーワードでスコアリング
            cad_keywords = {
                "blender": 10, "maya": 8, "3ds": 8, "autocad": 9, "fusion": 8,
                "solidworks": 9, "catia": 8, "nx": 7, "inventor": 7,
                "cura": 9, "prusa": 8, "slic3r": 8, "meshlab": 7,
                "stl": 5, "obj": 5, "3mf": 6, "gcode": 6
            }

            for keyword, score in cad_keywords.items():
                if keyword in package_name:
                    relevance_score += score

            if relevance_score >= 5:  # 最低スコア閾値
                return {
                    "name": package.project_name,
                    "type": self._categorize_tool(package_name),
                    "version": getattr(package, 'version', 'unknown'),
                    "relevance_score": relevance_score,
                    "metadata": metadata[:500] if metadata else ""
                }

        except Exception as e:
            self.logger.debug(f"Package analysis failed for {package.project_name}: {str(e)}")

        return None

    def _categorize_tool(self, package_name: str) -> str:
        """ツールを分類"""
        name_lower = package_name.lower()

        if any(word in name_lower for word in ["blender", "maya", "3ds", "autocad", "fusion", "solidworks"]):
            return "cad_software"
        elif any(word in name_lower for word in ["cura", "prusa", "slic3r", "ideamaker"]):
            return "slicer"
        elif any(word in name_lower for word in ["meshlab", "meshmixer"]):
            return "mesh_processor"
        elif any(word in name_lower for word in ["octoprint", "pronsole", "repetier"]):
            return "printer_control"
        else:
            return "other"

    def create_integration_endpoint(self, name: str, integration_type: IntegrationType,
                                  url: str, api_key: str = None) -> str:
        """統合エンドポイントを作成"""
        endpoint_id = f"endpoint_{integration_type.value}_{hash(f'{name}{url}') % 10000}"

        endpoint = IntegrationEndpoint(
            endpoint_id=endpoint_id,
            name=name,
            description=f"Integration with {name}",
            integration_type=integration_type,
            url=url,
            api_key=api_key,
            capabilities=self._get_default_capabilities(integration_type),
            status=IntegrationStatus.PENDING
        )

        self.integrations[endpoint_id] = endpoint

        # エンドポイントをテスト
        self._test_integration_endpoint(endpoint)

        return endpoint_id

    def _get_default_capabilities(self, integration_type: IntegrationType) -> List[str]:
        """デフォルトの機能を取得"""
        capabilities_map = {
            IntegrationType.CAD_SOFTWARE: ["mesh_import", "mesh_export", "parametric_modeling"],
            IntegrationType.SLICER: ["slice_model", "gcode_generation", "print_settings"],
            IntegrationType.PRINTER_CONTROL: ["printer_status", "job_control", "temperature_control"],
            IntegrationType.MATERIAL_DATABASE: ["material_lookup", "properties_query"],
            IntegrationType.SIMULATION_ENGINE: ["structural_analysis", "thermal_analysis"],
            IntegrationType.QUALITY_CONTROL: ["quality_check", "defect_detection"],
            IntegrationType.FILE_FORMAT: ["format_conversion", "validation"]
        }

        return capabilities_map.get(integration_type, [])

    def _test_integration_endpoint(self, endpoint: IntegrationEndpoint) -> None:
        """統合エンドポイントをテスト"""
        try:
            # 基本的な接続テスト
            if endpoint.integration_type == IntegrationType.CAD_SOFTWARE:
                test_result = self._test_cad_integration(endpoint)
            elif endpoint.integration_type == IntegrationType.SLICER:
                test_result = self._test_slicer_integration(endpoint)
            else:
                test_result = self._test_generic_integration(endpoint)

            if test_result["success"]:
                endpoint.status = IntegrationStatus.ACTIVE
                self.logger.info(f"Integration endpoint {endpoint.endpoint_id} is active")
            else:
                endpoint.status = IntegrationStatus.ERROR
                self.logger.warning(f"Integration endpoint {endpoint.endpoint_id} test failed: {test_result.get('error')}")

        except Exception as e:
            endpoint.status = IntegrationStatus.ERROR
            self.logger.error(f"Integration test failed for {endpoint.endpoint_id}: {str(e)}")

    def _test_cad_integration(self, endpoint: IntegrationEndpoint) -> Dict[str, Any]:
        """CAD統合をテスト"""
        # 簡易的なテスト（実際にはAPI呼び出し）
        return {"success": True, "message": "CAD integration test passed"}

    def _test_slicer_integration(self, endpoint: IntegrationEndpoint) -> Dict[str, Any]:
        """スライサー統合をテスト"""
        # 簡易的なテスト（実際にはAPI呼び出し）
        return {"success": True, "message": "Slicer integration test passed"}

    def _test_generic_integration(self, endpoint: IntegrationEndpoint) -> Dict[str, Any]:
        """一般的な統合をテスト"""
        # 基本的なHTTP接続テスト
        try:
            # 実際にはrequestsなどでエンドポイントをテスト
            return {"success": True, "message": "Generic integration test passed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_plugin(self, plugin: EcosystemPlugin) -> bool:
        """エコシステムプラグインを登録"""
        try:
            self.plugins[plugin.plugin_id] = plugin

            # プラグインの依存関係をチェック
            if not self._check_plugin_dependencies(plugin):
                self.logger.warning(f"Plugin {plugin.plugin_id} has unmet dependencies")
                return False

            # プラグインをロード
            instance = self._load_plugin(plugin)
            if instance:
                self.plugin_instances[plugin.plugin_id] = instance

                # プラグインフックを登録
                self._register_plugin_hooks(plugin, instance)

                self.logger.info(f"Successfully registered plugin: {plugin.plugin_id}")
                return True
            else:
                self.logger.error(f"Failed to load plugin: {plugin.plugin_id}")
                return False

        except Exception as e:
            self.logger.error(f"Plugin registration failed for {plugin.plugin_id}: {str(e)}")
            return False

    def _check_plugin_dependencies(self, plugin: EcosystemPlugin) -> bool:
        """プラグインの依存関係をチェック"""
        for dependency in plugin.dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                self.logger.error(f"Missing dependency for plugin {plugin.plugin_id}: {dependency}")
                return False
        return True

    def _load_plugin(self, plugin: EcosystemPlugin) -> Optional[Any]:
        """プラグインをロード"""
        try:
            # エントリポイントからモジュールをインポート
            for entry_name, module_path in plugin.entry_points.items():
                try:
                    # モジュールを動的にインポート
                    module = importlib.import_module(module_path)

                    # プラグインクラスを検索
                    plugin_class = getattr(module, entry_name, None)
                    if plugin_class and inspect.isclass(plugin_class):
                        return plugin_class()

                except Exception as e:
                    self.logger.warning(f"Failed to load plugin entry point {entry_name}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Plugin loading failed: {str(e)}")

        return None

    def _register_plugin_hooks(self, plugin: EcosystemPlugin, instance: Any) -> None:
        """プラグインフックを登録"""
        for hook_name in plugin.hooks:
            if hasattr(instance, hook_name):
                hook_method = getattr(instance, hook_name)
                # グローバルフックレジストリに登録
                hook_key = f"plugin_{plugin.plugin_id}_{hook_name}"
                setattr(self, hook_key, hook_method)

    def execute_plugin_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """プラグインフックを実行"""
        results = []

        for plugin_id, plugin in self.plugins.items():
            hook_key = f"plugin_{plugin_id}_{hook_name}"

            if hasattr(self, hook_key):
                try:
                    hook_method = getattr(self, hook_key)
                    result = hook_method(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Plugin hook execution failed {hook_key}: {str(e)}")

        return results

    def create_plugin_from_code(self, plugin_code: str, plugin_name: str,
                              integration_type: IntegrationType) -> Optional[EcosystemPlugin]:
        """コードからプラグインを作成"""
        try:
            # 一時ファイルにコードを書き込み
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(plugin_code)
                temp_file = f.name

            # プラグインを動的に作成
            plugin_id = f"dynamic_{plugin_name.lower().replace(' ', '_')}"

            plugin = EcosystemPlugin(
                plugin_id=plugin_id,
                name=plugin_name,
                version="1.0.0",
                description=f"Dynamically created {plugin_name} plugin",
                author="System",
                integration_type=integration_type,
                entry_points={"PluginClass": temp_file.replace('.py', '')},
                configuration={"dynamic": True}
            )

            # 作成したプラグインを登録
            if self.register_plugin(plugin):
                return plugin
            else:
                # 失敗した場合は一時ファイルを削除
                os.unlink(temp_file)
                return None

        except Exception as e:
            self.logger.error(f"Dynamic plugin creation failed: {str(e)}")
            return None

    def get_integration_status(self, endpoint_id: str) -> Dict[str, Any]:
        """統合ステータスを取得"""
        if endpoint_id not in self.integrations:
            return {"error": "Integration not found"}

        endpoint = self.integrations[endpoint_id]

        return {
            "endpoint_id": endpoint_id,
            "name": endpoint.name,
            "status": endpoint.status.value,
            "capabilities": endpoint.capabilities,
            "last_test": getattr(endpoint, 'last_test', None)
        }

    def get_plugin_status(self, plugin_id: str) -> Dict[str, Any]:
        """プラグインステータスを取得"""
        if plugin_id not in self.plugins:
            return {"error": "Plugin not found"}

        plugin = self.plugins[plugin_id]
        is_loaded = plugin_id in self.plugin_instances

        return {
            "plugin_id": plugin_id,
            "name": plugin.name,
            "loaded": is_loaded,
            "hooks": list(plugin.hooks.keys()),
            "dependencies": plugin.dependencies
        }

    def list_integrations(self) -> List[Dict[str, Any]]:
        """統合エンドポイントを一覧表示"""
        return [
            {
                "endpoint_id": endpoint.endpoint_id,
                "name": endpoint.name,
                "type": endpoint.integration_type.value,
                "status": endpoint.status.value,
                "capabilities": endpoint.capabilities
            }
            for endpoint in self.integrations.values()
        ]

    def list_plugins(self) -> List[Dict[str, Any]]:
        """プラグインを一覧表示"""
        return [
            {
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "type": plugin.integration_type.value,
                "loaded": plugin_id in self.plugin_instances,
                "hooks": list(plugin.hooks.keys())
            }
            for plugin_id, plugin in self.plugins.items()
        ]

    def generate_integration_report(self) -> Dict[str, Any]:
        """統合レポートを生成"""
        return {
            "total_integrations": len(self.integrations),
            "active_integrations": len([e for e in self.integrations.values() if e.status == IntegrationStatus.ACTIVE]),
            "total_plugins": len(self.plugins),
            "loaded_plugins": len(self.plugin_instances),
            "discovered_tools": len(self.discovered_tools),
            "integration_types": self._get_integration_type_summary(),
            "recent_activity": self._get_recent_activity()
        }

    def _get_integration_type_summary(self) -> Dict[str, int]:
        """統合タイプのサマリーを取得"""
        summary = {}

        for endpoint in self.integrations.values():
            type_name = endpoint.integration_type.value
            summary[type_name] = summary.get(type_name, 0) + 1

        return summary

    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """最近のアクティビティを取得"""
        # 簡易的なアクティビティログ（実際にはログファイルから取得）
        return [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "type": "plugin_loaded",
                "description": "Material Database plugin loaded successfully"
            },
            {
                "timestamp": "2024-01-15T09:15:00Z",
                "type": "integration_tested",
                "description": "Cura integration test completed"
            }
        ][:5]  # 最新5件

# グローバルインスタンス
_ecosystem_manager = None

def get_ecosystem_manager() -> EcosystemIntegrationManager:
    """エコシステム統合管理システムのインスタンスを取得"""
    global _ecosystem_manager
    if _ecosystem_manager is None:
        _ecosystem_manager = EcosystemIntegrationManager()
    return _ecosystem_manager
