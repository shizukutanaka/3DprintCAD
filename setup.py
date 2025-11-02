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
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0,<2.0.0",
        "trimesh>=3.10.0,<4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0,<8.0.0",
            "pytest-cov>=4.0.0,<5.0.0",
            "mypy>=1.0.0,<2.0.0",
            "black>=22.0.0,<24.0.0",
            "flake8>=5.0.0,<7.0.0",
        ],
        "full": [
            "scipy>=1.7.0,<2.0.0",
            "networkx>=2.6.0,<4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "printcad=src.cli:main",
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="3d-printing cad mesh validation stl obj geometry",
)