#!/usr/bin/env python3
"""
Fix BOM (Byte Order Mark) in manifest files
"""
from pathlib import Path

custom_addons = Path("C:/D/crm/custom-addons")

for manifest in custom_addons.glob("**/__manifest__.py"):
    print(f"Checking {manifest}...")
    
    # Read with UTF-8 and remove BOM
    content = manifest.read_bytes()
    
    # Remove UTF-8 BOM if present
    if content.startswith(b'\xef\xbb\xbf'):
        print(f"  Removing BOM from {manifest.name}")
        content = content[3:]  # Skip BOM
        manifest.write_bytes(content)
        print(f"  ✓ Fixed")
    else:
        print(f"  ✓ No BOM found")

print("\nAll manifest files checked and fixed!")
