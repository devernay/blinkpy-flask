#!/usr/bin/env python3
"""Setup script for blinkpy type stubs."""

from setuptools import find_packages, setup

setup(
    name="blinkpy-stubs",
    version="0.24.0b0",
    description="Type stubs for blinkpy package",
    author="Generated for blinkpy-flask project",
    packages=find_packages(),
    package_data={
        "blinkpy-stubs": ["py.typed", "**/*.pyi"],
    },
    zip_safe=False,
)
