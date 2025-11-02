# コーディング規約 / Coding Standards

## 概要 / Overview

本プロジェクトのコード品質を維持し、保守性と可読性を確保するためのコーディング規約を定義します。

This document defines coding standards to maintain code quality, maintainability, and readability for this project.

## 基本原則 / Basic Principles

### 1. 明確性と簡潔性 / Clarity and Conciseness
- コードは明確で理解しやすいものにする
- 冗長な表現を避け、簡潔に記述する
- 変数名、関数名は意味を明確に伝えるものにする

### 2. 一貫性 / Consistency
- プロジェクト全体で統一されたスタイルを維持
- 既存のコードパターンを尊重する
- ツールによる自動フォーマットを活用

### 3. 保守性 / Maintainability
- 将来の変更を容易にする設計
- 適切な抽象化と分割
- ドキュメントの充実

## Pythonコーディング規約 / Python Coding Standards

### スタイルガイド / Style Guide

#### Blackコードフォーマッター / Black Code Formatter
```python
# 正しい例 / Correct
def calculate_volume(length, width, height):
    """Calculate volume of rectangular prism."""
    return length * width * height

# 避けるべき例 / Avoid
def calculate_volume( length, width, height ):
    """Calculate volume of rectangular prism."""
    return length * width * height
```

#### isort import整理 / isort Import Organization
```python
# 正しい順序 / Correct order
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import trimesh

from .core.config import get_config
from .core.logging import get_logger
```

### 命名規則 / Naming Conventions

#### 変数と関数 / Variables and Functions
```python
# スネークケース / snake_case
user_name = "john_doe"
def calculate_mesh_volume():
    pass

# 定数 / Constants
MAX_FILE_SIZE_MB = 100
DEFAULT_TIMEOUT_SECONDS = 300
```

#### クラスと型 / Classes and Types
```python
# パスカルケース / PascalCase
class MeshValidator:
    pass

class ValidationResult:
    pass

# 型エイリアス / Type Aliases
MeshData = Dict[str, Any]
FilePath = str
```

#### プライベートメンバ / Private Members
```python
class Processor:
    def __init__(self):
        self._internal_state = None
        self.__private_method()
```

### ドキュメンテーション / Documentation

#### モジュールドックストリング / Module Docstrings
```python
"""Mesh validation utilities for 3D printing.

This module provides comprehensive validation for 3D mesh files
to ensure printability and quality standards.
"""

import numpy as np
```

#### クラスドックストリング / Class Docstrings
```python
class MeshValidator:
    """Validates 3D meshes for printing compatibility.

    This class performs geometric analysis and identifies
    potential printing issues before manufacturing.
    """

    def __init__(self, config: ValidationConfig):
        """Initialize validator with configuration.

        Args:
            config: Validation settings and thresholds
        """
        pass
```

#### 関数ドックストリング / Function Docstrings
```python
def validate_mesh(
    mesh: trimesh.Trimesh,
    settings: Optional[MeshValidationSettings] = None
) -> MeshValidationResult:
    """Validate mesh for 3D printing.

    Performs comprehensive checks including manifold validation,
    wall thickness analysis, and overhang detection.

    Args:
        mesh: The mesh to validate
        settings: Optional validation settings

    Returns:
        Validation results with issues and metrics

    Raises:
        ValueError: If mesh is invalid or corrupted
    """
    pass
```

### 型ヒント / Type Hints

#### 基本的な型ヒント / Basic Type Hints
```python
from typing import Dict, List, Optional, Tuple, Union, Any

def process_files(
    file_paths: List[str],
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    pass
```

#### ジェネリック型 / Generic Types
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Result(Generic[T]):
    def __init__(self, value: T, error: Optional[str] = None):
        self.value = value
        self.error = error
```

#### コールバック型 / Callable Types
```python
from typing import Callable

def register_callback(
    callback: Callable[[Dict[str, Any]], None]
) -> None:
    pass
```

## エラーハンドリング / Error Handling

### 例外の適切な使用 / Proper Exception Usage
```python
class ValidationError(Exception):
    """Raised when mesh validation fails."""
    pass

class FileProcessingError(Exception):
    """Raised when file processing fails."""
    pass

def load_mesh_file(file_path: str) -> trimesh.Trimesh:
    """Load mesh from file with proper error handling."""
    try:
        mesh = trimesh.load(file_path)
    except FileNotFoundError:
        raise FileProcessingError(f"File not found: {file_path}")
    except Exception as e:
        raise ValidationError(f"Failed to load mesh: {e}")

    if mesh.vertices.size == 0:
        raise ValidationError("Mesh contains no vertices")

    return mesh
```

### ログの適切な使用 / Proper Logging Usage
```python
import logging

logger = logging.getLogger(__name__)

def process_batch(files: List[str]) -> None:
    """Process multiple files with logging."""
    logger.info(f"Processing {len(files)} files")

    for file_path in files:
        try:
            logger.debug(f"Processing file: {file_path}")
            # 処理実行 / Process file
            logger.info(f"Successfully processed: {file_path}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            raise
```

## テスト規約 / Testing Standards

### ユニットテスト / Unit Tests
```python
import pytest
from unittest.mock import Mock, patch

class TestMeshValidator:

    def test_valid_mesh_passes_validation(self):
        """Test that valid mesh passes all validations."""
        # Arrange
        mesh = create_valid_test_mesh()
        validator = MeshValidator()

        # Act
        result = validator.validate(mesh)

        # Assert
        assert result.is_valid
        assert len(result.issues) == 0

    def test_invalid_mesh_fails_validation(self):
        """Test that invalid mesh fails validation."""
        # Arrange
        mesh = create_invalid_test_mesh()
        validator = MeshValidator()

        # Act
        result = validator.validate(mesh)

        # Assert
        assert not result.is_valid
        assert len(result.issues) > 0

    @patch('trimesh.load')
    def test_file_loading_error_handling(self, mock_load):
        """Test proper error handling for file loading failures."""
        # Arrange
        mock_load.side_effect = FileNotFoundError("File not found")
        validator = MeshValidator()

        # Act & Assert
        with pytest.raises(FileProcessingError):
            validator.load_file("nonexistent.stl")
```

### テスト命名規則 / Test Naming Conventions
```python
# テストクラス / Test Classes
class TestMeshValidator:
    pass

class TestFileProcessor:
    pass

# テストメソッド / Test Methods
def test_valid_input_returns_expected_output():
    pass

def test_invalid_input_raises_appropriate_exception():
    pass

def test_edge_case_handles_gracefully():
    pass
```

## パフォーマンス考慮 / Performance Considerations

### 効率的なアルゴリズム / Efficient Algorithms
```python
# ベクトル化を使用 / Use vectorization
import numpy as np

def calculate_distances(points: np.ndarray, center: np.ndarray) -> np.ndarray:
    """Calculate distances using vectorized operations."""
    # 良い例 / Good
    return np.linalg.norm(points - center, axis=1)

    # 避けるべき例 / Avoid
    # distances = []
    # for point in points:
    #     distances.append(np.linalg.norm(point - center))
    # return np.array(distances)
```

### メモリ管理 / Memory Management
```python
def process_large_mesh(mesh: trimesh.Trimesh) -> None:
    """Process large meshes with memory efficiency."""
    # 大きなデータを処理する際はチャンク分割 / Chunk large data
    chunk_size = 10000
    for i in range(0, len(mesh.faces), chunk_size):
        face_chunk = mesh.faces[i:i + chunk_size]
        # チャンク処理 / Process chunk
        process_faces(face_chunk)
```

## セキュリティ考慮 / Security Considerations

### 入力検証 / Input Validation
```python
def validate_file_path(file_path: str) -> Path:
    """Validate file path for security."""
    path = Path(file_path).resolve()

    # パストラバーサル攻撃防止 / Prevent path traversal
    if ".." in path.parts:
        raise ValueError("Path traversal detected")

    # 許可されたディレクトリのみ / Only allowed directories
    allowed_base = Path("/allowed/base").resolve()
    if not path.is_relative_to(allowed_base):
        raise ValueError("Path outside allowed directory")

    return path
```

### 機密データ処理 / Sensitive Data Handling
```python
import logging

class SecureProcessor:
    """Processor that handles sensitive data securely."""

    def __init__(self):
        # ログに機密情報を出力しない / Don't log sensitive info
        self.logger = logging.getLogger(__name__)

    def process_payment(self, card_number: str, amount: float):
        """Process payment without logging sensitive data."""
        # 良い例 / Good
        self.logger.info(f"Processing payment for amount: {amount}")

        # 避けるべき例 / Avoid
        # self.logger.info(f"Processing payment {card_number} for {amount}")
```

## コードレビューチェックリスト / Code Review Checklist

### 機能的側面 / Functional Aspects
- [ ] コードは要件を満たしているか
- [ ] エラー処理が適切か
- [ ] 境界条件が考慮されているか
- [ ] テストが十分か

### 品質側面 / Quality Aspects
- [ ] コーディング規約に従っているか
- [ ] ドキュメントが適切か
- [ ] 型ヒントが正確か
- [ ] セキュリティホールがないか

### パフォーマンス側面 / Performance Aspects
- [ ] 効率的なアルゴリズムを使用しているか
- [ ] メモリリークがないか
- [ ] 大規模データに対応できるか

### 保守性側面 / Maintainability Aspects
- [ ] コードが理解しやすいか
- [ ] 将来の拡張が考慮されているか
- [ ] 技術的負債がないか

## ツール設定 / Tool Configuration

### Black設定 / Black Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs
  | \.git
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### isort設定 / isort Configuration
```toml
# pyproject.toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### flake8設定 / flake8 Configuration
```toml
# pyproject.toml
[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    "__pycache__",
    "dist",
    "build",
    "*.egg-info",
    ".venv",
    "venv",
]
max-complexity = 15
```

### mypy設定 / mypy Configuration
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
disallow_any_generics = false
ignore_missing_imports = true
follow_imports = "silent"
show_error_codes = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
strict_equality = true
```

## 参考資料 / References

- [PEP 8 - Pythonコードスタイルガイド](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Black Code Formatter](https://black.readthedocs.io/)
- [mypy Type Checker](https://mypy.readthedocs.io/)
- [flake8 Linter](https://flake8.pycqa.org/)

---

**高品質なコードで信頼性の高いソフトウェアを**

**Build reliable software with high-quality code**
