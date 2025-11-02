#!/usr/bin/env python3
"""Generate multilingual documentation for 3D Print CAD Assistant."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.i18n_optimized import MultiLanguageDocumentationGenerator, Language

def main():
    """Generate multilingual documentation."""
    print("Generating multilingual documentation...")

    # Create documentation generator
    generator = MultiLanguageDocumentationGenerator()

    # Output directory
    output_dir = Path(__file__).parent / 'docs' / 'multilingual'
    output_dir.mkdir(exist_ok=True)

    # Generate user guides in all supported languages
    print("Generating user guides...")
    generator.generate_user_guide(output_dir)

    # Generate API references in all supported languages
    print("Generating API references...")
    generator.generate_api_reference(output_dir)

    print("Documentation generation completed!")
    print(f"Generated files in: {output_dir}")

    # List generated files
    print("\nGenerated files:")
    for file_path in sorted(output_dir.glob("*")):
        print(f"  {file_path.name}")

if __name__ == "__main__":
    main()
