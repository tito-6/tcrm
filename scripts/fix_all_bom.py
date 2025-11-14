#!/usr/bin/env python3
"""Fix BOM in all addon files"""
from pathlib import Path

custom_addons = Path("C:/D/crm/custom-addons")

count = 0
extensions = ['*.py', '*.xml', '*.csv', '*.txt', '*.md', '*.js', '*.css']

for ext in extensions:
    for file in custom_addons.glob(f"**/{ext}"):
        try:
            content = file.read_bytes()
            
            if content.startswith(b'\xef\xbb\xbf'):
                print(f"Fixing: {file.relative_to(custom_addons)}")
                file.write_bytes(content[3:])
                count += 1
        except Exception as e:
            print(f"Error with {file}: {e}")

print(f"\n✓ Fixed {count} files")
