"""
API endpoint implementations.

This package auto-imports all category modules to trigger action registration.
Category writers just need to create a new .py file with @action decorators.
"""

import importlib
import pkgutil

# Auto-import all modules in this package to trigger registration
for _, module_name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{module_name}")
