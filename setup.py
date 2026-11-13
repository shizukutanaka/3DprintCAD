"""Setup configuration for 3D Print CAD Assistant."""

from setuptools import setup, find_packages
from pathlib import Path

readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="printcad",
    version="0.1.0",
    author="3DprintCAD Team",
    description="3D Print CAD Assistant - Automated geometry validation and print preparation for 3D models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.9",
    # Dependency declarations live in pyproject.toml ([project] and
    # [project.optional-dependencies]) as the single source of truth.
    # This file intentionally declares none: setuptools merges the two
    # and stale duplicates here contradicted pyproject.toml.
    entry_points={
        "console_scripts": [
            "printcad=src.cli_main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Multimedia :: Graphics :: 3D Modeling",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="3d-printing cad mesh validation stl obj geometry",
)