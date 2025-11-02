#!/usr/bin/env python3
"""
高度なビジュアルプログラミングブロックシステム
Scratch風のノードベースデザインシステムで初心者を支援
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class BlockCategory(Enum):
    """ブロックのカテゴリ"""
    GEOMETRY = "geometry"
    TRANSFORMATION = "transformation"
    MATERIAL = "material"
    PRINT_SETTINGS = "print_settings"
    CONTROL = "control"
    VARIABLE = "variable"
    OPERATOR = "operator"

class BlockType(Enum):
    """ブロックの種類"""
    # ジオメトリブロック
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CONE = "cone"
    TORUS = "torus"

    # 変換ブロック
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    MIRROR = "mirror"

    # マテリアルブロック
    MATERIAL_PLA = "material_pla"
    MATERIAL_ABS = "material_abs"
    MATERIAL_PETG = "material_petg"
    MATERIAL_FLEXIBLE = "material_flexible"

    # プリント設定ブロック
    LAYER_HEIGHT = "layer_height"
    INFILL_DENSITY = "infill_density"
    PRINT_SPEED = "print_speed"
    SUPPORT_ENABLED = "support_enabled"

    # 制御ブロック
    IF = "if"
    LOOP = "loop"
    FUNCTION = "function"

    # 変数ブロック
    SET_VARIABLE = "set_variable"
    GET_VARIABLE = "get_variable"

    # 演算ブロック
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"

@dataclass
class VisualBlock:
    """ビジュアルプログラミングブロック"""
    id: str
    type: BlockType
    category: BlockCategory
    position: Tuple[float, float]
    size: Tuple[float, float]
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)  # 接続されたブロックのID
    parent_chain: List[str] = field(default_factory=list)  # 実行チェーン

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)

@dataclass
class VisualProgram:
    """ビジュアルプログラム"""
    id: str
    name: str
    description: str
    blocks: Dict[str, VisualBlock] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    modified_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['blocks'] = {k: v.to_dict() for k, v in self.blocks.items()}
        return data

class VisualProgrammingEngine:
    """ビジュアルプログラミングエンジン"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.programs: Dict[str, VisualProgram] = {}
        self.block_templates = self._initialize_block_templates()

    def _initialize_block_templates(self) -> Dict[BlockType, Dict[str, Any]]:
        """ブロックテンプレートを初期化"""
        return {
            BlockType.CUBE: {
                "category": BlockCategory.GEOMETRY,
                "name": _("立方体", "Cube"),
                "description": _("立方体を作成します", "Creates a cube"),
                "inputs": {
                    "width": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"},
                    "height": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"},
                    "depth": {"type": "number", "default": 20, "min": 1, "max": 200, "unit": "mm"}
                },
                "outputs": {"geometry": "cube"},
                "color": "#4CAF50"
            },
            BlockType.SPHERE: {
                "category": BlockCategory.GEOMETRY,
                "name": _("球体", "Sphere"),
                "description": _("球体を作成します", "Creates a sphere"),
                "inputs": {
                    "radius": {"type": "number", "default": 10, "min": 1, "max": 100, "unit": "mm"}
                },
                "outputs": {"geometry": "sphere"},
                "color": "#2196F3"
            },
            BlockType.TRANSLATE: {
                "category": BlockCategory.TRANSFORMATION,
                "name": _("移動", "Translate"),
                "description": _("オブジェクトを移動します", "Translates an object"),
                "inputs": {
                    "x": {"type": "number", "default": 0, "min": -100, "max": 100, "unit": "mm"},
                    "y": {"type": "number", "default": 0, "min": -100, "max": 100, "unit": "mm"},
                    "z": {"type": "number", "default": 0, "min": -100, "max": 100, "unit": "mm"},
                    "input_geometry": {"type": "geometry", "required": True}
                },
                "outputs": {"geometry": "translated"},
                "color": "#FF9800"
            },
            BlockType.MATERIAL_PLA: {
                "category": BlockCategory.MATERIAL,
                "name": _("PLAマテリアル", "PLA Material"),
                "description": _("PLAマテリアルを設定します", "Sets PLA material"),
                "inputs": {
                    "temperature": {"type": "number", "default": 200, "min": 180, "max": 220, "unit": "°C"},
                    "bed_temperature": {"type": "number", "default": 60, "min": 50, "max": 70, "unit": "°C"}
                },
                "outputs": {"material": "pla"},
                "color": "#9C27B0"
            }
        }

    def create_program(self, name: str, description: str = "") -> str:
        """新しいプログラムを作成"""
        program_id = f"visual_program_{uuid.uuid4().hex[:8]}"

        program = VisualProgram(
            id=program_id,
            name=name,
            description=description,
            created_at=self._get_timestamp(),
            modified_at=self._get_timestamp()
        )

        self.programs[program_id] = program
        self.logger.info(f"Created visual program: {program_id}")

        return program_id

    def add_block(self, program_id: str, block_type: BlockType, position: Tuple[float, float]) -> Dict[str, Any]:
        """プログラムにブロックを追加"""
        if program_id not in self.programs:
            raise ValueError("Program not found")

        program = self.programs[program_id]
        block_id = f"block_{uuid.uuid4().hex[:8]}"

        template = self.block_templates.get(block_type)
        if not template:
            raise ValueError(f"Block type {block_type} not supported")

        block = VisualBlock(
            id=block_id,
            type=block_type,
            category=template["category"],
            position=position,
            size=(120, 80),  # デフォルトサイズ
            inputs=template["inputs"].copy(),
            outputs=template["outputs"].copy()
        )

        program.blocks[block_id] = block
        program.modified_at = self._get_timestamp()

        return {
            "block_id": block_id,
            "block": block.to_dict(),
            "template": template
        }

    def connect_blocks(self, program_id: str, from_block_id: str, to_block_id: str,
                     from_output: str, to_input: str) -> Dict[str, Any]:
        """ブロックを接続"""
        if program_id not in self.programs:
            raise ValueError("Program not found")

        program = self.programs[program_id]

        if from_block_id not in program.blocks or to_block_id not in program.blocks:
            raise ValueError("Block not found")

        from_block = program.blocks[from_block_id]
        to_block = program.blocks[to_block_id]

        # 接続を追加
        if to_block_id not in from_block.connections:
            from_block.connections.append(to_block_id)

        # 入力値を設定
        if to_input in to_block.inputs:
            # from_blockの出力値をto_blockの入力に設定
            if from_output in from_block.outputs:
                to_block.inputs[to_input] = {"source": from_block_id, "output": from_output}

        program.modified_at = self._get_timestamp()

        return {
            "success": True,
            "connection": {
                "from_block": from_block_id,
                "to_block": to_block_id,
                "from_output": from_output,
                "to_input": to_input
            }
        }

    def update_block_input(self, program_id: str, block_id: str, input_name: str, value: Any) -> Dict[str, Any]:
        """ブロックの入力値を更新"""
        if program_id not in self.programs:
            raise ValueError("Program not found")

        program = self.programs[program_id]

        if block_id not in program.blocks:
            raise ValueError("Block not found")

        block = program.blocks[block_id]

        if input_name in block.inputs:
            block.inputs[input_name] = value
            program.modified_at = self._get_timestamp()

            return {"success": True, "updated_input": input_name, "new_value": value}
        else:
            return {"error": "Input not found"}

    def generate_code(self, program_id: str) -> Dict[str, Any]:
        """ビジュアルプログラムからコードを生成"""
        if program_id not in self.programs:
            raise ValueError("Program not found")

        program = self.programs[program_id]

        # 実行順序を決定（簡易的なトポロジカルソート）
        execution_order = self._determine_execution_order(program)

        # コードを生成
        code_lines = []
        code_lines.append("// Generated from Visual Programming Blocks")
        code_lines.append("")

        for block_id in execution_order:
            block = program.blocks[block_id]
            code = self._generate_block_code(block, program)
            if code:
                code_lines.append(code)

        generated_code = "\n".join(code_lines)

        return {
            "success": True,
            "generated_code": generated_code,
            "execution_order": execution_order,
            "variables_used": list(program.variables.keys())
        }

    def _determine_execution_order(self, program: VisualProgram) -> List[str]:
        """実行順序を決定"""
        # 簡易的な実装：接続の深さに基づいてソート
        visited = set()
        order = []

        def visit(block_id: str):
            if block_id in visited:
                return
            visited.add(block_id)

            block = program.blocks[block_id]

            # 依存関係を先に処理
            for connected_id in block.connections:
                if connected_id in program.blocks:
                    visit(connected_id)

            order.append(block_id)

        # ルートブロックから開始
        root_blocks = [block_id for block_id, block in program.blocks.items()
                      if not any(block_id in other_block.connections for other_block in program.blocks.values())]

        for root_id in root_blocks:
            visit(root_id)

        return order

    def _generate_block_code(self, block: VisualBlock, program: VisualProgram) -> str:
        """ブロックからコードを生成"""
        if block.type == BlockType.CUBE:
            width = block.inputs.get("width", 20)
            height = block.inputs.get("height", 20)
            depth = block.inputs.get("depth", 20)
            return f"cube([{width}, {height}, {depth}]);"

        elif block.type == BlockType.SPHERE:
            radius = block.inputs.get("radius", 10)
            return f"sphere(r = {radius});"

        elif block.type == BlockType.TRANSLATE:
            x = block.inputs.get("x", 0)
            y = block.inputs.get("y", 0)
            z = block.inputs.get("z", 0)
            input_geom = block.inputs.get("input_geometry", None)

            if input_geom and "source" in input_geom:
                source_block = program.blocks.get(input_geom["source"])
                if source_block:
                    inner_code = self._generate_block_code(source_block, program)
                    return f"translate([{x}, {y}, {z}]) {{\n  {inner_code}\n}};"
            else:
                return f"translate([{x}, {y}, {z}]);"

        elif block.type == BlockType.MATERIAL_PLA:
            temp = block.inputs.get("temperature", 200)
            bed_temp = block.inputs.get("bed_temperature", 60)
            return f"// Material: PLA, Temperature: {temp}°C, Bed: {bed_temp}°C"

        return f"// Block: {block.type.value}"

    def get_block_palette(self) -> Dict[str, List[Dict[str, Any]]]:
        """ブロックパレットを取得"""
        palette = {}

        for category in BlockCategory:
            palette[category.value] = []

            for block_type, template in self.block_templates.items():
                if template["category"] == category:
                    palette[category.value].append({
                        "type": block_type.value,
                        "name": template["name"],
                        "description": template["description"],
                        "color": template.get("color", "#CCCCCC"),
                        "inputs": template["inputs"],
                        "outputs": template["outputs"]
                    })

        return palette

    def validate_program(self, program_id: str) -> Dict[str, Any]:
        """プログラムを検証"""
        if program_id not in self.programs:
            raise ValueError("Program not found")

        program = self.programs[program_id]
        errors = []
        warnings = []

        # ブロックの検証
        for block_id, block in program.blocks.items():
            # 必須入力のチェック
            for input_name, input_def in block.inputs.items():
                if input_def.get("required", False) and input_name not in block.inputs:
                    errors.append(f"Block {block_id}: Missing required input '{input_name}'")

            # 接続の検証
            for connected_id in block.connections:
                if connected_id not in program.blocks:
                    errors.append(f"Block {block_id}: Connected block '{connected_id}' not found")

        # 循環参照のチェック（簡易的に）
        if self._has_cycle(program):
            errors.append("Circular dependency detected in block connections")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "block_count": len(program.blocks)
        }

    def _has_cycle(self, program: VisualProgram) -> bool:
        """循環参照をチェック（簡易実装）"""
        # 実際にはより洗練されたアルゴリズムが必要
        visited = set()
        rec_stack = set()

        def has_cycle_util(block_id: str) -> bool:
            if block_id in rec_stack:
                return True
            if block_id in visited:
                return False

            visited.add(block_id)
            rec_stack.add(block_id)

            block = program.blocks[block_id]
            for connected_id in block.connections:
                if connected_id in program.blocks and has_cycle_util(connected_id):
                    return True

            rec_stack.remove(block_id)
            return False

        for block_id in program.blocks:
            if has_cycle_util(block_id):
                return True

        return False

    def _get_timestamp(self) -> str:
        """タイムスタンプを取得"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

# グローバルインスタンス
_visual_programming_engine = None

def get_visual_programming_engine() -> VisualProgrammingEngine:
    """ビジュアルプログラミングエンジンのインスタンスを取得"""
    global _visual_programming_engine
    if _visual_programming_engine is None:
        _visual_programming_engine = VisualProgrammingEngine()
    return _visual_programming_engine
