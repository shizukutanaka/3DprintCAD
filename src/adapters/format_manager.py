"""Universal format manager for 3D printing file formats."""

import os
import json
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union, BinaryIO
from dataclasses import dataclass, asdict
from pathlib import Path
import trimesh
import numpy as np
from abc import ABC, abstractmethod

@dataclass
class ModelMetadata:
    """Metadata for 3D models."""
    title: str = ""
    creator: str = ""
    description: str = ""
    creation_time: str = ""
    modification_time: str = ""
    application: str = "3D Print CAD Pro"
    version: str = "1.0"
    units: str = "millimeter"
    material: Optional[str] = None
    print_settings: Optional[Dict] = None
    copyright: str = ""
    license: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class BaseFormatHandler(ABC):
    """Base class for format handlers."""

    @abstractmethod
    def can_import(self, file_path: str) -> bool:
        """Check if this handler can import the given file."""
        pass

    @abstractmethod
    def can_export(self, format_name: str) -> bool:
        """Check if this handler can export to the given format."""
        pass

    @abstractmethod
    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import model from file."""
        pass

    @abstractmethod
    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    **kwargs) -> bool:
        """Export model to file."""
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        pass

class STLHandler(BaseFormatHandler):
    """Handler for STL files (ASCII and Binary)."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.stl')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() in ['stl', 'stl_ascii', 'stl_binary']

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import STL file."""
        try:
            mesh = trimesh.load(file_path)

            # Extract metadata from comments if available
            metadata = ModelMetadata()

            if hasattr(mesh, 'metadata') and mesh.metadata:
                if 'header' in mesh.metadata:
                    header = mesh.metadata['header']
                    if isinstance(header, bytes):
                        header_str = header.decode('utf-8', errors='ignore').strip()
                        metadata.description = header_str

            return {
                'mesh': mesh,
                'metadata': metadata,
                'format': 'STL',
                'success': True,
                'warnings': []
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': 'STL',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    binary: bool = True, **kwargs) -> bool:
        """Export to STL format."""
        try:
            # Add metadata to header for binary STL
            if metadata and binary:
                header = f"{metadata.title} - {metadata.description}"[:80]
                mesh.export(file_path, file_type='stl', header=header.encode('utf-8'))
            else:
                mesh.export(file_path, file_type='stl')
            return True
        except Exception:
            return False

    def get_supported_extensions(self) -> List[str]:
        return ['.stl']

class OBJHandler(BaseFormatHandler):
    """Handler for OBJ files with MTL materials."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.obj')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() == 'obj'

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import OBJ file with materials."""
        try:
            mesh = trimesh.load(file_path)

            metadata = ModelMetadata()
            warnings = []

            # Check for MTL file
            mtl_path = file_path.replace('.obj', '.mtl')
            materials = {}

            if os.path.exists(mtl_path):
                materials = self._parse_mtl_file(mtl_path)
                if materials:
                    metadata.material = list(materials.keys())[0]

            # Extract comments from OBJ file
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            comment = line[1:].strip()
                            if comment and not metadata.description:
                                metadata.description = comment
                            break
            except (OSError, UnicodeDecodeError):
                pass

            return {
                'mesh': mesh,
                'metadata': metadata,
                'materials': materials,
                'format': 'OBJ',
                'success': True,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': 'OBJ',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    include_materials: bool = True, **kwargs) -> bool:
        """Export to OBJ format with optional materials."""
        try:
            # Export OBJ
            mesh.export(file_path, file_type='obj')

            # Add metadata as comments
            if metadata:
                self._add_obj_metadata(file_path, metadata)

            # Export materials if requested
            if include_materials:
                mtl_path = file_path.replace('.obj', '.mtl')
                self._create_default_mtl(mtl_path, metadata)

            return True
        except Exception:
            return False

    def _parse_mtl_file(self, mtl_path: str) -> Dict[str, Dict]:
        """Parse MTL material file."""
        materials = {}
        current_material = None

        try:
            with open(mtl_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('newmtl '):
                        current_material = line[7:]
                        materials[current_material] = {}
                    elif current_material and ' ' in line:
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            key, value = parts
                            materials[current_material][key] = value
        except (OSError, UnicodeDecodeError):
            pass

        return materials

    def _add_obj_metadata(self, file_path: str, metadata: ModelMetadata):
        """Add metadata as comments to OBJ file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            header = f"# {metadata.title}\n"
            header += f"# Created by: {metadata.creator}\n"
            header += f"# Description: {metadata.description}\n"
            header += f"# Application: {metadata.application}\n"

            with open(file_path, 'w') as f:
                f.write(header + content)
        except (OSError, UnicodeDecodeError):
            pass

    def _create_default_mtl(self, mtl_path: str, metadata: Optional[ModelMetadata]):
        """Create default MTL file."""
        try:
            material_name = metadata.material if metadata and metadata.material else "default"

            mtl_content = f"""# Material file created by 3D Print CAD Pro
newmtl {material_name}
Ka 0.2 0.2 0.2
Kd 0.8 0.8 0.8
Ks 0.5 0.5 0.5
Ns 100.0
illum 2
"""
            with open(mtl_path, 'w') as f:
                f.write(mtl_content)
        except OSError:
            pass

    def get_supported_extensions(self) -> List[str]:
        return ['.obj']

class PLYHandler(BaseFormatHandler):
    """Handler for PLY files."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.ply')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() == 'ply'

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import PLY file."""
        try:
            mesh = trimesh.load(file_path)

            metadata = ModelMetadata()

            return {
                'mesh': mesh,
                'metadata': metadata,
                'format': 'PLY',
                'success': True,
                'warnings': []
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': 'PLY',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    binary: bool = True, **kwargs) -> bool:
        """Export to PLY format."""
        try:
            mesh.export(file_path, file_type='ply')
            return True
        except Exception:
            return False

    def get_supported_extensions(self) -> List[str]:
        return ['.ply']

class AMFHandler(BaseFormatHandler):
    """Handler for AMF (Additive Manufacturing Format) files."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.amf')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() == 'amf'

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import AMF file."""
        try:
            # Parse AMF XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            metadata = ModelMetadata()

            # Extract metadata
            if root.tag == 'amf':
                unit = root.get('unit', 'millimeter')
                metadata.units = unit

                # Look for metadata elements
                for child in root:
                    if child.tag == 'metadata':
                        meta_type = child.get('type', '')
                        if meta_type == 'name':
                            metadata.title = child.text or ''
                        elif meta_type == 'description':
                            metadata.description = child.text or ''
                        elif meta_type == 'author':
                            metadata.creator = child.text or ''

            # Load mesh data
            mesh = trimesh.load(file_path)

            return {
                'mesh': mesh,
                'metadata': metadata,
                'format': 'AMF',
                'success': True,
                'warnings': []
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': 'AMF',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    **kwargs) -> bool:
        """Export to AMF format."""
        try:
            # Create AMF XML structure
            amf = ET.Element('amf')
            amf.set('unit', metadata.units if metadata else 'millimeter')
            amf.set('version', '1.1')

            # Add metadata
            if metadata:
                if metadata.title:
                    meta_name = ET.SubElement(amf, 'metadata')
                    meta_name.set('type', 'name')
                    meta_name.text = metadata.title

                if metadata.description:
                    meta_desc = ET.SubElement(amf, 'metadata')
                    meta_desc.set('type', 'description')
                    meta_desc.text = metadata.description

                if metadata.creator:
                    meta_author = ET.SubElement(amf, 'metadata')
                    meta_author.set('type', 'author')
                    meta_author.text = metadata.creator

            # Add object
            obj = ET.SubElement(amf, 'object')
            obj.set('id', '0')

            # Add mesh data
            mesh_elem = ET.SubElement(obj, 'mesh')
            vertices_elem = ET.SubElement(mesh_elem, 'vertices')

            # Add vertices
            for i, vertex in enumerate(mesh.vertices):
                vertex_elem = ET.SubElement(vertices_elem, 'vertex')
                coord = ET.SubElement(vertex_elem, 'coordinates')

                x_elem = ET.SubElement(coord, 'x')
                x_elem.text = str(vertex[0])
                y_elem = ET.SubElement(coord, 'y')
                y_elem.text = str(vertex[1])
                z_elem = ET.SubElement(coord, 'z')
                z_elem.text = str(vertex[2])

            # Add volume and triangles
            volume_elem = ET.SubElement(mesh_elem, 'volume')
            for face in mesh.faces:
                triangle = ET.SubElement(volume_elem, 'triangle')
                v1 = ET.SubElement(triangle, 'v1')
                v1.text = str(face[0])
                v2 = ET.SubElement(triangle, 'v2')
                v2.text = str(face[1])
                v3 = ET.SubElement(triangle, 'v3')
                v3.text = str(face[2])

            # Write XML
            tree = ET.ElementTree(amf)
            tree.write(file_path, encoding='utf-8', xml_declaration=True)

            return True
        except Exception:
            return False

    def get_supported_extensions(self) -> List[str]:
        return ['.amf']

class ThreeMFHandler(BaseFormatHandler):
    """Handler for 3MF (3D Manufacturing Format) files."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.3mf')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() == '3mf'

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import 3MF file."""
        try:
            metadata = ModelMetadata()
            warnings = []

            # 3MF is a ZIP archive
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Read model file
                model_data = zip_file.read('3D/3dmodel.model')
                tree = ET.fromstring(model_data)

                # Extract metadata
                for meta in tree.findall('.//{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}metadata'):
                    name = meta.get('name', '')
                    if name == 'Title':
                        metadata.title = meta.text or ''
                    elif name == 'Designer':
                        metadata.creator = meta.text or ''
                    elif name == 'Description':
                        metadata.description = meta.text or ''

                # Load mesh using trimesh
                mesh = trimesh.load(file_path)

            return {
                'mesh': mesh,
                'metadata': metadata,
                'format': '3MF',
                'success': True,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': '3MF',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    **kwargs) -> bool:
        """Export to 3MF format."""
        try:
            # Create 3MF structure
            model_xml = self._create_3mf_model(mesh, metadata)

            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add content types
                content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
    <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />
</Types>'''
                zip_file.writestr('[Content_Types].xml', content_types)

                # Add relationships
                rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />
</Relationships>'''
                zip_file.writestr('_rels/.rels', rels)

                # Add model
                zip_file.writestr('3D/3dmodel.model', model_xml)

            return True
        except Exception:
            return False

    def _create_3mf_model(self, mesh: trimesh.Trimesh, metadata: Optional[ModelMetadata]) -> str:
        """Create 3MF model XML."""
        model = ET.Element('model')
        model.set('unit', metadata.units if metadata else 'millimeter')
        model.set('xmlns', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')

        # Add metadata
        if metadata:
            meta_group = ET.SubElement(model, 'metadata')
            meta_group.set('name', 'Application')
            meta_group.text = metadata.application

            if metadata.title:
                meta_title = ET.SubElement(model, 'metadata')
                meta_title.set('name', 'Title')
                meta_title.text = metadata.title

            if metadata.creator:
                meta_creator = ET.SubElement(model, 'metadata')
                meta_creator.set('name', 'Designer')
                meta_creator.text = metadata.creator

        # Add resources
        resources = ET.SubElement(model, 'resources')
        obj = ET.SubElement(resources, 'object')
        obj.set('id', '1')
        obj.set('type', 'model')

        # Add mesh
        mesh_elem = ET.SubElement(obj, 'mesh')

        # Add vertices
        vertices = ET.SubElement(mesh_elem, 'vertices')
        for vertex in mesh.vertices:
            vertex_elem = ET.SubElement(vertices, 'vertex')
            vertex_elem.set('x', str(vertex[0]))
            vertex_elem.set('y', str(vertex[1]))
            vertex_elem.set('z', str(vertex[2]))

        # Add triangles
        triangles = ET.SubElement(mesh_elem, 'triangles')
        for face in mesh.faces:
            triangle = ET.SubElement(triangles, 'triangle')
            triangle.set('v1', str(face[0]))
            triangle.set('v2', str(face[1]))
            triangle.set('v3', str(face[2]))

        # Add build
        build = ET.SubElement(model, 'build')
        item = ET.SubElement(build, 'item')
        item.set('objectid', '1')

        return ET.tostring(model, encoding='unicode')

    def get_supported_extensions(self) -> List[str]:
        return ['.3mf']

class X3DHandler(BaseFormatHandler):
    """Handler for X3D files."""

    def can_import(self, file_path: str) -> bool:
        return file_path.lower().endswith('.x3d')

    def can_export(self, format_name: str) -> bool:
        return format_name.lower() == 'x3d'

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import X3D file."""
        try:
            mesh = trimesh.load(file_path)
            metadata = ModelMetadata()

            return {
                'mesh': mesh,
                'metadata': metadata,
                'format': 'X3D',
                'success': True,
                'warnings': []
            }

        except Exception as e:
            return {
                'mesh': None,
                'metadata': None,
                'format': 'X3D',
                'success': False,
                'error': str(e)
            }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    metadata: Optional[ModelMetadata] = None,
                    **kwargs) -> bool:
        """Export to X3D format."""
        try:
            # Create X3D structure
            x3d_content = self._create_x3d_content(mesh, metadata)

            with open(file_path, 'w') as f:
                f.write(x3d_content)

            return True
        except Exception:
            return False

    def _create_x3d_content(self, mesh: trimesh.Trimesh, metadata: Optional[ModelMetadata]) -> str:
        """Create X3D content."""
        vertices_str = ' '.join([f"{v[0]} {v[1]} {v[2]}" for v in mesh.vertices])
        indices_str = ' '.join([f"{f[0]} {f[1]} {f[2]} -1" for f in mesh.faces])

        title = metadata.title if metadata else "3D Model"
        description = metadata.description if metadata else "Exported from 3D Print CAD Pro"

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="3.3">
  <head>
    <meta name="title" content="{title}"/>
    <meta name="description" content="{description}"/>
    <meta name="generator" content="3D Print CAD Pro"/>
  </head>
  <Scene>
    <Shape>
      <IndexedFaceSet coordIndex="{indices_str}">
        <Coordinate point="{vertices_str}"/>
      </IndexedFaceSet>
      <Appearance>
        <Material diffuseColor="0.8 0.8 0.8"/>
      </Appearance>
    </Shape>
  </Scene>
</X3D>'''

    def get_supported_extensions(self) -> List[str]:
        return ['.x3d']

class FormatManager:
    """Universal format manager for 3D printing files."""

    def __init__(self):
        self.handlers = {
            'stl': STLHandler(),
            'obj': OBJHandler(),
            'ply': PLYHandler(),
            'amf': AMFHandler(),
            '3mf': ThreeMFHandler(),
            'x3d': X3DHandler()
        }

    def get_supported_import_formats(self) -> Dict[str, List[str]]:
        """Get all supported import formats."""
        formats = {}
        for name, handler in self.handlers.items():
            formats[name.upper()] = handler.get_supported_extensions()
        return formats

    def get_supported_export_formats(self) -> List[str]:
        """Get all supported export formats."""
        formats = []
        for name, handler in self.handlers.items():
            if handler.can_export(name):
                formats.append(name.upper())
        return formats

    def detect_format(self, file_path: str) -> Optional[str]:
        """Detect file format from extension."""
        ext = Path(file_path).suffix.lower()

        for name, handler in self.handlers.items():
            if ext in handler.get_supported_extensions():
                return name.upper()

        return None

    def can_import(self, file_path: str) -> bool:
        """Check if file can be imported."""
        for handler in self.handlers.values():
            if handler.can_import(file_path):
                return True
        return False

    def import_model(self, file_path: str) -> Dict[str, Any]:
        """Import model from file."""
        for handler in self.handlers.values():
            if handler.can_import(file_path):
                return handler.import_model(file_path)

        return {
            'mesh': None,
            'metadata': None,
            'format': None,
            'success': False,
            'error': 'Unsupported file format'
        }

    def export_model(self, mesh: trimesh.Trimesh, file_path: str,
                    format_name: str = None,
                    metadata: Optional[ModelMetadata] = None,
                    **kwargs) -> bool:
        """Export model to file."""

        # Detect format from extension if not specified
        if format_name is None:
            format_name = self.detect_format(file_path)
            if format_name is None:
                return False

        format_name = format_name.lower()

        if format_name in self.handlers:
            handler = self.handlers[format_name]
            if handler.can_export(format_name):
                return handler.export_model(mesh, file_path, metadata, **kwargs)

        return False

    def batch_convert(self, input_files: List[str], output_format: str,
                     output_dir: str = None) -> Dict[str, bool]:
        """Convert multiple files to specified format."""
        results = {}

        for input_file in input_files:
            try:
                # Import
                import_result = self.import_model(input_file)
                if not import_result['success']:
                    results[input_file] = False
                    continue

                # Determine output path
                if output_dir:
                    output_path = os.path.join(output_dir,
                                             Path(input_file).stem + f'.{output_format.lower()}')
                else:
                    output_path = str(Path(input_file).with_suffix(f'.{output_format.lower()}'))

                # Export
                success = self.export_model(
                    import_result['mesh'],
                    output_path,
                    output_format,
                    import_result['metadata']
                )

                results[input_file] = success

            except Exception:
                results[input_file] = False

        return results

    def validate_model(self, file_path: str) -> Dict[str, Any]:
        """Validate imported model."""
        import_result = self.import_model(file_path)

        if not import_result['success']:
            return import_result

        mesh = import_result['mesh']
        validation_results = {
            'is_watertight': mesh.is_watertight,
            'is_manifold': mesh.is_winding_consistent,
            'volume': float(mesh.volume) if mesh.is_watertight else None,
            'surface_area': float(mesh.area),
            'bounding_box': mesh.bounds.tolist(),
            'vertex_count': len(mesh.vertices),
            'face_count': len(mesh.faces),
            'issues': []
        }

        # Check for issues
        if not mesh.is_watertight:
            validation_results['issues'].append('Model is not watertight')

        if not mesh.is_winding_consistent:
            validation_results['issues'].append('Model has inconsistent normals')

        if mesh.volume < 0:
            validation_results['issues'].append('Model has negative volume')

        return {**import_result, 'validation': validation_results}

    def get_model_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive model information."""
        validation = self.validate_model(file_path)

        if not validation['success']:
            return validation

        mesh = validation['mesh']
        metadata = validation['metadata']

        # Calculate additional metrics
        dimensions = mesh.bounds[1] - mesh.bounds[0]

        info = {
            'file_info': {
                'path': file_path,
                'size': os.path.getsize(file_path),
                'format': validation['format']
            },
            'metadata': asdict(metadata),
            'geometry': {
                'dimensions': dimensions.tolist(),
                'volume': float(mesh.volume) if mesh.is_watertight else None,
                'surface_area': float(mesh.area),
                'center_of_mass': mesh.center_mass.tolist() if mesh.is_watertight else None,
                'is_watertight': mesh.is_watertight,
                'is_manifold': mesh.is_winding_consistent
            },
            'mesh_quality': {
                'vertex_count': len(mesh.vertices),
                'face_count': len(mesh.faces),
                'edge_count': len(mesh.edges),
                'genus': mesh.euler_number if mesh.is_watertight else None
            },
            'validation': validation['validation']
        }

        return info