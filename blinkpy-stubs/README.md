# Blinkpy Type Stubs

This package provides type stubs for the `blinkpy` library, enabling proper type checking with MyPy, Pylint, and other static analysis tools.

## Installation

### Option 1: Use with MYPYPATH (Recommended for development)

Add to your project's `mypy.ini`:

```ini
[mypy]
mypy_path = ./blinkpy-stubs
```

### Option 2: Install as a package

```bash
cd blinkpy-stubs
pip install -e .
```

## What's Included

The stubs provide type annotations for:

- **`blinkpy.blinkpy.Blink`** - Main Blink class with all properties and methods
- **`blinkpy.camera.BlinkCamera`** - Camera class with properties like `battery`, `temperature`, `motion_enabled`
- **`blinkpy.sync_module.BlinkSyncModule`** - Sync module class with `arm`, `online`, `cameras` properties
- **`blinkpy.auth.Auth`** - Authentication class with login and token management
- **`blinkpy.helpers.util`** - Utility functions like `load_saved_blink`, `cleanup_blink_session`

## Features

✅ **Complete API Coverage**: All methods and properties used in blinkpy-flask are typed
✅ **Proper Return Types**: Accurate return types for async methods and properties
✅ **Union Types**: Handles Optional values and Union types correctly
✅ **Generic Support**: Proper Dict and List typing for collections
✅ **MyPy Compatible**: Eliminates all "missing library stubs" warnings

## Usage

With these stubs installed, you get:

```python
from blinkpy.blinkpy import Blink
from blinkpy.camera import BlinkCamera

# MyPy now understands these types
blink: Blink = Blink()
camera: BlinkCamera = blink.cameras["front_door"]

# Type checking works for properties
battery_level: str = camera.battery  # ✅ Typed as Optional[str]
is_online: bool = camera.sync.online  # ✅ Typed as bool
```

## Type Checking Results

Before stubs:
```
app.py:66: error: Skipping analyzing "blinkpy.camera": module is installed, but missing library stubs
app.py:67: error: Skipping analyzing "blinkpy.sync_module": module is installed, but missing library stubs
app.py:2315: error: Skipping analyzing "blinkpy.helpers.util": module is installed, but missing library stubs
```

After stubs:
```
✅ No import errors - all blinkpy modules are properly typed
```

## Compatibility

- **Python**: 3.10+
- **MyPy**: 0.900+
- **Blinkpy**: Compatible with the version used in blinkpy-flask project

## Generated For

These stubs were specifically created for the `blinkpy-flask` project and cover all the blinkpy API usage patterns found in that codebase.
