#!/usr/bin/env python3
"""
最新の統合開発環境システム
VS Codeエクステンションとプラグインシステムを提供
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class ExtensionType(Enum):
    """エクステンションの種類"""
    LANGUAGE_SERVER = "language_server"
    DEBUGGER = "debugger"
    LINTER = "linter"
    FORMATTER = "formatter"
    SNIPPET_PROVIDER = "snippet_provider"
    COMMAND_PROVIDER = "command_provider"
    VIEW_PROVIDER = "view_provider"

class PluginType(Enum):
    """プラグインの種類"""
    MESH_PROCESSOR = "mesh_processor"
    MATERIAL_PROVIDER = "material_provider"
    PRINTER_DRIVER = "printer_driver"
    EXPORT_FILTER = "export_filter"
    IMPORT_FILTER = "import_filter"
    VALIDATION_RULE = "validation_rule"
    VISUALIZATION = "visualization"

@dataclass
class VSCODEExtension:
    """VS Codeエクステンション"""
    id: str
    name: str
    description: str
    version: str
    publisher: str
    extension_type: ExtensionType
    languages: List[str] = field(default_factory=list)
    activation_events: List[str] = field(default_factory=list)
    contributes: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)

@dataclass
class CADPlugin:
    """CADプラグイン"""
    id: str
    name: str
    description: str
    version: str
    plugin_type: PluginType
    author: str
    entry_point: str  # Pythonモジュールパス
    configuration: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    hooks: Dict[str, str] = field(default_factory=dict)  # イベントフック

class IDEIntegrationManager:
    """統合開発環境統合管理システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.extensions: Dict[str, VSCODEExtension] = {}
        self.plugins: Dict[str, CADPlugin] = {}
        self.plugin_registry: Dict[str, Any] = {}

    def create_vscode_extension(self, extension_id: str, name: str,
                              description: str, extension_type: ExtensionType) -> str:
        """VS Codeエクステンションを作成"""
        extension = VSCODEExtension(
            id=extension_id,
            name=name,
            description=description,
            version="1.0.0",
            publisher="3d-print-cad-assistant",
            extension_type=extension_type,
            languages=["cad", "stl", "obj", "3mf"],
            activation_events=[
                "onLanguage:cad",
                "onCommand:3dcad.validate",
                "onCommand:3dcad.repair",
                "onCommand:3dcad.optimize"
            ],
            contributes={
                "languages": [{
                    "id": "cad",
                    "aliases": ["CAD", "3D Print CAD"],
                    "extensions": [".cad", ".stl", ".obj", ".3mf"]
                }],
                "commands": [
                    {
                        "command": "3dcad.validate",
                        "title": _("モデルを検証", "Validate Model"),
                        "category": "3D CAD"
                    },
                    {
                        "command": "3dcad.repair",
                        "title": _("モデルを修復", "Repair Model"),
                        "category": "3D CAD"
                    },
                    {
                        "command": "3dcad.optimize",
                        "title": _("モデルを最適化", "Optimize Model"),
                        "category": "3D CAD"
                    }
                ],
                "menus": {
                    "explorer/context": [
                        {
                            "when": "resourceExtname == .stl || resourceExtname == .obj || resourceExtname == .3mf",
                            "command": "3dcad.validate",
                            "group": "3dcad"
                        }
                    ]
                },
                "configuration": {
                    "title": "3D Print CAD Assistant",
                    "properties": {
                        "3dcad.server.port": {
                            "type": "number",
                            "default": 8080,
                            "description": _("サーバーポート", "Server Port")
                        },
                        "3dcad.autoValidation": {
                            "type": "boolean",
                            "default": true,
                            "description": _("自動検証を有効にする", "Enable Auto Validation")
                        }
                    }
                }
            }
        )

        self.extensions[extension_id] = extension

        # エクステンションファイルを生成
        self._generate_vscode_extension_files(extension)

        return extension_id

    def _generate_vscode_extension_files(self, extension: VSCODEExtension) -> None:
        """VS Codeエクステンションファイルを生成"""
        # エクステンションディレクトリを作成
        extension_dir = Path.home() / ".vscode" / "extensions" / extension.id
        extension_dir.mkdir(parents=True, exist_ok=True)

        # package.jsonを生成
        package_json = {
            "name": extension.id,
            "displayName": extension.name,
            "description": extension.description,
            "version": extension.version,
            "publisher": extension.publisher,
            "engines": {
                "vscode": "^1.70.0"
            },
            "categories": ["Other"],
            "activationEvents": extension.activation_events,
            "main": "./out/extension.js",
            "contributes": extension.contributes,
            "dependencies": extension.dependencies,
            "devDependencies": extension.dev_dependencies,
            "scripts": extension.scripts
        }

        with open(extension_dir / "package.json", 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2, ensure_ascii=False)

        # TypeScriptソースコードを生成
        ts_code = """import * as vscode from 'vscode';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    console.log('3D Print CAD Assistant extension is now active!');

    // 検証コマンドを登録
    let validateDisposable = vscode.commands.registerCommand('3dcad.validate', async (uri: vscode.Uri) => {
        if (uri) {
            await validateModel(uri.fsPath);
        }
    });

    // 修復コマンドを登録
    let repairDisposable = vscode.commands.registerCommand('3dcad.repair', async (uri: vscode.Uri) => {
        if (uri) {
            await repairModel(uri.fsPath);
        }
    });

    // 最適化コマンドを登録
    let optimizeDisposable = vscode.commands.registerCommand('3dcad.optimize', async (uri: vscode.Uri) => {
        if (uri) {
            await optimizeModel(uri.fsPath);
        }
    });

    context.subscriptions.push(validateDisposable, repairDisposable, optimizeDisposable);

    // 言語サーバーを起動
    startLanguageServer(context);
}

async function validateModel(filePath: string): Promise<void> {
    try {
        vscode.window.showInformationMessage(\`Validating model: \${filePath}\`);

        // 実際の検証ロジックはここに実装
        const response = await callCADAssistantAPI('validate', { file_path: filePath });

        if (response.success) {
            vscode.window.showInformationMessage('Model validation completed successfully');
        } else {
            vscode.window.showErrorMessage(\`Validation failed: \${response.error}\`);
        }
    } catch (error) {
        vscode.window.showErrorMessage(\`Error validating model: \${error}\`);
    }
}

async function repairModel(filePath: string): Promise<void> {
    try {
        vscode.window.showInformationMessage(\`Repairing model: \${filePath}\`);

        const response = await callCADAssistantAPI('repair', { file_path: filePath });

        if (response.success) {
            vscode.window.showInformationMessage('Model repair completed successfully');
        } else {
            vscode.window.showErrorMessage(\`Repair failed: \${response.error}\`);
        }
    } catch (error) {
        vscode.window.showErrorMessage(\`Error repairing model: \${error}\`);
    }
}

async function optimizeModel(filePath: string): Promise<void> {
    try {
        vscode.window.showInformationMessage(\`Optimizing model: \${filePath}\`);

        const response = await callCADAssistantAPI('optimize', { file_path: filePath });

        if (response.success) {
            vscode.window.showInformationMessage('Model optimization completed successfully');
        } else {
            vscode.window.showErrorMessage(\`Optimization failed: \${response.error}\`);
        }
    } catch (error) {
        vscode.window.showErrorMessage(\`Error optimizing model: \${error}\`);
    }
}

async function callCADAssistantAPI(action: string, params: any): Promise<any> {
    const config = vscode.workspace.getConfiguration('3dcad');
    const port = config.get('server.port', 8080);

    try {
        const response = await fetch(\`http://localhost:\${port}/api/\${action}\`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params)
        });

        return await response.json();
    } catch (error) {
        throw new Error(\`Failed to connect to CAD Assistant server: \${error}\`);
    }
}

function startLanguageServer(context: vscode.ExtensionContext): void {
    // 言語サーバーの実装（簡易版）
    const serverModule = context.asAbsolutePath(path.join('out', 'language-server.js'));

    const serverOptions = {
        run: { command: 'node', args: [serverModule] },
        debug: { command: 'node', args: [serverModule, '--debug'] }
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'cad' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.cad')
        }
    };

    const client = new vscode.LanguageClient(
        '3DCADLanguageServer',
        '3D CAD Language Server',
        serverOptions,
        clientOptions
    );

    context.subscriptions.push(client.start());
}

export function deactivate(): Thenable<void> | undefined {
    return undefined;
}
"""

        with open(extension_dir / "src" / "extension.ts", 'w', encoding='utf-8') as f:
            f.write(ts_code)

        # 言語サーバーコードを生成
        ls_code = """// Language Server for CAD files
const {
    createConnection,
    TextDocuments,
    Diagnostic,
    DiagnosticSeverity,
    ProposedFeatures,
    TextDocumentSyncKind,
} = require('vscode-languageserver');

const connection = createConnection(ProposedFeatures.all);
const documents = new TextDocuments();

connection.onInitialize(() => {
    return {
        capabilities: {
            textDocumentSync: TextDocumentSyncKind.Full,
            diagnosticProvider: {
                documentSelector: ['cad']
            }
        }
    };
});

documents.onDidChangeContent((change) => {
    const document = change.document;
    validateCADDocument(document);
});

async function validateCADDocument(document) {
    const diagnostics = [];

    // 簡易的なCADファイル検証
    const text = document.getText();

    // 基本的な構文チェック
    if (text.includes('cube') && !text.includes(';')) {
        diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: {
                start: { line: 0, character: 0 },
                end: { line: 0, character: 10 }
            },
            message: 'Missing semicolon after cube declaration',
            source: 'CAD Assistant'
        });
    }

    // 診断情報を送信
    connection.sendDiagnostics({ uri: document.uri, diagnostics });
}

connection.listen();
"""

        with open(extension_dir / "out" / "language-server.js", 'w', encoding='utf-8') as f:
            f.write(ls_code)

        self.logger.info(f"VS Code extension files generated: {extension_dir}")

    def register_plugin(self, plugin: CADPlugin) -> None:
        """CADプラグインを登録"""
        self.plugins[plugin.id] = plugin

        # プラグインを動的にロード
        try:
            module_path = plugin.entry_point
            if module_path.endswith('.py'):
                # Pythonプラグインをインポート
                import importlib.util
                spec = importlib.util.spec_from_file_location(plugin.id, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # プラグインフックを登録
                    self._register_plugin_hooks(plugin, module)

            self.plugin_registry[plugin.id] = {
                "plugin": plugin,
                "loaded": True,
                "module": module if 'module' in locals() else None
            }

            self.logger.info(f"Registered CAD plugin: {plugin.id}")

        except Exception as e:
            self.logger.error(f"Failed to register plugin {plugin.id}: {str(e)}")
            self.plugin_registry[plugin.id] = {
                "plugin": plugin,
                "loaded": False,
                "error": str(e)
            }

    def _register_plugin_hooks(self, plugin: CADPlugin, module: Any) -> None:
        """プラグインフックを登録"""
        for hook_name, hook_function in plugin.hooks.items():
            if hasattr(module, hook_function):
                # フック関数をグローバルレジストリに登録
                hook_key = f"{plugin.id}_{hook_name}"
                setattr(self, hook_key, getattr(module, hook_function))

    def execute_plugin_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """プラグインフックを実行"""
        results = []

        for plugin_id, plugin_info in self.plugin_registry.items():
            if plugin_info.get("loaded", False):
                plugin = plugin_info["plugin"]
                hook_key = f"{plugin_id}_{hook_name}"

                if hasattr(self, hook_key):
                    try:
                        hook_function = getattr(self, hook_key)
                        result = hook_function(*args, **kwargs)
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"Error executing plugin hook {hook_key}: {str(e)}")

        return results

    def create_plugin_template(self, plugin_type: PluginType, name: str, author: str) -> CADPlugin:
        """プラグインテンプレートを作成"""
        plugin_id = f"{plugin_type.value}_{name.lower().replace(' ', '_')}"

        template_hooks = {
            PluginType.MESH_PROCESSOR: {
                "on_mesh_load": "process_mesh",
                "on_mesh_save": "post_process_mesh"
            },
            PluginType.MATERIAL_PROVIDER: {
                "on_material_request": "provide_material",
                "on_material_update": "update_material"
            },
            PluginType.EXPORT_FILTER: {
                "on_export": "filter_export",
                "on_format_convert": "convert_format"
            }
        }

        plugin = CADPlugin(
            id=plugin_id,
            name=name,
            description=f"Custom {plugin_type.value} plugin",
            version="1.0.0",
            plugin_type=plugin_type,
            author=author,
            entry_point=f"plugins/{plugin_id}.py",
            hooks=template_hooks.get(plugin_type, {})
        )

        # プラグインテンプレートファイルを生成
        self._generate_plugin_template_file(plugin)

        return plugin

    def _generate_plugin_template_file(self, plugin: CADPlugin) -> None:
        """プラグインテンプレートファイルを生成"""
        template_code = f'''#!/usr/bin/env python3
"""
{plugin.name} - {plugin.description}
Author: {plugin.author}
Version: {plugin.version}
"""

from __future__ import annotations

def process_mesh(mesh_data: dict, context: dict) -> dict:
    """メッシュデータを処理するフック関数"""
    # カスタムメッシュ処理ロジックを実装
    print(f"Processing mesh with {plugin.name}")

    # 元のデータを返す（変更なし）
    return mesh_data

def post_process_mesh(mesh_data: dict, context: dict) -> dict:
    """メッシュ保存後の処理フック関数"""
    # カスタム後処理ロジックを実装
    print(f"Post-processing mesh with {plugin.name}")

    return mesh_data

# プラグインフックをエクスポート
__all__ = [
    "process_mesh",
    "post_process_mesh"
]
'''

        # プラグインディレクトリを作成
        plugin_dir = Path("plugins")
        plugin_dir.mkdir(exist_ok=True)

        plugin_file = plugin_dir / f"{plugin.id}.py"
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write(template_code)

        self.logger.info(f"Plugin template created: {plugin_file}")

    def install_vscode_extension(self, extension_path: str) -> bool:
        """VS Codeエクステンションをインストール"""
        try:
            # VS Codeのコマンドラインインターフェースを使用してインストール
            cmd = [
                "code",
                "--install-extension",
                extension_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"VS Code extension installed: {extension_path}")
                return True
            else:
                self.logger.error(f"Failed to install VS Code extension: {result.stderr}")
                return False

        except FileNotFoundError:
            self.logger.error("VS Code CLI not found. Please install VS Code and ensure 'code' command is available.")
            return False
        except Exception as e:
            self.logger.error(f"Error installing VS Code extension: {str(e)}")
            return False

    def get_extension_manifest(self, extension_id: str) -> Optional[Dict[str, Any]]:
        """エクステンションマニフェストを取得"""
        if extension_id in self.extensions:
            extension = self.extensions[extension_id]

            # package.json形式で返す
            return {
                "name": extension.id,
                "displayName": extension.name,
                "description": extension.description,
                "version": extension.version,
                "publisher": extension.publisher,
                "engines": {"vscode": "^1.70.0"},
                "categories": ["Other"],
                "activationEvents": extension.activation_events,
                "main": "./out/extension.js",
                "contributes": extension.contributes
            }

        return None

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """プラグイン情報を取得"""
        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            registry_info = self.plugin_registry.get(plugin_id, {})

            return {
                "plugin": plugin.__dict__,
                "loaded": registry_info.get("loaded", False),
                "error": registry_info.get("error", None)
            }

        return None

    def list_extensions(self) -> List[Dict[str, Any]]:
        """登録済みエクステンションを一覧表示"""
        return [
            {
                "id": ext.id,
                "name": ext.name,
                "type": ext.extension_type.value,
                "version": ext.version
            }
            for ext in self.extensions.values()
        ]

    def list_plugins(self) -> List[Dict[str, Any]]:
        """登録済みプラグインを一覧表示"""
        return [
            {
                "id": plugin.id,
                "name": plugin.name,
                "type": plugin.plugin_type.value,
                "version": plugin.version,
                "loaded": self.plugin_registry.get(plugin.id, {}).get("loaded", False)
            }
            for plugin in self.plugins.values()
        ]

# グローバルインスタンス
_ide_integration_manager = None

def get_ide_integration_manager() -> IDEIntegrationManager:
    """統合開発環境統合管理システムのインスタンスを取得"""
    global _ide_integration_manager
    if _ide_integration_manager is None:
        _ide_integration_manager = IDEIntegrationManager()
    return _ide_integration_manager
