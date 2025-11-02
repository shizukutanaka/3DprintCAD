"""Material database management system."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Iterator, Union
from dataclasses import asdict
import threading
from contextlib import contextmanager

from ..config import get_config
from ..logging import get_logger
from .models import MaterialPreset, MaterialType, MaterialCategory, PrinterType


class MaterialDatabase:
    """SQLite-based material database with JSON backup support."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize material database."""
        if db_path is None:
            config = get_config()
            db_path = config.config_directory / "materials.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = get_logger(__name__)
        self._lock = threading.RLock()

        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Materials table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    manufacturer TEXT,
                    product_line TEXT,
                    color TEXT,
                    material_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    data TEXT NOT NULL,  -- JSON serialized material data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Material tags for flexible categorization
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_tags (
                    material_id TEXT,
                    tag TEXT,
                    PRIMARY KEY (material_id, tag),
                    FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
                )
            ''')

            # Material compatibility table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_printer_compatibility (
                    material_id TEXT,
                    printer_type TEXT,
                    compatible BOOLEAN,
                    PRIMARY KEY (material_id, printer_type),
                    FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_type ON materials (material_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_category ON materials (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_manufacturer ON materials (manufacturer)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_material_tags_tag ON material_tags (tag)')

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def add_material(self, material: MaterialPreset, update_if_exists: bool = True) -> bool:
        """Add material to database."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Check if material exists
                    cursor.execute('SELECT id FROM materials WHERE id = ?', (material.id,))
                    exists = cursor.fetchone() is not None

                    if exists and not update_if_exists:
                        self.logger.warning(f"Material {material.id} already exists")
                        return False

                    # Serialize material data
                    material_data = json.dumps(material.to_dict())

                    if exists:
                        # Update existing material
                        cursor.execute('''
                            UPDATE materials
                            SET name=?, manufacturer=?, product_line=?, color=?,
                                material_type=?, category=?, data=?,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (
                            material.name, material.manufacturer, material.product_line,
                            material.color, material.material_type.value, material.category.value,
                            material_data, material.id
                        ))
                    else:
                        # Insert new material
                        cursor.execute('''
                            INSERT INTO materials (id, name, manufacturer, product_line, color,
                                                 material_type, category, data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            material.id, material.name, material.manufacturer, material.product_line,
                            material.color, material.material_type.value, material.category.value,
                            material_data
                        ))

                    # Update compatibility data
                    cursor.execute('DELETE FROM material_printer_compatibility WHERE material_id = ?',
                                 (material.id,))

                    for printer_type in material.compatibility.compatible_printers:
                        cursor.execute('''
                            INSERT INTO material_printer_compatibility (material_id, printer_type, compatible)
                            VALUES (?, ?, ?)
                        ''', (material.id, printer_type.value, True))

                    for printer_type in material.compatibility.incompatible_printers:
                        cursor.execute('''
                            INSERT INTO material_printer_compatibility (material_id, printer_type, compatible)
                            VALUES (?, ?, ?)
                        ''', (material.id, printer_type.value, False))

                    conn.commit()

                    action = "Updated" if exists else "Added"
                    self.logger.info(f"{action} material: {material.name} ({material.id})")
                    return True

            except Exception as e:
                self.logger.error(f"Failed to add material {material.id}: {str(e)}")
                return False

    def get_material(self, material_id: str) -> Optional[MaterialPreset]:
        """Get material by ID."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT data FROM materials WHERE id = ?', (material_id,))
                    row = cursor.fetchone()

                    if row:
                        material_data = json.loads(row['data'])
                        return MaterialPreset.from_dict(material_data)

                    return None

            except Exception as e:
                self.logger.error(f"Failed to get material {material_id}: {str(e)}")
                return None

    def search_materials(
        self,
        material_type: Optional[MaterialType] = None,
        category: Optional[MaterialCategory] = None,
        manufacturer: Optional[str] = None,
        compatible_with: Optional[PrinterType] = None,
        name_contains: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[MaterialPreset]:
        """Search materials with various filters."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    query_parts = ['SELECT DISTINCT m.data FROM materials m']
                    conditions = []
                    params = []

                    # Join with compatibility table if needed
                    if compatible_with:
                        query_parts.append('LEFT JOIN material_printer_compatibility mpc ON m.id = mpc.material_id')

                    # Join with tags table if needed
                    if tags:
                        query_parts.append('LEFT JOIN material_tags mt ON m.id = mt.material_id')

                    # Build WHERE conditions
                    if material_type:
                        conditions.append('m.material_type = ?')
                        params.append(material_type.value)

                    if category:
                        conditions.append('m.category = ?')
                        params.append(category.value)

                    if manufacturer:
                        conditions.append('m.manufacturer = ?')
                        params.append(manufacturer)

                    if name_contains:
                        conditions.append('m.name LIKE ?')
                        params.append(f'%{name_contains}%')

                    if compatible_with:
                        conditions.append('(mpc.printer_type = ? AND mpc.compatible = 1)')
                        params.append(compatible_with.value)

                    if tags:
                        tag_conditions = ' OR '.join(['mt.tag = ?'] * len(tags))
                        conditions.append(f'({tag_conditions})')
                        params.extend(tags)

                    # Combine query parts
                    query = ' '.join(query_parts)
                    if conditions:
                        query += ' WHERE ' + ' AND '.join(conditions)

                    query += ' ORDER BY m.name'

                    if limit:
                        query += ' LIMIT ?'
                        params.append(limit)

                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                    materials = []
                    for row in rows:
                        try:
                            material_data = json.loads(row['data'])
                            material = MaterialPreset.from_dict(material_data)
                            materials.append(material)
                        except Exception as e:
                            self.logger.warning(f"Failed to deserialize material data: {str(e)}")

                    return materials

            except Exception as e:
                self.logger.error(f"Failed to search materials: {str(e)}")
                return []

    def list_all_materials(self) -> List[MaterialPreset]:
        """List all materials in database."""
        return self.search_materials()

    def delete_material(self, material_id: str) -> bool:
        """Delete material from database."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM materials WHERE id = ?', (material_id,))
                    deleted = cursor.rowcount > 0
                    conn.commit()

                    if deleted:
                        self.logger.info(f"Deleted material: {material_id}")
                    else:
                        self.logger.warning(f"Material not found for deletion: {material_id}")

                    return deleted

            except Exception as e:
                self.logger.error(f"Failed to delete material {material_id}: {str(e)}")
                return False

    def get_material_count(self) -> int:
        """Get total number of materials in database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM materials')
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            self.logger.error(f"Failed to get material count: {str(e)}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # Total count
                cursor.execute('SELECT COUNT(*) as total FROM materials')
                stats['total_materials'] = cursor.fetchone()['total']

                # Count by type
                cursor.execute('''
                    SELECT material_type, COUNT(*) as count
                    FROM materials
                    GROUP BY material_type
                ''')
                stats['by_type'] = {row['material_type']: row['count'] for row in cursor.fetchall()}

                # Count by category
                cursor.execute('''
                    SELECT category, COUNT(*) as count
                    FROM materials
                    GROUP BY category
                ''')
                stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}

                # Count by manufacturer
                cursor.execute('''
                    SELECT manufacturer, COUNT(*) as count
                    FROM materials
                    WHERE manufacturer IS NOT NULL
                    GROUP BY manufacturer
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                stats['top_manufacturers'] = {
                    row['manufacturer']: row['count'] for row in cursor.fetchall()
                }

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {}

    def export_to_json(self, file_path: Path) -> bool:
        """Export all materials to JSON file."""
        try:
            materials = self.list_all_materials()
            data = {
                'version': '1.0',
                'exported_at': None,  # Could add timestamp
                'materials': [material.to_dict() for material in materials]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported {len(materials)} materials to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export materials: {str(e)}")
            return False

    def import_from_json(self, file_path: Path, update_existing: bool = True) -> int:
        """Import materials from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            materials_data = data.get('materials', [])
            imported_count = 0

            for material_data in materials_data:
                try:
                    material = MaterialPreset.from_dict(material_data)
                    if self.add_material(material, update_if_exists=update_existing):
                        imported_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to import material: {str(e)}")

            self.logger.info(f"Imported {imported_count} materials from {file_path}")
            return imported_count

        except Exception as e:
            self.logger.error(f"Failed to import materials: {str(e)}")
            return 0


# Global database instance
_material_database: Optional[MaterialDatabase] = None
_db_lock = threading.Lock()


def get_material_database() -> MaterialDatabase:
    """Get global material database instance."""
    global _material_database

    if _material_database is None:
        with _db_lock:
            if _material_database is None:
                _material_database = MaterialDatabase()

    return _material_database