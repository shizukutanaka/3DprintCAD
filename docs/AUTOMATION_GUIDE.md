# Automation Guide

## Overview
This guide covers automated workflows for efficient 3D print preparation.

---

## Quick Start

### Auto-Validate Single File
```python
from src.core.automation import auto_validate_file
from pathlib import Path

result = auto_validate_file(Path("model.stl"))
print(f"Valid: {result['validation']['is_valid']}")
print(f"Issues: {len(result['validation']['issues'])}")
```

### Auto-Repair Single File
```python
from src.core.automation import auto_repair_file
from pathlib import Path

result = auto_repair_file(
    Path("broken_model.stl"),
    output_path=Path("fixed_model.stl")
)

if result['success'] and result.get('repaired'):
    print(f"Repaired! Issues before: {result['improvement']['issues_before']}")
    print(f"Issues after: {result['improvement']['issues_after']}")
```

### Batch Process Directory
```python
from src.core.automation import process_batch
from pathlib import Path

# Validate all STL files
result = process_batch(
    input_dir=Path("models/"),
    auto_repair=False
)

# Auto-repair all files
result = process_batch(
    input_dir=Path("models/"),
    output_dir=Path("fixed/"),
    auto_repair=True
)

print(f"Processed: {result['processed']}/{result['total_files']}")
print(f"Valid: {result['valid']}, Repaired: {result['repaired']}")
```

---

## CLI Usage

### Quick Batch Script
```bash
# Validate all STL files in directory
python scripts/auto_process.py models/

# Auto-repair all files
python scripts/auto_process.py models/ --repair -o fixed/

# Process specific pattern
python scripts/auto_process.py models/ --pattern "*.obj"
```

---

## API Integration

### Upload with Auto-Validation (Default)
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@model.stl"
```

Response includes:
- `file_id`: Unique identifier
- `validation`: Full validation report
- `recommendations`: Suggested fixes
- `auto_repairable`: Can be automatically fixed

### Upload Without Auto-Validation
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@model.stl" \
  -F "auto_validate=false"
```

### Auto-Repair Uploaded File
```bash
curl -X POST http://localhost:5000/api/auto-repair/{file_id}
```

Response includes:
- `repair_needed`: Whether repair was necessary
- `repaired`: Whether repair was performed
- `before_validation`: Issues before repair
- `after_validation`: Issues after repair
- `improvement`: Metrics showing improvement

---

## Features

### 1. Auto-Validation
**Purpose**: Automatically validate meshes on upload/load

**What it checks**:
- Manifold edges (watertightness)
- Degenerate faces
- Inverted normals
- Wall thickness
- Feature size
- Overhang angles

**Output**:
- Structured validation report
- Prioritized issue list
- Recommendations for fixes
- Auto-repairable flag

### 2. Auto-Repair
**Purpose**: Fix common mesh issues automatically

**What it fixes**:
- Non-manifold edges
- Degenerate faces
- Duplicate vertices
- Inverted normals
- Small holes

**Workflow**:
1. Validate mesh
2. Check if auto-repairable
3. Apply repairs
4. Re-validate
5. Report improvements

### 3. File Format Detection
**Purpose**: Identify file format from extension and binary signature

**Supports**:
- Extension-based detection
- Binary signature detection
- Format compatibility check

**Example**:
```python
from src.core.automation import FileTypeDetector
from pathlib import Path

info = FileTypeDetector.detect_format(Path("model.stl"))
print(f"Format: {info['format_name']}")
print(f"Binary: {info['is_binary']}")
print(f"Supported: {info['supported']}")
```

### 4. Batch Processing
**Purpose**: Process multiple files efficiently

**Modes**:
- Validate only (default)
- Auto-repair mode
- Custom processing

**Features**:
- Directory scanning
- Pattern matching
- Progress tracking
- Error handling
- Detailed reporting

---

## Automation Classes

### AutoValidator
Automatic validation on file operations.

```python
from src.core.automation import AutoValidator
from src.core.analysis.mesh_validator import MeshValidationSettings

# Custom settings
settings = MeshValidationSettings(
    min_wall_thickness=1.0,
    min_feature_size=0.5
)

validator = AutoValidator(settings)
result = validator.validate_and_report(file_path)
```

### AutoRepair
Intelligent mesh repair workflow.

```python
from src.core.automation import AutoRepair

repairer = AutoRepair()
result = repairer.repair_if_needed(
    file_path=Path("model.stl"),
    output_path=Path("fixed.stl"),
    aggressive=False  # Use conservative repair
)
```

### BatchProcessor
Efficient batch file processing.

```python
from src.core.automation import BatchProcessor

processor = BatchProcessor(
    auto_repair=True,
    auto_validate=True
)

result = processor.process_directory(
    input_dir=Path("models/"),
    output_dir=Path("processed/"),
    pattern="*.stl"
)
```

---

## Integration Examples

### Web Upload Handler
```python
from flask import request
from src.core.automation import auto_validate_file

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file_path = save_uploaded_file(file)

    # Auto-validate
    result = auto_validate_file(file_path)

    return jsonify({
        'validation': result['validation'],
        'auto_repairable': result['auto_repairable']
    })
```

### CLI Integration
```python
import click
from src.core.automation import auto_repair_file

@click.command()
@click.argument('input_file')
def repair(input_file):
    """Auto-repair mesh file."""
    result = auto_repair_file(Path(input_file))

    if result['success'] and result.get('repaired'):
        click.echo(f"✓ Repaired: {result['output_file']}")
    else:
        click.echo(f"✗ {result.get('message', 'Repair failed')}")
```

### Workflow Automation
```python
from pathlib import Path
from src.core.automation import (
    auto_validate_file,
    auto_repair_file
)

def automated_workflow(input_dir: Path, output_dir: Path):
    """Complete automated workflow."""
    for file_path in input_dir.glob("*.stl"):
        # Step 1: Validate
        validation = auto_validate_file(file_path)

        if not validation['validation']['is_valid']:
            # Step 2: Try repair if possible
            if validation['auto_repairable']:
                repair_result = auto_repair_file(
                    file_path,
                    output_path=output_dir / file_path.name
                )

                if repair_result['success']:
                    print(f"✓ {file_path.name} - Repaired")
                else:
                    print(f"✗ {file_path.name} - Cannot auto-repair")
            else:
                print(f"⚠ {file_path.name} - Needs manual repair")
        else:
            print(f"✓ {file_path.name} - Already valid")
```

---

## Best Practices

### 1. Validation Strategy
- Always validate before slicing
- Use auto-validation on upload
- Set appropriate thresholds for your printer

### 2. Repair Strategy
- Try conservative repair first
- Use aggressive mode only when needed
- Always re-validate after repair
- Keep original files as backup

### 3. Batch Processing
- Process in smaller batches for large sets
- Use pattern matching to filter files
- Check output regularly during processing
- Handle failures gracefully

### 4. Error Handling
```python
from src.core.automation import auto_repair_file
from pathlib import Path

try:
    result = auto_repair_file(file_path)

    if not result['success']:
        print(f"Error: {result.get('message', 'Unknown error')}")

        if not result.get('auto_repairable'):
            print("Manual intervention required")

except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Performance Tips

1. **Batch Processing**: Use `BatchProcessor` for multiple files
2. **Parallel Processing**: Process independent files in parallel
3. **Caching**: Reuse validation results when possible
4. **Filtering**: Use pattern matching to process only needed files

---

## Troubleshooting

### Issue: Auto-repair fails
**Solution**: Check if issues are auto-repairable
```python
if not result.get('auto_repairable'):
    # Manual repair needed
    print("Issues require manual intervention")
```

### Issue: Validation too strict
**Solution**: Adjust validation settings
```python
settings = MeshValidationSettings(
    min_wall_thickness=0.4,  # Lower threshold
    min_feature_size=0.2
)
```

### Issue: Batch processing slow
**Solution**: Use pattern matching and process smaller batches
```bash
# Process only STL files
python scripts/auto_process.py models/ --pattern "*.stl"

# Process subdirectory
python scripts/auto_process.py models/batch1/ --repair
```

---

## Examples

### Complete Workflow Script
```python
#!/usr/bin/env python3
"""Production automation workflow."""
from pathlib import Path
from src.core.automation import (
    BatchProcessor,
    AutoValidator,
    AutoRepair
)

def production_workflow(input_dir: Path):
    """Complete production workflow."""
    # Step 1: Batch validate
    validator = BatchProcessor(auto_validate=True, auto_repair=False)
    validation_results = validator.process_directory(input_dir)

    print(f"Validation: {validation_results['valid']}/{validation_results['total_files']} valid")

    # Step 2: Auto-repair failures
    repairer = AutoRepair()
    repaired = 0

    for file_result in validation_results['files']:
        if not file_result.get('validation', {}).get('is_valid'):
            if file_result.get('auto_repairable'):
                repair_result = repairer.repair_if_needed(
                    Path(file_result['file'])
                )
                if repair_result.get('repaired'):
                    repaired += 1

    print(f"Auto-repair: {repaired} files repaired")

    # Step 3: Final report
    print("\nProduction ready files:")
    for file_result in validation_results['files']:
        if file_result.get('validation', {}).get('is_valid'):
            print(f"  ✓ {Path(file_result['file']).name}")

if __name__ == '__main__':
    production_workflow(Path("models/"))
```

---

## Summary

Automation features provide:
- **Time savings**: Validate and repair in bulk
- **Consistency**: Same validation rules across all files
- **Efficiency**: Automated workflows reduce manual work
- **Quality**: Catch issues early in the pipeline

**Key Benefits**:
- Upload → Auto-validate → Instant feedback
- Batch repair → Save hours of manual work
- Format detection → No guessing file types
- API integration → Seamless workflow automation
