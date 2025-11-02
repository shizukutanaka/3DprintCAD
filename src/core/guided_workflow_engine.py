#!/usr/bin/env python3
"""
初心者向けガイド付きワークフローシステム
TinkerCADスタイルの簡単操作とステップバイステップガイドを提供
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class WorkflowStep(Enum):
    """ワークフローステップの種類"""
    INTRODUCTION = "introduction"
    TEMPLATE_SELECTION = "template_selection"
    PARAMETER_INPUT = "parameter_input"
    DESIGN_CUSTOMIZATION = "design_customization"
    PREVIEW_AND_SIMULATION = "preview_simulation"
    EXPORT_AND_PRINT = "export_print"

class TemplateCategory(Enum):
    """テンプレートのカテゴリ"""
    BASIC_SHAPES = "basic_shapes"
    HOUSEHOLD_ITEMS = "household_items"
    TOYS_AND_GAMES = "toys_games"
    JEWELRY = "jewelry"
    MECHANICAL_PARTS = "mechanical_parts"
    ART_AND_DECORATION = "art_decoration"
    PROTOTYPES = "prototypes"
    CUSTOM = "custom"

@dataclass
class WorkflowTemplate:
    """ワークフローテンプレート"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    difficulty: str  # "beginner", "intermediate", "advanced"
    estimated_time: int  # 分単位
    preview_image: Optional[str] = None
    parameters: Dict[str, Any] = None
    steps: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)

class GuidedWorkflowEngine:
    """ガイド付きワークフローエンジン"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.templates = self._load_templates()
        self.current_session = None

    def _load_templates(self) -> Dict[str, WorkflowTemplate]:
        """テンプレートをロード"""
        templates_dir = Path(__file__).parent / "templates" / "guided_workflows"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # デフォルトテンプレート
        default_templates = {
            "basic_cube": WorkflowTemplate(
                id="basic_cube",
                name=_("基本的な立方体", "Basic Cube"),
                description=_("シンプルな立方体の作成から始めましょう", "Let's start with creating a simple cube"),
                category=TemplateCategory.BASIC_SHAPES,
                difficulty="beginner",
                estimated_time=5,
                parameters={
                    "width": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"},
                    "height": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"},
                    "depth": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"}
                },
                steps=[
                    "template_selection",
                    "parameter_input",
                    "preview_simulation",
                    "export_print"
                ]
            ),
            "phone_stand": WorkflowTemplate(
                id="phone_stand",
                name=_("スマホスタンド", "Phone Stand"),
                description=_("実用的なスマホスタンドを作成します", "Create a practical phone stand"),
                category=TemplateCategory.HOUSEHOLD_ITEMS,
                difficulty="intermediate",
                estimated_time=15,
                parameters={
                    "phone_width": {"type": "number", "default": 75, "min": 60, "max": 100, "unit": "mm"},
                    "phone_thickness": {"type": "number", "default": 8, "min": 5, "max": 15, "unit": "mm"},
                    "stand_angle": {"type": "number", "default": 30, "min": 15, "max": 60, "unit": "degrees"},
                    "base_width": {"type": "number", "default": 100, "min": 80, "max": 150, "unit": "mm"}
                },
                steps=[
                    "template_selection",
                    "parameter_input",
                    "design_customization",
                    "preview_simulation",
                    "export_print"
                ]
            ),
            "custom_jewelry": WorkflowTemplate(
                id="custom_jewelry",
                name=_("カスタムジュエリー", "Custom Jewelry"),
                description=_("自分だけのジュエリーを作成しましょう", "Create your own unique jewelry"),
                category=TemplateCategory.JEWELRY,
                difficulty="advanced",
                estimated_time=25,
                parameters={
                    "ring_size": {"type": "number", "default": 17, "min": 10, "max": 25, "unit": "mm"},
                    "band_width": {"type": "number", "default": 3, "min": 2, "max": 8, "unit": "mm"},
                    "gem_shape": {"type": "select", "options": ["round", "square", "oval", "heart"], "default": "round"},
                    "engraving_text": {"type": "text", "default": "", "max_length": 20}
                },
                steps=[
                    "template_selection",
                    "parameter_input",
                    "design_customization",
                    "preview_simulation",
                    "export_print"
                ]
            )
        }

        return default_templates

    def start_guided_session(self, template_id: str, language: str = "ja") -> Dict[str, Any]:
        """ガイド付きセッションを開始"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")

        template = self.templates[template_id]
        self.current_session = {
            "session_id": str(uuid.uuid4()),
            "template": template.to_dict(),
            "current_step": WorkflowStep.TEMPLATE_SELECTION.value,
            "progress": 0,
            "parameters": {},
            "language": language,
            "created_at": self._get_timestamp()
        }

        self.logger.info(f"Started guided session {self.current_session['session_id']} for template {template_id}")

        return {
            "session_id": self.current_session["session_id"],
            "welcome_message": self._get_welcome_message(template, language),
            "next_step": self.current_session["current_step"],
            "template": template.to_dict()
        }

    def get_next_step(self, session_id: str, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        """次のステップを取得"""
        if not self.current_session or self.current_session["session_id"] != session_id:
            raise ValueError("Invalid session ID")

        current_step = self.current_session["current_step"]
        template = self.current_session["template"]

        if current_step == WorkflowStep.TEMPLATE_SELECTION.value:
            return self._handle_template_selection(user_input)
        elif current_step == WorkflowStep.PARAMETER_INPUT.value:
            return self._handle_parameter_input(user_input)
        elif current_step == WorkflowStep.DESIGN_CUSTOMIZATION.value:
            return self._handle_design_customization(user_input)
        elif current_step == WorkflowStep.PREVIEW_AND_SIMULATION.value:
            return self._handle_preview_simulation(user_input)
        elif current_step == WorkflowStep.EXPORT_AND_PRINT.value:
            return self._handle_export_print(user_input)

        return {"error": "Unknown step"}

    def _handle_template_selection(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """テンプレート選択ステップを処理"""
        # 既に選択済みなのでパラメータ入力へ
        self.current_session["current_step"] = WorkflowStep.PARAMETER_INPUT.value
        self.current_session["progress"] = 25

        template = self.current_session["template"]

        return {
            "step": WorkflowStep.PARAMETER_INPUT.value,
            "message": _("パラメータを入力してください", "Please enter the parameters"),
            "parameters": template.get("parameters", {}),
            "progress": self.current_session["progress"]
        }

    def _handle_parameter_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """パラメータ入力ステップを処理"""
        if user_input:
            # パラメータを検証して保存
            self.current_session["parameters"].update(user_input)

        # 全てのパラメータが入力されたかチェック
        template = self.current_session["template"]
        required_params = template.get("parameters", {})

        if all(param in self.current_session["parameters"] for param in required_params):
            self.current_session["current_step"] = WorkflowStep.DESIGN_CUSTOMIZATION.value
            self.current_session["progress"] = 50

            return {
                "step": WorkflowStep.DESIGN_CUSTOMIZATION.value,
                "message": _("デザインをカスタマイズしますか？", "Would you like to customize the design?"),
                "can_skip": True,
                "progress": self.current_session["progress"]
            }
        else:
            # まだ入力が必要なパラメータがある
            missing_params = [p for p in required_params if p not in self.current_session["parameters"]]
            return {
                "step": WorkflowStep.PARAMETER_INPUT.value,
                "message": _("以下の必須パラメータを入力してください", "Please enter the following required parameters"),
                "missing_parameters": missing_params,
                "parameters": {k: v for k, v in required_params.items() if k in missing_params}
            }

    def _handle_design_customization(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """デザインカスタマイズステップを処理"""
        if user_input and user_input.get("skip", False):
            # スキップする場合
            self.current_session["current_step"] = WorkflowStep.PREVIEW_AND_SIMULATION.value
            self.current_session["progress"] = 75
        else:
            # カスタマイズ処理（ここでは簡易的に）
            self.current_session["customizations"] = user_input or {}

            self.current_session["current_step"] = WorkflowStep.PREVIEW_AND_SIMULATION.value
            self.current_session["progress"] = 75

        return {
            "step": WorkflowStep.PREVIEW_AND_SIMULATION.value,
            "message": _("デザインをプレビューします", "Previewing your design"),
            "preview_data": self._generate_preview_data(),
            "progress": self.current_session["progress"]
        }

    def _handle_preview_simulation(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """プレビューとシミュレーションステップを処理"""
        # プレビュー生成（簡易的に）
        preview_info = {
            "estimated_print_time": "2時間30分",
            "material_usage": "25g",
            "layer_count": 180,
            "support_needed": False,
            "potential_issues": []
        }

        self.current_session["current_step"] = WorkflowStep.EXPORT_AND_PRINT.value
        self.current_session["progress"] = 100
        self.current_session["preview_info"] = preview_info

        return {
            "step": WorkflowStep.EXPORT_AND_PRINT.value,
            "message": _("エクスポートと印刷の準備ができました", "Ready for export and printing"),
            "preview_info": preview_info,
            "export_options": ["STL", "OBJ", "3MF"],
            "progress": self.current_session["progress"]
        }

    def _handle_export_print(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """エクスポートと印刷ステップを処理"""
        export_format = user_input.get("format", "STL") if user_input else "STL"

        # エクスポート処理（ここではファイルパスを生成）
        export_path = f"/tmp/guided_export_{self.current_session['session_id']}.{export_format.lower()}"

        self.current_session["export_path"] = export_path
        self.current_session["completed_at"] = self._get_timestamp()

        self.logger.info(f"Completed guided session {self.current_session['session_id']}")

        return {
            "completed": True,
            "export_path": export_path,
            "export_format": export_format,
            "summary": self._generate_session_summary()
        }

    def _get_welcome_message(self, template: WorkflowTemplate, language: str) -> str:
        """ウェルカムメッセージを生成"""
        if language == "ja":
            return f"「{template.name}」の作成を始めましょう！このガイドでは、ステップバイステップで{templated.estimated_time}分程度で完了します。"
        else:
            return f"Let's start creating '{template.name}'! This guided workflow will take approximately {template.estimated_time} minutes to complete."

    def _generate_preview_data(self) -> Dict[str, Any]:
        """プレビューデータを生成"""
        return {
            "model_info": {
                "dimensions": self.current_session["parameters"],
                "volume": "15.2 cm³",
                "surface_area": "45.8 cm²"
            },
            "print_settings": {
                "recommended_layer_height": "0.2mm",
                "infill_density": "20%",
                "support_material": "なし"
            }
        }

    def _generate_session_summary(self) -> Dict[str, Any]:
        """セッションサマリーを生成"""
        return {
            "session_id": self.current_session["session_id"],
            "template_used": self.current_session["template"]["name"],
            "parameters_used": self.current_session["parameters"],
            "completion_time": self.current_session["completed_at"],
            "estimated_print_time": self.current_session["preview_info"]["estimated_print_time"]
        }

    def _get_timestamp(self) -> str:
        """タイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_available_templates(self, category: Optional[TemplateCategory] = None) -> List[Dict[str, Any]]:
        """利用可能なテンプレートを取得"""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return [t.to_dict() for t in templates]

# グローバルインスタンス
_guided_workflow_engine = None

def get_guided_workflow_engine() -> GuidedWorkflowEngine:
    """ガイド付きワークフローエンジンのインスタンスを取得"""
    global _guided_workflow_engine
    if _guided_workflow_engine is None:
        _guided_workflow_engine = GuidedWorkflowEngine()
    return _guided_workflow_engine
