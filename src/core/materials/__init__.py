"""Material database system for 3D printing materials."""
from .database import MaterialDatabase, get_material_database
from .models import (
    MaterialType, PrinterType, MaterialProperties, MaterialPreset,
    PrintSettings, CompatibilityInfo, MaterialCategory
)
from .presets import MaterialPresetManager
from .selection import MaterialSelector

__all__ = [
    'MaterialDatabase',
    'get_material_database',
    'MaterialType',
    'PrinterType',
    'MaterialProperties',
    'MaterialPreset',
    'PrintSettings',
    'CompatibilityInfo',
    'MaterialCategory',
    'MaterialPresetManager',
    'MaterialSelector'
]