# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.

import sys
from importlib.machinery import ModuleSpec

# Extend the path to include all addon directories
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

# The TCRM module system expects __path__ to have a _path_finder attribute
# We need to add this without breaking the list functionality
class _PathFinderWrapper:
    """Wrapper to add _path_finder attribute to the path list"""
    def __call__(self, *args):
        return None

# Store the original list
_original_path = __path__

# Create a custom list class that has the _path_finder attribute
class NamespacePath(list):
    """Custom list class with _path_finder attribute for TCRM compatibility"""
    _path_finder = _PathFinderWrapper()
    
    def __init__(self, items):
        super().__init__(items)

# Replace __path__ with our custom list
__path__ = NamespacePath(_original_path)
